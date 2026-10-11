"""PROTOTYPE -- throwaway. Tier-1 task generation, rendering and reward.

Implements issue #7's generator design with issue #16's two-arm objective sampler, for the
sole purpose of issue #8's cold probe. Not production code: no abstractions, no error
handling past what keeps it runnable.

Runs on Windows (task generation, analysis) and inside WSL (the rollout's tool + reward),
so it depends only on RDKit + numpy. RDKit must be 2026.09.1 in both -- the sigma cache's
provenance key -- or y_ref and sigma silently stop matching the task file.
"""

from __future__ import annotations

import json
import math
import random
import re
from pathlib import Path

import numpy as np
from rdkit import Chem, RDLogger
from rdkit.Chem import BRICS

from glosses import gloss

RDLogger.DisableLog("rdApp.*")

REPO = Path(__file__).resolve().parents[2]
CACHES = REPO / "caches" / "tier1-pool"

# --- Table A1 reward constants (Tier-1 column) -----------------------------------------------
K_OBJ = 10.0
S_SOFT = 0.1
W_OBJ = 0.5
W_CONSTRAINT = 0.5
R_TOOL = -0.001
R_FORMAT = -0.5
R_INVALID = -0.001

# --- the properties module from scripts/pool, imported by path ------------------------------
import importlib.util as _ilu

_spec = _ilu.spec_from_file_location("pool_properties", REPO / "scripts" / "pool" / "properties.py")
pool_properties = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(pool_properties)

NAMES = pool_properties.NAMES
KIND = pool_properties.KIND


# --- caches ----------------------------------------------------------------------------------
def load_caches():
    sigma = json.loads((CACHES / "sigma_cache.json").read_text())["properties"]
    rho = np.load(CACHES / "spearman_cache.npz", allow_pickle=True)
    rho_names = [str(n) for n in rho["names"]]
    rho_ix = {n: i for i, n in enumerate(rho_names)}
    return sigma, rho["rho"], rho_ix


def arm_pools(sigma):
    """The two objective pools of issue #16, recomputed from the cache rather than hardcoded."""
    ok = {k: v for k, v in sigma.items() if v["status"] == "ok"}
    span = sorted(k for k, v in ok.items() if v["p5"] < v["p95"])
    gate = sorted(
        k
        for k, v in ok.items()
        if (v["kind"] == "continuous")
        or (v["kind"] == "integer" and v["sigma"] >= 2.5 and k != "num_stereoisomers")
    )
    # Constraints are drawn from every property that survived the descriptor pass at all
    # (#7: "all 101, fixed at the sampler"). The three non-ok ones are excluded because a
    # nan constraint cannot be scored, and they carry no row in the Spearman matrix either.
    constraint_pool = sorted(ok)
    return {"span": span, "gate": gate}, constraint_pool


# --- scaffold --------------------------------------------------------------------------------
def _cap_with_h(frag):
    """Turn a BRICS fragment's attachment dummies into hydrogens.

    Capping, not deleting, is what the paper's own example shows: its published core
    ``COc1ccccc1SCC=O`` is the acyl fragment with the amide nitrogen replaced by H, which is
    why it renders as an aldehyde. Both of the obvious wrong turns were measured in #8 over
    582 fragments: ``DeleteSubstructs`` leaves unfilled valences (91 fragments then fail to
    match their own parent), and ``SetAtomicNum(1)`` alone keeps the BRICS isotope label that
    encodes the bond type, giving ``[5H]`` -- a hydrogen-5 that matches nothing (582 of 582
    fail). Clearing the isotope as well brings non-matches to 0 of 582.
    """
    rw = Chem.RWMol(frag)
    for a in rw.GetAtoms():
        if a.GetAtomicNum() == 0:
            a.SetAtomicNum(1)
            a.SetIsotope(0)
            a.SetNoImplicit(False)
    mol = rw.GetMol()
    try:
        Chem.SanitizeMol(mol)
        return Chem.RemoveHs(mol)
    except Exception:
        return None


def brics_scaffold(mol, rng):
    """Break ONE BRICS bond, keep the larger fragment, cap the attachment with H.

    Issue #7 recorded this recipe's *result* for the paper's published example
    (COc1ccccc1SCC(=O)N[C@@H](C)c1ccon1 -> COc1ccccc1SCC=O, 12 heavy atoms vs 8) but
    scripts/pool/properties.py implements full ``BRICSDecompose`` instead, which returns the
    largest *leaf*: `c1ccccc1`, benzene. Measured in #8: full decomposition cannot produce the
    published string from any of its 7 leaves, while breaking the single amide bond reproduces
    it exactly. Which of the 6 BRICS bonds to break is not recoverable from one example, so it
    is drawn uniformly -- the plain reading of "randomly generated", and the published scaffold
    is one of its 6 outcomes.

    Returns "" when the molecule has no BRICS bond at all (caller resamples the seed).
    """
    bonds = list(BRICS.FindBRICSBonds(mol))
    if not bonds:
        return ""
    chosen = bonds[rng.randrange(len(bonds))]
    broken = BRICS.BreakBRICSBonds(mol, bonds=[chosen])
    best, best_n = "", -1
    for frag in Chem.GetMolFrags(broken, asMols=True, sanitizeFrags=False):
        capped = _cap_with_h(frag)
        if capped is None:
            continue
        n = capped.GetNumHeavyAtoms()
        if n > best_n:
            best, best_n = Chem.MolToSmiles(capped), n
    return best


# Properties whose value on any molecule containing the scaffold is bounded below by the
# scaffold's own value. A substructure match pins every heavy atom of the core, so heavy-atom
# counts and weights are provable lower bounds. atom_count_H is NOT: substituting a core
# hydrogen removes it. Used only by filter tests 3 and 4.
SIZE_MONOTONE = {
    "molecular_weight",
    "exact_molecular_weight",
    "heavy_atom_molecular_weight",
    "heavy_atom_count",
    "num_heteroatoms",
    "num_bonds",
    "num_valence_electrons",
    "nocount",
    *[f"atom_count_{s}" for s in ("C", "N", "O", "S", "F", "Cl", "Br", "P", "I")],
}


# --- property evaluation ---------------------------------------------------------------------
_PROP_IX = {n: i for i, n in enumerate(NAMES)}
_CACHE: dict[str, list[float]] = {}


def props_of(smiles: str):
    """All 100 numeric properties, memoised by canonical SMILES (#7's borrowed plumbing)."""
    if smiles in _CACHE:
        return _CACHE[smiles]
    mol = Chem.MolFromSmiles(smiles)
    vals = None if mol is None else pool_properties.compute(mol)
    _CACHE[smiles] = vals
    return vals


def prop_value(smiles: str, name: str):
    vals = props_of(smiles)
    if vals is None:
        return None
    v = vals[_PROP_IX[name]]
    return None if (v is None or not math.isfinite(v)) else v


# --- reward (Eq A1-A6) -----------------------------------------------------------------------
def r_obj(y_hat, y_ref, tau, direction):
    delta = (y_hat - y_ref) if direction == "maximize" else (y_ref - y_hat)
    if tau <= 0:
        return 0.0
    mag = 1.0 - math.exp(-K_OBJ * (delta / tau) ** 2)
    return math.copysign(mag, delta) if delta != 0 else 0.0


def score_constraint(con, smiles):
    """Eq A5 (integer -> hard 1/0) and Eq A6 (continuous -> Gaussian partial credit)."""
    if con["kind"] == "scaffold":
        mol = Chem.MolFromSmiles(smiles)
        core = Chem.MolFromSmiles(con["core"])
        if mol is None or core is None:
            return 0.0
        return 1.0 if mol.HasSubstructMatch(core, useChirality=False) else 0.0

    v = prop_value(smiles, con["property"])
    if v is None:
        return 0.0

    if con["kind"] == "integer":
        op, bound = con["op"], con["bound"]
        if op == "==":
            return 1.0 if abs(v - bound) < 1e-9 else 0.0
        if op == ">=":
            return 1.0 if v >= bound - 1e-9 else 0.0
        return 1.0 if v <= bound + 1e-9 else 0.0

    lo, hi, sigma_i = con["lo"], con["hi"], con["sigma_i"]
    if lo - 1e-12 <= v <= hi + 1e-12:
        return 1.0
    d = (lo - v) if v < lo else (v - hi)
    scale = S_SOFT * sigma_i
    return math.exp(-0.5 * (d / scale) ** 2) if scale > 0 else 0.0


def reward(task, smiles, n_tool_calls, format_ok, include_tool_penalty=True):
    """R_total = w_obj*r_obj + w_c*r_c + n_tool*r_tool + r_format + r_invalid.

    ``smiles`` is the final proposed molecule, or None when the episode produced none.
    """
    out = {
        "r_obj": 0.0,
        "r_constraint": 0.0,
        "r_format": 0.0 if format_ok else R_FORMAT,
        "r_invalid": 0.0,
        "r_tool": n_tool_calls * R_TOOL,
        "constraint_scores": [],
        "valid": False,
    }
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        out["r_invalid"] = R_INVALID
    else:
        out["valid"] = True
        canon = Chem.MolToSmiles(mol)
        obj = task["objective"]
        y_hat = prop_value(canon, obj["property"])
        if y_hat is not None:
            out["r_obj"] = r_obj(y_hat, obj["y_ref"], obj["tau"], obj["direction"])
            out["y_hat"] = y_hat
        scores = [score_constraint(c, canon) for c in task["constraints"]]
        out["constraint_scores"] = scores
        out["r_constraint"] = sum(scores) / len(scores) if scores else 0.0

    total = W_OBJ * out["r_obj"] + W_CONSTRAINT * out["r_constraint"] + out["r_format"] + out["r_invalid"]
    if include_tool_penalty:
        total += out["r_tool"]
    out["total"] = total
    return out


# --- rendering -------------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a helpful scientific assistant with expertise in molecular design, computational biology, and chemistry.

When working with molecular and biological data, use standard conventions:

- Molecular representations: SMILES, SELFIES, InChI, IUPAC names, SMARTS patterns, molecular formulas

- Protein sequences: single-letter amino acid codes (A, C, D, E, F, G, H, I, K, L, M, N, P, Q, R, S, T, V, W, Y). When providing a protein sequence, output one continuous string of amino acids with no spaces, unless the prompt specifies otherwise.

- Standard units: g/mol for molecular weight, Angstroms for distances

At the end of your response, provide a summary of your reasoning and the answer:

On a new line provide the reasoning summary between <|reasoning_summary_start|> and <|reasoning_summary_end|> tags.

On a new line provide the final answer between <|answer_start|> and <|answer_end|> tags.

After your thinking, the <|answer_start|> and <|answer_end|> tags must each appear exactly once in your response, enclosing your single final answer.

Example format:

<|reasoning_summary_start|>[summary of reasoning and analysis]<|reasoning_summary_end|>

<|answer_start|>[final answer]<|answer_end|>

Note: The brackets [ ] above are placeholders only - do not include them in your actual response."""


def _fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def render_constraint(con):
    """The paper's rendering: unperturbed integers as a bare value, perturbed ones as an
    inequality, the scaffold as "Must contain scaffold:"."""
    if con["kind"] == "scaffold":
        return f"- Must contain scaffold: {con['core']}"
    g = gloss(con["property"])
    if con["kind"] == "integer":
        if con["op"] == "==":
            return f"- {int(con['bound'])} {g}"
        sym = ">" if con["op"] == ">=" else "<"
        return f"- {g} {sym} {int(con['render_against'])}"
    return f"- {g} between {_fmt(con['lo'])} and {_fmt(con['hi'])}"


def render_prompt(task, turn_budget=15):
    props = "\n".join(NAMES)
    cons = "\n\n".join(render_constraint(c) for c in task["constraints"])
    return f"""Your task is to design molecules that optimize a target molecular property while satisfying user-provided constraints.

TURN BUDGET

You have {turn_budget} turns total. Each turn is either a molecule proposal OR a tool call -- both count toward the limit.

TOOL USE

You have access to a property-calculation tool. Each tool call incurs a small cost, but returns precise property values that help you make better proposals. You must decide when the information gain from a tool call is worth the cost.

To call the tool, emit a line of exactly this form and nothing else in the message:

CALL_TOOL: calculate_multiple_properties(properties=[name, name, ...], smiles=[SMILES, ...])

OUTPUT FORMAT

Each molecule proposal must be its own message containing both of the following tag blocks:

<|reasoning_summary_start|>

[Your reasoning: what molecule you are evaluating, what modifications you made, which constraints you are addressing]

<|reasoning_summary_end|>

<|answer_start|>

[Molecule representation only -- a valid molecule representation]

<|answer_end|>

Do NOT include tool calls in the same message as your molecule proposal. If you want to evaluate a molecule's properties, first propose it in one message, then call the property-calculation tool in a separate message.

AVAILABLE PROPERTIES

{props}

EXAMPLE

Message 1 (call tool to evaluate starting molecule):

CALL_TOOL: calculate_multiple_properties(properties=[logp, qed], smiles=[NS(=O)(=O)c1ccc(N)cc1])

Message 2 (propose molecule based on results):

"Based on the property calculations, logp is too high. I will add a hydroxyl group to reduce lipophilicity.

<|reasoning_summary_start|>

Adding hydroxyl at the para position to reduce logp while maintaining the required scaffold and improving QED.

<|reasoning_summary_end|>

<|answer_start|>

NS(=O)(=O)c1ccc(NC(=O)Nc2ccc(O)c(F)c2)cc1

<|answer_end|>"

REQUIREMENTS

1. Molecule proposals and tool calls must be in separate messages.

2. The answer tags must contain ONLY a single valid molecule representation.

3. Your LAST message MUST include the answer tags with your final molecule. This can be your best molecule from any point in the conversation -- you do not need to propose something new if you already found a good candidate.

GOAL

Your goal is to optimize a target property of the starting molecule while satisfying all constraints below. You are scored on the quality of your final proposed molecule.

Starting molecule: {task['seed_smiles']}

Target property:

Your objective is to {task['objective']['direction']} the {gloss(task['objective']['property'])}.

Constraints:

{cons}

WORKFLOW

1. Calculate properties of the starting molecule to understand the baseline.

2. Identify which constraints are violated and what needs improvement.

3. Propose a structural modification that improves the target property while satisfying constraints.

4. Evaluate the modified molecule with the tool.

5. Iterate -- use the tool results to guide your next proposal.

6. In your final message, output the best molecule you found (which may be one you proposed earlier)."""


# --- parsing the model's messages ------------------------------------------------------------
_ANSWER = re.compile(r"<\|answer_start\|>(.*?)<\|answer_end\|>", re.S)
_SUMMARY = re.compile(r"<\|reasoning_summary_start\|>(.*?)<\|reasoning_summary_end\|>", re.S)
_TOOLCALL = re.compile(
    r"calculate_multiple_properties\s*\(\s*properties\s*=\s*\[(.*?)\]\s*,\s*smiles\s*=\s*\[(.*?)\]\s*\)",
    re.S | re.I,
)
# Qwen3 is post-trained on its own tool-call format, so the probe accepts that too. Insisting
# on the ad-hoc CALL_TOOL: line would measure syntax luck, not whether the model reaches for
# the tool -- which is what question 2 of the ticket asks.
_NATIVE_TOOLCALL = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)

_SPLIT = lambda s: [t.strip().strip("\"'") for t in s.split(",") if t.strip()]


def parse_message(text):
    """Classify one assistant message. Returns a dict describing what it is."""
    answers = _ANSWER.findall(text)
    summaries = _SUMMARY.findall(text)
    out = {
        "n_answer_tags": len(answers),
        "n_summary_tags": len(summaries),
        "has_tool_call": False,
        "tool_syntax": None,
        "answer": None,
        "answer_parses": False,
        "tool_properties": None,
        "tool_smiles": None,
    }
    if answers:
        cand = answers[-1].strip()
        out["answer"] = cand
        out["answer_parses"] = Chem.MolFromSmiles(cand) is not None

    tool = _TOOLCALL.search(text)
    if tool:
        out.update(
            has_tool_call=True,
            tool_syntax="call_tool",
            tool_properties=_SPLIT(tool.group(1)),
            tool_smiles=_SPLIT(tool.group(2)),
        )
        return out

    native = _NATIVE_TOOLCALL.search(text)
    if native:
        try:
            payload = json.loads(native.group(1))
            args = payload.get("arguments", payload) or {}
            props = args.get("properties") or []
            smis = args.get("smiles") or []
            as_list = lambda x: [str(v) for v in x] if isinstance(x, list) else _SPLIT(str(x))
            out.update(
                has_tool_call=True,
                tool_syntax="native",
                tool_properties=as_list(props),
                tool_smiles=as_list(smis),
            )
        except Exception:
            out.update(has_tool_call=True, tool_syntax="native_unparsable",
                       tool_properties=[], tool_smiles=[])
    return out


def run_tool(properties_req, smiles_req, max_props=25, max_smiles=5):
    """calculate_multiple_properties. Returns (text, stats)."""
    bad_props = [p for p in properties_req if p not in _PROP_IX]
    good_props = [p for p in properties_req if p in _PROP_IX][:max_props]
    lines, bad_smiles = [], []
    for smi in smiles_req[:max_smiles]:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            bad_smiles.append(smi)
            lines.append(f"{smi}: ERROR - not a parsable molecule")
            continue
        canon = Chem.MolToSmiles(mol)
        vals = ", ".join(f"{p}={_fmt(round(prop_value(canon, p) or float('nan'), 3))}" for p in good_props)
        lines.append(f"{smi}: {vals}" if good_props else f"{smi}: no valid property names requested")
    if bad_props:
        lines.append(f"Unknown property names (ignored): {', '.join(bad_props[:10])}")
    if not smiles_req:
        lines.append("ERROR - no SMILES supplied")
    stats = {
        "n_props_requested": len(properties_req),
        "n_props_valid": len(good_props),
        "n_smiles_requested": len(smiles_req),
        "n_smiles_invalid": len(bad_smiles),
        "all_props_valid": bool(properties_req) and not bad_props,
        # The rejected names themselves, not just a count. Question 2 of #8 asks whether the
        # tool is called "with a valid property list", and the probe renders tasks in the
        # paper's gloss style ("the primary amine groups") while the tool accepts only
        # identifiers (fr_NH2) -- so the *shape* of the failure is the finding: a gloss echoed
        # back verbatim means the glossing is the problem, a near-miss identifier means it is
        # not.
        "bad_props": bad_props[:12],
    }
    return "\n".join(lines), stats

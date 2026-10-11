"""PROTOTYPE -- throwaway. The template-match problem.

Requiring the whole lead as a substructure makes any scaffold-modifying proposal
unscorable, which would impose a hard scaffold constraint the paper does not have
(its contains_scaffold is evaluation-only, by design). Test an MCS fallback:
embed against the maximum common substructure instead, and measure what it costs.
"""
import json
import os
import sys
import time
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent))
from PROTOTYPE_dock_oracle import embed_to_template  # noqa: E402
from rdkit import Chem, RDLogger  # noqa: E402
from rdkit.Chem import AllChem, rdFMCS  # noqa: E402

RDLogger.DisableLog("rdApp.*")
STRUCT = Path(os.environ["STRUCT_DIR"])


def embed_via_mcs(smiles, core, min_core_atoms=8, timeout=5):
    """Fall back to the MCS of proposal and lead, keeping the lead's coordinates
    for the shared part. Returns (mol, err, n_core_atoms, t_mcs)."""
    m = Chem.MolFromSmiles(smiles)
    if m is None or m.GetNumAtoms() == 0:
        return None, "parse_failed", 0, 0.0
    t0 = time.perf_counter()
    res = rdFMCS.FindMCS([core, m], timeout=timeout,
                         ringMatchesRingOnly=True, completeRingsOnly=True,
                         atomCompare=rdFMCS.AtomCompare.CompareElements,
                         bondCompare=rdFMCS.BondCompare.CompareOrder)
    t_mcs = time.perf_counter() - t0
    if res.canceled or res.numAtoms < min_core_atoms:
        return None, f"mcs_too_small({res.numAtoms})", res.numAtoms, t_mcs
    patt = Chem.MolFromSmarts(res.smartsString)
    cmatch = core.GetSubstructMatch(patt)
    if not cmatch:
        return None, "mcs_no_core_match", res.numAtoms, t_mcs

    # build a sub-core carrying the lead's crystallographic coordinates
    sub = Chem.RWMol(core)
    keep = set(cmatch)
    for idx in sorted((a.GetIdx() for a in core.GetAtoms() if a.GetIdx() not in keep),
                      reverse=True):
        sub.RemoveAtom(idx)
    subcore = sub.GetMol()
    try:
        Chem.SanitizeMol(subcore)
    except Exception:
        Chem.SanitizeMol(subcore, Chem.SanitizeFlags.SANITIZE_ALL ^
                         Chem.SanitizeFlags.SANITIZE_PROPERTIES)

    mh = Chem.AddHs(m)
    if not mh.GetSubstructMatch(subcore):
        return None, "subcore_no_match", res.numAtoms, t_mcs
    try:
        AllChem.ConstrainedEmbed(mh, subcore, useTethers=True, randomseed=0xF00D)
    except Exception as e:
        return None, f"embed_failed:{type(e).__name__}", res.numAtoms, t_mcs
    return mh, None, res.numAtoms, t_mcs


def main():
    manifest = json.loads((STRUCT / "manifest.json").read_text())
    info = manifest["1iep"]
    core = next(Chem.SDMolSupplier(info["ligand"], removeHs=False))
    lead = info["smiles"]
    print(f"lead (1iep/STI): {lead}\n")

    # scaffold-modifying proposals: ring swaps, linker edits, truncations --
    # exactly the moves a lead-optimisation policy will try
    cases = [
        ("strict analog (methyl)",  None),
        ("pyridine->pyrimidine",    lead.replace("c1ccncc1", "c1cncnc1", 1)),
        ("amide reversed",          lead.replace("C(=O)Nc", "NC(=O)c", 1)),
        ("piperazine->morpholine",  lead.replace("N1CCN(C)CC1", "N1CCOCC1", 1)),
        ("truncated (drop tail)",   "Cc1ccc(NC(=O)c2ccccc2)cc1Nc1nccc(-c2cccnc2)n1"),
        ("off-scaffold entirely",   "CCO"),
        ("different chemotype",     "O=C(Nc1ccc(F)cc1)c1ccc(S(N)(=O)=O)cc1"),
    ]
    strict_ok = mcs_ok = 0
    mcs_times = []
    for label, smi in cases:
        if smi is None:
            smi = lead.replace("Cc1ccc", "CCc1ccc", 1)
        if smi == lead:
            print(f"  {label:<26} (SMILES edit did not apply, skipped)")
            continue
        _, err_strict = embed_to_template(smi, core)
        m, err_mcs, ncore, t_mcs = embed_via_mcs(smi, core)
        mcs_times.append(t_mcs)
        strict_ok += err_strict is None
        mcs_ok += err_mcs is None
        print(f"  {label:<26} strict={'OK ' if not err_strict else 'FAIL':<5} "
              f"mcs={'OK ' if not err_mcs else 'FAIL':<5} "
              f"core={ncore:>3} atoms  mcs_time={t_mcs * 1000:6.1f} ms"
              f"{'  [' + str(err_mcs) + ']' if err_mcs else ''}")

    print(f"\n  strict template: {strict_ok}/{len(mcs_times)} scorable")
    print(f"  MCS fallback   : {mcs_ok}/{len(mcs_times)} scorable")
    print(f"  MCS cost       : median {median(mcs_times) * 1000:.1f} ms, "
          f"max {max(mcs_times) * 1000:.1f} ms")


if __name__ == "__main__":
    main()

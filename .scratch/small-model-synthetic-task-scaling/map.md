# Map: Synthetic Task Scaling at <8B

Label: `wayfinder:map`
Tracker: local markdown (`.scratch/<effort>/`)
Charted: 2026-10-09

## Destination

**A validated, executable spec** for reproducing arXiv:2609.04735 ("Training Large Language
Models for Small-Molecule Design with Synthetic Task Scaling") with a **sub-8B model on one
RTX 5090**, using only free and open software. The spec must be complete enough that someone
can execute it without re-deciding anything: concrete task generators, oracle substitutions,
scaled hyperparameters, curriculum arms, evaluation protocol, and an honest ledger of every
deviation from the paper.

The map is done when nothing is left to decide. **Running the training is the follow-on effort,
not this one.**

## Notes

**Domain.** Multi-turn agentic RL (RLVR/GRPO) for small-molecule lead optimization. Chemistry
tooling: RDKit, docking, PLINDER structures, BRICS scaffolds. The user is **new to machine
learning and is not a computational chemist** — this is their first fine-tuning project.
Tickets must be sized and worded for that: prefer measuring over assuming, and prefer a small
working thing over a correct-on-paper thing.

**Read first, every session:**
- [`paper digest`](../reference/paper-2609.04735-digest.md) — the paper's full specification,
  including both reward functions, Tables A1/A2, task-construction algorithms, prompts, and the
  reproduction-relevant inventory of what is gated vs. free. **Read this before the full text.**
- [`paper full text`](../reference/paper-2609.04735-fulltext.txt) — only when the digest is
  insufficient. 3,179 lines; read by section, not whole.
- [`Unsloth RL capability research`](../research/unsloth-rl-capability.md)
- [`open chemistry oracle research`](../research/open-chem-oracle-stack.md)

**Skills every session should consult:** `grilling` + `domain-modeling` by default; `research`
for AFK fact-finding; `prototype` for the measurement tickets.

### Settled while charting (standing constraints, not up for re-litigation)

1. **Destination is a spec**, aimed at execution as a separate follow-on effort.
2. **Faithful reproduction, shrunk** — keep the paper's pipeline and logic, swap the model size
   and substitute gated oracles. Not a re-framed research question.
3. **Audience: portfolio piece, public repo.** Bar = honest, reproducible, well-documented
   small-scale result. Negative results are acceptable outcomes; undocumented deviations are not.
4. **Strictly free and open-source, local on one RTX 5090** (32 GB, ~21 GB free in practice;
   Blackwell / sm_120). No paid licences, no cloud GPUs, no paid API calls.
5. **No deadline.** Assume ~10 h/week.
6. **Scaling-down principle: preserve the curriculum *shape*, shrink every other dimension.**
   The paper's contribution is the *comparison between curricula*, so multiple comparable arms
   must survive even at ~1% of the compute. Absolute numbers will be far worse than the
   paper's; that is expected and must be stated up front.
7. **Claims targeted:** primary = *curriculum beats Tier-2-only, which mode-collapses*;
   stretch = *an optimum exists around T1(400)–T2(100)*. **Dropped: beating frontier models**
   (needs paid API access; conflicts with constraint 4). The **untrained base model** is the
   floor baseline instead.
8. **Model: Qwen3-4B-Instruct.** A deliberate, documented deviation — the paper uses a *base*
   model, but Table A3 shows Qwen 3.6 base managed only 74/200 successful rollouts with
   123/200 invalid formatting, and 4B is the only size with published Unsloth multi-turn
   evidence. Instruct starts with format- and tool-following already working.
9. **Unsloth Studio is not usable for this.** Its GUI is supervised fine-tuning only — no
   reward functions, no RL, YAML-only export. The RL work happens in the **Unsloth Python
   library under WSL2** (vLLM, which GRPO rollouts require, does not run on native Windows).
   Studio stays available only if an SFT stage is ever added.

### Known traps (surfaced during charting — do not rediscover)

- **Tool-call-penalty warmup is measured in *group-scoring* steps**, not trainer steps:
  1000 group steps at batch 1024 / group 16 ≈ 16 trainer steps. Any rescaling of batch or group
  size must rescale it, or the model learns "catastrophically conservative tool call behavior."
- **Zero-advantage groups are discarded** (Dr. GRPO, no std normalisation). At small group size
  with a weak 4B policy, many groups will be uniformly-rewarded and wasted.
- **Relative BA improvement is normalised against the T1-only arm**, so a Tier-1-only run is a
  mandatory reference arm, not an optional baseline.
- **`contains_scaffold` is evaluation-only by design** — the paper found that exposing it during
  training causes mode collapse.
- **PLINDER train/test split discipline**: Tier-2 draws from train, evaluation from test.
- **IPO loss is prime-rl-specific** and absent from TRL/Unsloth (which offer grpo / dr_grpo /
  dapo / bnpo).
- Poisoned package names: `pip install syba` and `pip install rascore` install **unrelated**
  packages. `PyTDC` fails on Python 3.14. GuacaMol still imports `scipy.histogram` (removed
  from modern SciPy).
- Avoid: **ZINC-22 entirely** — the 3D collection is ~1 PB *and the SMILES-only 2D collection is
  1.31 TB* (measured), so the paper's stated seed source is unobtainable either way; use ZINC20
  2D in-stock, 619 MB (see [ticket 02](issues/02-zinc-smiles-seed-source.md)). Also avoid
  CrossDocked2020's full tarball (50 GiB / 52M files — will choke NTFS) and PDBbind
  (registration-gated, commercialised). PLINDER's **default download is ~1.5 GiB**; the full
  2026-09 release is 64 GiB and is not needed.
- **σ is part of the environment's definition, not a runtime detail.** The Tier-1 reward divides
  by property standard deviations (τ = σ_y in Eq A2, σ_i in Eq A6), so the seed pool sets the
  entire reward scale. Cache σ once to a file keyed by pool + RDKit version + seed, read it
  exclusively from there, and **never regenerate it mid-sweep** — doing so silently rescales
  every reward and invalidates cross-arm comparisons.
- **ZINC has no open licence** — "you may not redistribute major portions of ZINC without
  express written permission." The public repo ships the script, the ZINC IDs and the σ cache,
  **not the SMILES**.

## Decisions so far

<!-- one line per closed ticket: gist + link. -->

- [Where to get ZINC seed molecules at a manageable size](issues/02-zinc-smiles-seed-source.md):
  **ZINC20 2D in-stock (A+B), filtered to MW 300–450, sampled to one 1 M-molecule pool serving as
  both seed and σ pool.** ZINC-22 is undownloadable in *any* form (2D alone is 1.31 TB), so
  substituting ZINC20 is mandatory. The MW filter is the whole fix: it brings σ_MW from 88.4 to
  38.1, inside ZINC-22's implied 30–45 Da band — an uncorrected factor-2 σ mismatch flattens the
  objective reward 3.5× and makes constraints ignorable.

## Not yet specified

In scope, but not yet sharp enough to ticket. Graduates as the frontier advances.

- **LoRA vs full fine-tuning, and LoRA rank / target modules.** The paper does not state which
  it used (almost certainly full FT on 32×B200). Whether LoRA has enough capacity for *RL* —
  as opposed to SFT — at 4B is unresolved, and the answer depends on what ticket 01 measures.
- **Fallback if 4B cannot learn Tier-2 at all.** The paper's own base model mode-collapsed on
  Tier-2; a 4B model may collapse on *both* tiers. Possible responses (an intermediate tier, a
  warm SFT stage, reward reshaping, a smaller turn budget) only become specifiable once
  tickets 07 and 10 report.
- **Zero-advantage waste mitigation** at small group size — difficulty filtering, group-size
  tuning, or task resampling. Needs the measured reward distribution from ticket 07.
- **Write-up structure and the deviation ledger's final form** — what the public repo and
  README must contain for the portfolio bar in constraint 3.
- **Whether to publish the generated Tier-1 task set** as a standalone artifact, and under what
  licence. Partly settled by [ticket 02](issues/02-zinc-smiles-seed-source.md): ZINC's terms
  forbid redistributing major portions, so seed *structures* cannot ship and the repo carries
  the script + ZINC IDs + σ cache instead. Still open: whether a *generated task set* (which
  embeds seed SMILES in its prompts) counts as redistribution, and whether ChEMBL
  (CC BY-SA 3.0) should be used as the seed pool purely to make the artifact shippable —
  at the cost of an upward-skewed σ. Sharpens once the repo's contents are decided.
- **Reopening Tier-2 fidelity if the OpenEye licence is granted** (ticket 04). A grant would
  reopen the oracle substitution, the 15 missing properties, and the `.oedu` filter criterion.
- **Reasoning-token budget.** The paper allows 14,000 completion tokens and 16,384 sequence
  length; a 4B model at 4-bit on 21 GB free VRAM cannot afford that, but the usable figure
  depends on ticket 01's measurements.

## Out of scope

Ruled beyond the destination. Never graduates; returns only if the destination is redrawn.

- **Beating or benchmarking frontier models** (the paper's claim ii). Requires paid API calls to
  five frontier models × 200 rollouts, conflicting with constraint 4. Replaced by the untrained
  base model as the floor baseline.
- **Reproducing SQM2.20.** No standalone implementation exists; it is PM6-D3H4X + COSMO2
  assembled from MOPAC2016 + Cuby4 + AmberTools at ~20 min/complex, with the know-how licensed
  commercially. A free substitute for its *role* is in scope (ticket 08); the method itself is not.
- **Matching the paper's absolute numbers** (+3.18 kcal/mol, 0.623 balanced reward, etc.). At
  ~1% compute with substituted oracles this is not meaningful. Only the *direction and ordering*
  of arms is reproducible.
- **Executing the training runs and reporting results.** That is the follow-on effort the spec
  feeds; this map ends at the spec.
- **The 15 OpenEye properties and the `.oedu` filter criterion**, unless ticket 04 changes the
  licence situation.
- **Multi-GPU, cloud, or distributed training**, including async trainer/inference separation as
  prime-rl does it. One local GPU only.

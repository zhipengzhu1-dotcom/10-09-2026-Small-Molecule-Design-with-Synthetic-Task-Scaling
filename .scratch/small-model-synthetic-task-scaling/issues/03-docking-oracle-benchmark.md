# 03 — Which docking oracle replaces POSIT + Chemgauss4, and how fast is it here?

Type: prototype
Status: open
Blocked by: —
Map: [Synthetic Task Scaling at <8B](../map.md)

## Question

What is the Tier-2 scoring oracle, and what does one call actually cost on this machine?

The paper's `score_chemgauss4` does **POSIT template-based docking** — placing each proposal
using the crystallographic pose of the seed ligand as a template — then scores with
**Chemgauss4**, at "order of seconds" per call. Both are OpenEye and unavailable (see ticket 04).

The leading candidate from research is **smina `--minimize --autobox_ligand`** with the
**Vinardo** scoring function: local minimisation starting from the crystal pose, which mirrors
POSIT's template-based logic rather than re-docking blind. Estimated 0.1–2 s/molecule, but that
figure is **inferred, not benchmarked** — this ticket must measure it. smina is also the only
maintained docking engine with real native-Windows conda-forge builds.

Build a throwaway prototype that, for a handful of real PLINDER systems:

1. Takes a seed ligand + receptor and a proposed analog SMILES.
2. Generates a constrained 3D pose for the proposal (RDKit `ConstrainedEmbed` against the seed's
   scaffold, mirroring the template logic).
3. Scores it, and returns a single number with the same sign convention as Chemgauss4
   (**more negative = tighter binding**).
4. **Measures wall-clock per call** over ≥100 molecules on this hardware, reporting median and
   tail, not just the mean.

Then decide, with measurements rather than opinion:

- **smina/Vinardo (native Windows) vs Uni-Dock (GPU, WSL2, Apache-2.0) vs gnina (WSL2).** Note
  that a GPU docking engine competes with vLLM for the same 21 GB of free VRAM — quantify that
  conflict before choosing GPU docking.
- Is the chosen oracle fast enough to sit inside the RL loop at the scaled rollout budget?
  Compute the implied total docking wall-clock for a full Tier-2 arm and state it explicitly.
  **Full-exhaustiveness CPU Vina/smina is ~126 s/complex — 35 h per 1,000 scores — and is
  disqualified for training.**
- How failures are handled: pose-generation failure, scaffold-embedding failure, non-physical
  poses. The paper penalises unscorable molecules with `r_invalid`, so the oracle must return a
  clean "failed" signal rather than a garbage score. Decide whether PoseBusters runs inside the
  reward path or only during dataset curation.

Record the chosen oracle, its measured cost, its failure contract, and the sign convention.

## Answer

<!-- append on resolution -->

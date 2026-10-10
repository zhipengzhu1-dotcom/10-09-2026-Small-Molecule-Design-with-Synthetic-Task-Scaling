# 06 — Tier-1 task generator design

Type: grilling
Status: open
Blocked by: 02
Map: [Synthetic Task Scaling at <8B](../map.md)

## Question

What exactly does the Tier-1 task generator do, concretely enough to implement?

The paper specifies the algorithm in six steps (see the digest), and **101 of its 116 properties
are RDKit**, so this tier is reproducible almost in full. The decisions are in the details the
paper leaves implicit.

Resolve:

- **Property pool.** Take the 101 RDKit properties from Table A4 as-is, or trim? Several are
  near-duplicates (`molecular_weight` / `exact_molecular_weight` / `heavy_atom_molecular_weight`)
  and 30 are `fr_*` functional-group counts that are zero for most molecules — a target property
  that is 0 for nearly every seed makes a degenerate task. Decide the pool and the exclusion rule.
- **Constraint sampling.** 2–4 constraints plus a BRICS scaffold constraint. Decide how a
  constraint is formed from a seed property value (the paper's example shows both an exact
  equality — "11 aromatic atoms" — and an inequality — "sulfone groups > 2"), and what the
  perturbation in step 4 actually is, numerically, such that the seed violates at least one.
- **Hard vs soft classification.** The reward treats integer/boolean constraints as hard (1/0)
  and continuous ones as soft (Gaussian partial credit). Produce the explicit per-property
  mapping for the chosen pool — this directly determines reward density.
- **Pathology filter.** The paper names two cases (property already saturated at a chemically
  feasible limit; non-scalar property). Enumerate the actual tests. Consider also: constraints
  that are jointly unsatisfiable, and targets that cannot move while the scaffold is retained.
- **Scaffold constraint.** How the BRICS core is extracted from the seed, and what happens when
  BRICS decomposition yields nothing usable.
- **σ for the reward.** The objective normalisation `τ = σ_y` and the soft-constraint `σ_i` are
  property standard deviations over the seed pool (see ticket 02). Decide how and when these are
  computed and cached — they are part of the environment's definition, not a runtime detail.
- **Reuse question.** Research flagged that **GuacaMol v2's 20 goal-directed tasks** are
  RDKit-only and include built-in scaffold-constraint tasks (Deco/Scaffold Hop), and that
  **PMO's** 10,000-call budget / AUC-top-10 / caching protocol is a ready-made harness. Given
  this map's "faithful reproduction, shrunk" constraint, decide whether to rebuild the paper's
  generator faithfully, or borrow GuacaMol/PMO machinery where it does not change the task
  semantics. Caveat: GuacaMol still imports `scipy.histogram`, which no longer exists.
- **How many tasks**, given the ~1% scaling principle, and whether tasks are pre-generated to
  disk or sampled on the fly.

## Answer

<!-- append on resolution -->

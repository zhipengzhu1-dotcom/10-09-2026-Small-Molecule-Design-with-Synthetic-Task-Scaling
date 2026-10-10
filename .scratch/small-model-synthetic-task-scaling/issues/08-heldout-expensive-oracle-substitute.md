# 08 — What plays SQM2.20's role as the held-out expensive oracle?

Type: grilling
Status: open
Blocked by: 03
Map: [Synthetic Task Scaling at <8B](../map.md)

## Question

The paper's entire claim is **cheap-to-expensive transfer**: train on tiers the model can afford,
evaluate on an oracle too expensive to train on. SQM2.20 is unavailable and out of scope. So what
fills its *role*?

Without a substitute there is no held-out expensive oracle, and the reproduction collapses into
"we trained on docking and evaluated on docking" — which reproduces none of the paper's point.
The reproduction needs an evaluation oracle that is (a) free, (b) meaningfully **more expensive
and higher-fidelity** than the Tier-2 training oracle, and (c) **never trained on**.

The promising structural insight: the cheap/expensive *gap* can be recreated with the same
family of tools at different settings. Candidates to weigh:

- **Full-exhaustiveness blind docking** (Vina/smina at default exhaustiveness, ~126 s/complex)
  as the expensive oracle, against **minimisation-only Vinardo** (ticket 03, target 0.1–2 s/mol)
  as the cheap training oracle. Same software family, ~100× cost ratio, genuinely different
  answers. 126 s × 40 systems × 5 rollouts × 5 calls is affordable *at evaluation only* — which
  is precisely the paper's own structure.
- **GFN2-xTB / xtb rescoring** of the docked complex — semiempirical QM, so it is the closest
  free analogue to what SQM2.20 actually is. Research found **no primary source documenting
  per-structure timings**, so this needs measuring before it can be chosen.
- **gnina's CNN rescoring** — a learned scoring function, a genuinely different fidelity class
  from a physics-based one.
- MOPAC or Psi4 single-point interaction energies.

Decide:

1. Which oracle, with a measured cost, and the cost **ratio** to the Tier-2 oracle. State the
   ratio explicitly — it is the quantity that makes the transfer claim meaningful, and the
   paper's own ratio is roughly seconds → tens of minutes.
2. Whether the expensive oracle is **independent enough** to be a real test. If the expensive
   and cheap oracles are too correlated — the same scoring function at different exhaustiveness
   may be — then "transfer" is measuring almost nothing. Quantify the correlation between the
   two oracles on a sample of molecules before committing. **This is the crux of the ticket.**
3. The evaluation-time budget: the paper allows ≤5 expensive calls per rollout, 40 systems ×
   5 rollouts = 200 rollouts. Decide the scaled equivalent and the total wall-clock.
4. Whether `contains_scaffold` is provided at evaluation, as the paper does — and keep it
   **out** of training, which the paper found causes mode collapse.
5. Sign convention and how failures score (the paper assigns invalid rollouts an improvement of 0).

## Answer

<!-- append on resolution -->

# 12 — Which curriculum arms to run

Type: grilling
Status: open
Blocked by: 10, 11
Map: [Synthetic Task Scaling at <8B](../map.md)

## Question

Which of the paper's twelve curriculum arms does the reproduction actually run, and in what order?

The paper runs **twelve arms**, all 500 steps: `T1(500)`, `T2(500)`, and `T1(a)–T2(b)` and
`T1(a)–Mix(b)` for a ∈ {250, 300, 350, 400, 450}. `Mix` means a 25% : 75% Tier-1:Tier-2 batch
mixture in stage 2. Twelve arms is out of reach here; the map's scaling principle keeps the
*shape* of the comparison, not its full breadth.

Decide the arm set and its ordering, against the claims in constraint 7:

- **Minimum viable set for the primary claim** (curriculum > Tier-2-only, which mode-collapses).
  Three arms appear sufficient: **`T1(n)`** as the reference, **`T2(n)`** to exhibit mode
  collapse, and **one** `T1(a)–T2(b)` curriculum. Confirm this is sufficient, and confirm the
  reference arm is required by the metric defined in ticket 11.
- **Which single curriculum split**, if only one. The paper's best were T1(400)–T2(100) and
  T1(300)–T2(200) — both heavily Tier-1-weighted, which is also the cheaper choice since Tier-2
  rollouts cost up to twice a Tier-1 rollout. Decide the scaled equivalent of a 400:100 split.
- **Stretch set for claim (iii)** (an optimum exists). This needs ≥3 curriculum splits to show a
  non-monotonic curve. Decide which splits, and cost them against ticket 10's wall-clock. Note
  the paper found **no clear scaling law**, so a flat or noisy curve is a faithful reproduction
  of its finding, not a failure.
- **Whether to run any `Mix` arm at all.** The paper found mixing Tier-1 back into stage 2 is
  *generally not beneficial* and that catastrophic forgetting is minimal — with one striking
  exception, T1(250)–Mix(250), which beat its T2 counterpart substantially. Decide whether
  testing the exception is worth an arm, or whether `Mix` is dropped entirely as a documented
  deviation.
- **Execution order.** Stage 1 is shared: every `T1(a)–*` arm hot-starts from the Tier-1 run's
  checkpoint at step a. So **one Tier-1 run with checkpoints at each branch point yields all the
  stage-1 prefixes for free.** Exploit this — it is the difference between paying for the
  curriculum arms once and paying for them repeatedly. Specify the checkpoint schedule that the
  chosen arm set implies.
- **The order that de-risks fastest.** Which arm runs first? Running `T2(n)` early is tempting
  because mode collapse should appear quickly and cheaply, confirming the primary claim's
  signature before any expensive curriculum run is attempted.
- **Stopping rule.** Define when to stop adding arms: a wall-clock cap, or a decision that the
  claim is settled either way.

## Answer

<!-- append on resolution -->

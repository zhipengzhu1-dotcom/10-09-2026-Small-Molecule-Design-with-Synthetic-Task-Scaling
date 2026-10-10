# 11 — Evaluation protocol, and is the primary claim even detectable at this scale?

Type: grilling
Status: open
Blocked by: 05, 08, 10
Map: [Synthetic Task Scaling at <8B](../map.md)

## Question

How is the reproduction evaluated, and will the primary claim be visible above the noise?

The paper: **40 held-out systems × 5 rollouts = n = 200** per model; **relative binding affinity
improvement normalised against the T1(500) arm**; ±1 paired SE over the 40 shared systems;
invalid rollouts assigned an improvement of 0; plus balanced reward, systems improved, mean
turns, expensive-oracle turns, and constraint-satisfaction percentage.

Note the paper's own error bars: **+3.18 ± 1.35** and **+3.88 ± 1.98 kcal/mol**. The effect is
only about 2σ at *their* n and *their* compute. At ~1% compute with substituted oracles, the
effect could easily be smaller and the variance larger — so this ticket must establish whether
the experiment can conclude anything before it is run.

Resolve:

- **The metric.** With SQM replaced (ticket 08), define the headline metric and its sign
  convention, and the reference arm for normalisation. **The Tier-1-only arm is a mandatory
  reference, not an optional baseline** — the paper's metric is defined relative to it.
- **Systems and rollouts.** How many held-out systems and rollouts per system, given the
  expensive oracle's measured cost from ticket 08? Trade n against per-call cost explicitly.
- **Detectability — the crux.** The primary claim is *curriculum beats Tier-2-only, which
  mode-collapses*. Fortunately this has a **cheap, unmistakable signature** that does not depend
  on affinity numbers at all: per Appendix C.1, Tier-2-only training drives `r_obj ≈ 0` while
  `r_constraint` saturates, producing single-turn policies that never call tools. Decide whether
  the primary claim is evidenced by **training-curve diagnostics** (`r_obj` vs `r_constraint`,
  mean turns, tool-call counts — nearly free, read off the training run) rather than by the
  expensive held-out metric. If so, the expensive evaluation supports the stretch claim (iii)
  and the primary claim becomes robust to small n. **This is likely the single most important
  design decision in the whole map.**
- **Statistics.** Paired SE over shared systems, as the paper does. Decide whether to add
  seed-level repetition — at this scale, run-to-run variance between *training seeds* may exceed
  the between-arm difference, which no amount of rollout sampling detects. Decide how many
  training seeds per arm, acknowledging the wall-clock cost from ticket 10.
- **Diagnostics to log**, mirroring the paper's auxiliary tables so the comparison is like-for-like:
  rollout outcome breakdown (successful / invalid formatting / scoring failed, as Table A3),
  mean turns, expensive-oracle calls and the turn at which they occur, constraint-satisfaction
  percentage, output character counts, and generative diversity.
- **Negative-result protocol.** Define in advance what would count as *failing to reproduce*,
  versus *reproducing at reduced effect size*, versus *inconclusive*. Writing this down before
  running is what makes the portfolio claim (constraint 3) honest rather than post-hoc.

## Answer

<!-- append on resolution -->

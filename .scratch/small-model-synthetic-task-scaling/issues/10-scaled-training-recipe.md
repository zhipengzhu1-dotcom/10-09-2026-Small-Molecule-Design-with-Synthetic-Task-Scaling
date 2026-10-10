# 10 — The scaled training recipe

Type: grilling
Status: open
Blocked by: 01, 03, 07, 09
Map: [Synthetic Task Scaling at <8B](../map.md)

## Question

What are the actual numbers for a run on one RTX 5090 — and do they fit in a tolerable
wall-clock?

The paper: **32 × B200**, 500 steps, **1024 rollouts/step**, 64 unique tasks/batch, **group
size 16**, 16,384 max sequence, 14,000 max completion. That is **512,000 rollouts per run**, and
the paper reports twelve such runs. Rough arithmetic puts a single faithful-scale run at
**billions of generated tokens and weeks of wall-clock** on one consumer GPU — roughly a 100×
gap. The map's scaling principle (constraint 6) is to **preserve the curriculum shape and shrink
every other dimension**, so comparable arms survive at ~1% cost.

By this point tickets 01, 03, 07 and 09 have supplied measured throughput, measured oracle
latency, the observed reward distribution, and the loss/LoRA decisions. Turn them into a recipe.

Decide, with the arithmetic shown:

- **Total steps**, **rollouts per step**, **unique tasks per batch**, **group size G**.
  Constraint: Unsloth requires `num_generations > 2`; ticket 07's measured fraction of
  zero-advantage groups sets the floor on G, because a group that is uniformly rewarded is
  discarded and its compute wasted.
- **Max sequence length and max completion tokens.** The paper's 16,384 / 14,000 will not fit
  alongside vLLM on ~21 GB of free VRAM. Pick values from ticket 01's measurements and state the
  consequence: a smaller completion budget truncates reasoning, and the paper's trained models
  used far fewer tokens than the base model, so a tight budget may penalise the *untrained*
  policy disproportionately and bias the comparison against the baseline arm.
- **Turn budgets.** Paper: 15 turns (Tier-1), 20 turns with ≤5 expensive scoring calls (Tier-2).
  Trained models used ~7.7 turns. Decide whether to keep the paper's budgets or cut them, and
  note that cutting them changes the task, not just the cost.
- **The rescaled tool-call-penalty warmup.** The paper ramps over **1000 group-scoring steps**,
  where group-scoring steps per trainer step = batch / group = 1024/16 = 64, so ≈ 16 trainer
  steps. At a scaled batch and group this ratio changes completely, and the paper is explicit
  that getting it wrong produces "catastrophically conservative tool call behavior." Compute the
  scaled equivalent in trainer steps and state the formula, not just the number. For mixed
  curricula the paper splits the warmup 250 / 750 between tiers so the full penalty lands at the
  same trainer step for both — preserve that property.
- **Reward hyperparameters** (Table A1): k = 10.0, τ, s = 0.1, r_tool = −0.001,
  r_format = −0.5, r_invalid = −0.001, and the tier-specific weights (Tier-1 0.5/0.5, Tier-2
  0.75/0.25). Decide which transfer unchanged. Note the penalty *scale* interacts with the
  shrunken reward range — r_format = −0.5 against an objective reward bounded in [−1, 1] is a
  large penalty, and at a smaller group size it may dominate the advantage.
- **Checkpointing and hot-start.** The paper hot-starts stage 2 from the stage-1 checkpoint,
  **loading weights only and resetting the optimizer state**. Confirm this is reproducible in
  Unsloth with LoRA adapters, which is not the same operation as reloading a full checkpoint.
- **The wall-clock bottom line.** State hours per arm and hours for the full arm set from
  ticket 12, and check it against ~10 h/week of human attention. If the total is intolerable,
  shrink further *here* rather than discovering it mid-run.

## Answer

<!-- append on resolution -->

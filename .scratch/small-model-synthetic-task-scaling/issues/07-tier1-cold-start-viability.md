# 07 — Can Qwen3-4B-Instruct score above zero on Tier-1 cold?

Type: prototype
Status: open
Blocked by: 01, 06
Map: [Synthetic Task Scaling at <8B](../map.md)

## Question

Does the untrained policy produce enough reward variance for RL to have a gradient at all?

**This is the ticket most likely to kill the project, so it should run as early as possible.**
RLVR needs the starting policy to *sometimes* succeed. The advantage estimator is mean-centring
within a group with no std normalisation, and **groups whose rollouts all receive identical
rewards are discarded as having zero gradient signal**. If a 4B model fails every Tier-1 task
identically — or satisfies the format trivially and nothing else — training does nothing and no
amount of compute fixes it.

The paper's own evidence sharpens the worry: **Qwen 3.6 base managed only 74/200 successful
rollouts with 123/200 invalid formatting** (Table A3) even at 35B. That is why this map chose
the Instruct variant (constraint 8), but the choice is a hypothesis until measured.

Run the untrained Qwen3-4B-Instruct against a sample of generated Tier-1 tasks — **no training,
inference only** — and measure:

1. **Format compliance.** What fraction emit exactly one `<|reasoning_summary_start|>...` and one
   `<|answer_start|>...` block, with a single RDKit-parsable SMILES in the answer tags?
2. **Tool use.** Does it call `calculate_multiple_properties` at all, with a valid property list
   and valid SMILES, in a *separate message* from its proposal as the prompt demands?
3. **Multi-turn behaviour.** Does it iterate across turns, or submit once and stop? Compare
   against the paper's observed collapse signature (single-turn, no tool calls).
4. **Reward distribution.** The headline number: sample G rollouts per task over many tasks and
   report the **within-group reward variance**. What fraction of groups are uniformly-rewarded
   and therefore discarded? This is the go/no-go statistic.
5. **Objective vs constraint decomposition.** Does `r_obj` move at all, or does the model only
   collect `r_constraint`? A policy that saturates constraints while `r_obj ≈ 0` is exactly the
   paper's mode-collapse signature — observing it *before* training would be an important
   finding, not a bug.

Then decide: does Tier-1 as specified in ticket 06 give a usable learning signal to a 4B
Instruct model? If not, the options already noted in the map's fog — an easier intermediate
tier, a short SFT warm start, reward reshaping, a reduced turn budget, or a larger group size —
become specifiable, and this ticket should graduate them into fresh tickets rather than silently
patching the recipe.

## Answer

<!-- append on resolution -->

# Tier-1 cold probe (issue #8) — throwaway

**Question:** does the untrained Qwen3-4B policy produce enough reward variance for GRPO to have
a gradient at all? And, folded in from [#16], does the **span** objective pool or the **gate**
pool give more usable groups?

Throwaway by construction: no tests, no abstractions, no reuse intended. The decisions it
produces belong in the issue; the code is kept only as the primary source behind them.

## Shape

| File | Where it runs | What it does |
| --- | --- | --- |
| `glosses.py` | both | property identifier → the paper's natural-language gloss |
| `tier1.py` | both | #7's generator pieces, the Eq A1–A6 reward, the prompt, the tool |
| `gen_tasks.py` | Windows `.venv` | writes `tasks_span.jsonl` / `tasks_gate.jsonl` + rejection summaries |
| `rollout.py` | WSL `~/.venvs/stsc` | cold multi-turn rollouts, plain vLLM, no trainer |
| `analyse.py` | Windows `.venv` | the five measurements #8 asks for, then #16's deciding rule |

Task files and episode records go to `data/tier1-cold-probe/`, **not** the repo tree: every task
carries `seed_smiles`, and ZINC's terms forbid redistributing structures in bulk. `data/` is
gitignored and the pre-commit hook counts structures in staged content as a second line.

## Running it

```bash
# 1. tasks (needs RDKit 2026.09.1 -- the sigma cache's provenance key)
.venv/Scripts/python.exe prototypes/tier1-cold-probe/gen_tasks.py --n 200

# 2. rollouts, one arm at a time (resumable: re-run to continue an interrupted pass)
wsl.exe -d Ubuntu-24.04 -- bash /mnt/c/Users/zhipe/run_probe.sh \
  --tasks "/mnt/d/LLM Fine Tuning/data/tier1-cold-probe/tasks_span.jsonl" \
  --out   "/mnt/d/LLM Fine Tuning/data/tier1-cold-probe/episodes_span.jsonl"

# 3. the numbers
.venv/Scripts/python.exe prototypes/tier1-cold-probe/analyse.py \
  data/tier1-cold-probe/episodes_span.jsonl data/tier1-cold-probe/episodes_gate.jsonl
```

RDKit had to be added to the WSL venv for the tool and the reward. `uv pip install --no-deps
"rdkit==2026.9.1"` — `--no-deps` matters: it leaves the `vllm==0.15.1`-pinned stack untouched
(verified afterwards: torch 2.9.1+cu128, vllm 0.15.1, transformers 4.57.6, trl 0.29.1, numpy
2.2.6 all unchanged). The Linux wheel reports `2026.09.1`, matching the Windows RDKit that built
the σ cache.

## Configuration, and why

| Knob | Value | Why |
| --- | --- | --- |
| model | `unsloth/Qwen3-4B` | the hybrid checkpoint already cached from #2. The map's "Qwen3-4B-Instruct" is this, not `Qwen3-4B-Instruct-2507`, which is not cached |
| thinking | **off** | `enable_thinking=False` pre-fills an empty `<think></think>`. The paper's reasoning channel is its own summary tags, and thinking costs ~5–10× the tokens |
| turn budget | **15** | the paper's. Episodes run the full budget; there is no early-stop signal in the paper's prompt |
| group size | 8 | #7's planned training value; #16 requires the arms share it |
| temperature | 1.0 | TRL's `GRPOConfig` default, i.e. what training would sample at. **The knob that most directly moves the headline statistic** — lower temperature means less within-group spread |
| precision | bf16 | a go/no-go on *capability* should not risk a false negative from 4-bit quantisation |
| `gpu_memory_utilization` | **computed, capped at 0.4713** | see the regulator below |
| episodes in flight | **derived from KV capacity** | see the regulator below |

## The regulator (read this before changing memory settings)

Two independent mistakes were made here and both are now guarded in code, because both look
like reasonable optimisations and neither announces itself as a fault.

**1. Utilisation was set from total VRAM, not free VRAM.** The reasoning was that cold inference
has no optimiser, no reference model and no LoRA, so the memory Unsloth's 0.4713 reserves for
training could go to KV instead — 0.70, ~22 GiB. That is wrong on this machine for a reason #2's
trap 5 states plainly: under WDDM the **Windows desktop is a live co-tenant**, and #2's own
4096-ctx runs peaked within 1–2 GiB of the card's 32.6 GiB against an ~11.5 GiB desktop. The
run flooded the desktop's memory. vLLM preallocates the entire KV cache at load, so there is no
way to give memory back mid-run: the only lever is the figure chosen before loading.

`gpu_budget()` now derives utilisation from **free** VRAM minus `--reserve-gib` (default 12),
hard-capped at **0.4713** — not a judgement call, but the figure Unsloth derives and #2 measured
as working on all twelve of its runs. Measured: 15.01 GiB to vLLM, **16.84 GiB left free**. If
the reserve cannot be honoured it **raises SystemExit** rather than proceeding, and
`--check-only` prints the whole budget while loading nothing. Both paths are verified.

**2. Every episode was kept in flight at once.** 80 episodes x ~5k tokens is roughly 4x the
measured KV budget, so vLLM preempted and recomputed continuously — it does not OOM, it just
stops making progress, which reads like a hang rather than a misconfiguration. Measured: **80
in flight finished no episode in 15 minutes**; waves of 8 finished 32 episodes in 2.9 minutes.
The wave size now comes from the KV capacity vLLM reports (43,696 tokens here), budgeting each
episode at half of `max_model_len`.

### Measured cost, under the regulator

32 episodes x 15 turns in **2.9 min** -> **545 tok/s**, 2,920 completion tokens per episode
(max 5,498). No episode exhausted its context; **7 of 480 turns** hit the 448-token per-turn cap.
The full 3,200-episode probe extrapolates to **~4.8 h**. Episode records are keyed and appended,
so a killed run resumes and partial output stays analysable.

## Deviations this probe introduces

1. **Tool-call syntax.** The paper shows `[Call the property-calculation tool on the starting
   molecule]` and never publishes a syntax. The prompt here specifies a `CALL_TOOL:` line, and
   the parser *also* accepts Qwen's native `<tool_call>` JSON, so a failure to call the tool is
   a real failure rather than a syntax mismatch.
2. **An environment turn after every message.** Chat format needs a user turn between assistant
   turns, and the paper does not publish its env transcript. The injected text is the tool
   result when there was a call, plus `[Turn k of 15 used. n remaining.]`.
3. **`AVAILABLE PROPERTIES` lists all 100 numeric identifiers.** The paper omits its own list
   "for brevity". Identical in both arms, so it cannot confound the comparison.
4. **Tool output capped** at 25 properties × 5 SMILES per call, to bound context growth.

## Corrections to #7 found while building this

`scripts/pool/properties.py:scaffold()` does not implement the recipe #7 recorded as verified.
Both faults were measured, not argued:

- It uses full `BRICSDecompose` and takes the largest **leaf**, which for the paper's published
  example gives `c1ccccc1` — benzene — not `COc1ccccc1SCC=O`. No leaf of that decomposition can
  produce the published string. Breaking a **single** BRICS bond and keeping the larger fragment
  reproduces it exactly (12 heavy atoms vs 8, #7's own numbers).
- It **deletes** the attachment dummies. Capping them with hydrogen is what the paper's example
  shows — its core is an *aldehyde* precisely because the amide nitrogen became H. Over 582
  fragments, deletion leaves 91 that fail to match their own parent; `SetAtomicNum(1)` without
  also clearing the BRICS **isotope** label yields `[5H]` and fails all 582; clearing both gives
  **0 of 582** failures.

Which of a molecule's BRICS bonds to break is not recoverable from one published example, so it
is drawn uniformly — the plain reading of "randomly generated", with the published scaffold one
of its six possible outcomes for that seed.

# RTX 5090 + WSL2 bring-up and multi-turn GRPO smoke test

Resolves [#2](https://github.com/zhipengzhu1-dotcom/10-09-2026-Small-Molecule-Design-with-Synthetic-Task-Scaling/issues/2).
Measured **2026-10-10** on the project machine. This is the basis of the spec's setup section.

Every number here was measured on this hardware. Nothing is inferred unless it says so.
The harness that produced it is a throwaway script kept outside the repo
(`~/stsc/smoke.py` in WSL, one process per configuration, writing JSON per run);
the install commands below are the reproducible part.

---

## The machine, as found

| Fact | Value |
|---|---|
| GPU | RTX 5090, 32,607 MiB, compute capability **12.0** (sm_120, Blackwell) |
| Windows driver | 610.74, CUDA UMD 13.3, WDDM |
| Windows | 11 Home 10.0.26200.9457 |
| System RAM | 63.4 GiB; **WSL2 sees 31 GiB** (default 50% cap, no `.wslconfig` present) |
| CPU | 24 cores visible to WSL |
| WSL | **already installed**: WSL 2.6.3.0, kernel 6.6.87.2, Ubuntu 24.04.5 LTS, Python 3.12.3 |
| WSL disk | 1007 GiB ext4 (`/dev/sdd`), 946 GiB free before install |
| Other distros present | `docker-desktop`, `Unsloth-Engines-7e3f92b2` (Unsloth Studio's) |

**Ticket step 1 was already done.** `wsl --install` was not needed, and CUDA passthrough already
worked: `nvidia-smi` runs inside Ubuntu-24.04 and reports the 5090. No driver work, no reboot.

**`sudo` requires a password in this distro**, so `apt` is not available to an unattended agent.
Worked around entirely: `uv` was installed to `~/.local/bin` via the standalone installer and
creates venvs without `python3.12-venv`. `cmake` and `ninja` are absent and were never needed —
every wheel installed was prebuilt. **No compilation happened at any point.**

## Step 2 — sm_120 support: verified, not assumed

`torch==2.9.1+cu128` ships **`sm_120` in its compiled arch list**
(`sm_70 sm_75 sm_80 sm_86 sm_90 sm_100 sm_120`). Each check below ran a real kernel and
validated its output, rather than only importing:

| Check | Result |
|---|---|
| `torch.cuda.get_device_capability()` | `[12, 0]` |
| bf16 4096×4096 matmul vs fp32 CPU reference | finite, max abs err 0.536 (normal for bf16) |
| `scaled_dot_product_attention` | finite |
| triton 3.5.1 JIT compile + run custom kernel | exact (max err 0.0) |
| bitsandbytes 0.50.2 `Linear4bit` forward | finite |
| bitsandbytes `AdamW8bit` step | finite |
| vLLM 0.15.1 import | ok |
| flashinfer-python 0.6.1 import | ok |

**Nothing in the stack needed a patch, a source build, or a nightly for Blackwell.** This was
the map's single largest unverified risk and it is now closed.

One benign warning, recorded for the spec: flashinfer's `tvm_ffi` prints
`Failed to JIT torch c dlpack extension, EnvTensorAllocator will not be enabled` and suggests
`pip install torch-c-dlpack-ext`. It is a performance path, not a correctness one.

## The pinned stack that works

Installed into `~/.venvs/stsc` (9.8 GiB) in ~3.5 min at ~20 MB/s. Two commands, following the
Wordle notebook's own two-phase shape (resolve, then a `--no-deps` layer on top):

```
uv pip install "vllm==0.15.1" bitsandbytes
uv pip install --upgrade --no-deps "transformers==4.57.6" "tokenizers>=0.22.0,<=0.23.0" \
    "huggingface_hub>=0.34.0,<1.0" "trl==0.29.1" unsloth unsloth_zoo
```

Resolved versions (the manifest for the spec's setup section):

| Package | Version | Package | Version |
|---|---|---|---|
| torch | 2.9.1+cu128 | unsloth | 2026.10.3 |
| torchvision | 0.24.1 | unsloth-zoo | 2026.10.3 |
| torchaudio | 2.9.1 | trl | 0.29.1 |
| vllm | 0.15.1 | transformers | 4.57.6 |
| triton | 3.5.1 | tokenizers | 0.22.2 |
| bitsandbytes | 0.50.2 | huggingface-hub | 0.36.2 |
| flashinfer-python | 0.6.1 | numpy | 2.2.6 |
| datasets | 5.0.1 | accelerate | 1.15.0 |
| peft | 0.21.2 | trackio | 0.20.2 |
| openenv-core | 0.3.0 | textarena | 0.7.4 |

`vllm==0.15.1` is what forces most of the stack: it pins `torch==2.9.1`,
`torchvision==0.24.1`, `torchaudio==2.9.1`, `flashinfer-python==0.6.1`, and
`transformers<5,>=4.56.0`.

## What broke, and the fix

1. **`ModuleNotFoundError: No module named 'datasets'`** on `import unsloth`.
   The notebook's `--no-deps` layer never installs `datasets`; Colab ships it preinstalled, so
   the notebook cannot reveal this. A local install must add `datasets`, `accelerate`, `peft`
   explicitly. Fix: install them *with* every existing pin restated as a constraint, so the
   resolver cannot walk `transformers`/`trl`/`torch` to satisfy them. This is the trap the map
   already warns about (Unsloth regex-rewrites TRL's source, so a silent TRL bump breaks GRPO).
   Side effects to expect and accept: `pandas` 3.0.6 → 2.3.3, `pillow` 12.3.0 → 11.3.0,
   `fsspec` 2026.9.0 → 2026.6.0.

2. **`uv pip install` has no `--prefer-binary` flag** (the notebook's cell-6 `pip` line uses it).
   Harmless here — nothing needed to be built — but the line must be dropped or run through
   real `pip`.

3. **`uv 0.13.0` has no `uv pip index versions` subcommand**; version discovery has to go
   through the PyPI JSON API.

4. **`TypeError: StepResult.__init__() got an unexpected keyword argument 'metadata'`**,
   raised from `env.reset()` inside the first training step. This one is worth the spec
   spelling out, because the symptom points nowhere near the cause.

   There are **two importable `openenv` packages**, and *both report `__version__ == "0.3.0"`*,
   so the version string cannot tell them apart:

   | Copy | `StepResult` fields |
   |---|---|
   | `~/vendor/OpenEnv/src/openenv` (git clone of main, `0.8.1.dev0` in `pyproject.toml`) | `observation, reward, done, **metadata**` |
   | site-packages `openenv-core==0.3.0` (PyPI; **0.3.0 is the newest release**) | `observation, reward, done` |

   OpenEnv main's `envs/textarena_env/client.py:100` constructs
   `StepResult(..., metadata=...)`, so it requires the git copy of the core.

   The trap: **`import unsloth` itself imports `openenv`.** Any `sys.path.insert` for the
   OpenEnv checkout placed *after* the Unsloth import is too late — `sys.modules['openenv']`
   is already bound to the PyPI copy, and `sys.path` cannot retroactively rebind it.
   Confirmed by bisection: identical script, `openenv` resolves to the git copy without the
   Unsloth import and to site-packages with it.

   **Fix: insert the OpenEnv `src` and `envs` paths at the very top of the file, before
   `import unsloth`.** The notebook happens to be correct here — its cell 6 does the
   `sys.path.insert` and cell 8 imports Unsloth — so this bites only when the notebook is
   restructured into a script, where Unsloth's "import me first" rule pulls in the opposite
   direction. This was our bug, not the notebook's.

   The deeper point for the spec: *the notebook's own recipe (clone OpenEnv main +
   `pip install "openenv-core>=0.2.1"`) is no longer internally consistent*, because main has
   drifted to 0.8.1.dev0 while PyPI is still 0.3.0. Our project should not depend on that
   seam at all — see "Recommendation" below.

## The notebook has changed since our research doc

`docs/research/unsloth-rl-capability.md` (2026-10-09) records the install pins as the
`--no-deps` line. The notebook's *primary* path now installs
`unsloth[base]`/`unsloth_zoo[base]` **from git main** plus a pinned `triton_kernels` commit
(`0add6826`), falling back to the `--no-deps` pins. We deliberately used the **released**
`unsloth==2026.10.3` rather than git main: reproducibility beats currency for a spec.

Two config details in the notebook that the research doc's recommendation contradicts, and
which matter for the recipe ticket (#11):

- **`beta = 0.02`, not 0.0** — so the notebook *does* load a reference model, costing VRAM.
  The research doc recommended `beta=0.0` ("no reference model loaded") on memory grounds.
  These are different runs; #11 has to pick one knowingly.
- **`enable_thinking=False`** in every `apply_chat_template` call. The paper's pipeline is
  reasoning-heavy, so this interacts directly with the map's open "reasoning-token budget" fog.
- `max_completion_length=1024` is the **whole episode**, while `max_turns=6` ×
  `max_new_tokens=256` can reach 1536 tokens — the reference config can truncate its own
  episodes. Instrumented and measured below.

## The environment: run it locally, not against the Space

The notebook points `TextArenaEnv` at a **hosted HF Space** (`openenv-wordle.hf.space`) and
itself warns the Space has "limited concurrency". That is unusable for measurement: network
latency would be folded into every seconds-per-step figure.

The OpenEnv TextArena env is a plain FastAPI app, so it runs locally with **no Docker**:

```
PYTHONPATH=$OE/envs:$OE/src TEXTARENA_ENV_ID=Wordle-v0 \
  python -m uvicorn textarena_env.server.app:app --host 127.0.0.1 --port 8000
```

Up in 8 s. Both were verified to produce identical Wordle semantics, and measured:

| Env | reset | mean step |
|---|---|---|
| **local uvicorn** | 483 ms | **1 ms** |
| hosted HF Space | 1676 ms | 21 ms |

Local is ~20× faster per step and works offline. **All measurements below use the local
server**; the hosted Space is kept only as a fidelity cross-check.

Measured env cost across a real training run: **0.1 s of environment time against 111.6 s of
generation**. The environment is free; generation is the entire bill. That is the single most
important number for the recipe ticket (#11), because it means an expensive chemistry oracle
has a real budget to spend before it becomes the bottleneck — but also that the docking
oracle (#4) is the thing to measure, since Wordle's 1 ms is not representative.

## Step 3 — the mechanism works on this hardware

**Multi-turn, tool-calling GRPO trains on the RTX 5090.** The notebook's own configuration
(Qwen3-4B, bf16 LoRA r32, 4096 ctx, `num_generations=4`, `max_completion_length=1024`,
`beta=0.02`, 6 turns, 256 tokens/turn), run against the local env with an **11.5 GiB desktop
baseline**, completed 4 trainer steps:

| Measurement | Value |
|---|---|
| **Peak GPU used, system-wide** | **31,399 MiB of 32,607** (96%; **~1.2 GiB headroom**) |
| Peak reserved by torch alone | 17.74 GiB |
| After-load / after-PEFT | 27,409 / 27,645 MiB |
| Mean step (excluding first) | **22.6 s** |
| Step times | 81.7 s (first, includes warmup), then 19.5 / 23.9 / 24.5 |
| Generation throughput | **94 tok/s** |
| Env time vs generation time | **0.1 s vs 111.6 s** |
| Turns per episode | 5.5 (of 6 allowed) |
| Episodes truncated at `max_completion` | **3 of 16** |
| Model load (warm cache) | 46.6 s (362.7 s cold, incl. 219 s weight download) |
| `train_loss` | 0.031 |

Three things to carry forward:

1. **The notebook's A100 configuration only just fits.** 1.2 GiB of headroom at a normal
   desktop baseline means bf16 r32 at 4096 ctx has no room to grow — any increase in context
   or `num_generations` should be expected to OOM in bf16. This is why the 4-bit arm matters.
2. **`max_completion_length=1024` truncates 3 of 16 episodes**, exactly as the arithmetic
   predicted (6 turns × 256 tokens = 1536 > 1024). The reference config silently clips its own
   episodes; the spec must either raise the cap or lower `max_turns`/`max_new_tokens`
   deliberately, and the map's "reasoning-token budget" fog item inherits this.
3. **94 tok/s is a batch-of-one number.** `rollout_once` calls
   (see the full matrix below for how this varies)
   `generate_rollout_completions(trainer, [prompt_text])` with a **single** prompt, so all 88
   generate calls in a step are sequential, one sequence at a time, and the GPU is idle-ish
   throughout. Batching the episodes of a group into one generate call is the obvious
   optimisation and is #11's to make — the paper's group size makes this a large factor.

## Step 4 — the measurement matrix

Twelve configurations, each a separate process, 4 trainer steps (2 for the context runs),
local env, Qwen3-4B.

### How to read the VRAM columns (important)

`nvidia-smi` reports **system-wide** memory, so its peak includes whatever the Windows desktop
was holding. The desktop's own usage **drifted from ~11.7 GiB to ~2.5 GiB during the matrix**
(the display slept and Edge released GPU memory part-way through), which makes the raw peak
column non-comparable across rows — the later rows look cheaper purely because the desktop got
out of the way.

What makes the matrix salvageable is that **Unsloth chose `gpu_memory_utilization = 47.13%` on
every single non-standby run**, identically. It derives that from total VRAM (0.4713 × 31.84 GiB
≈ 15 GiB for vLLM), *not* from free VRAM, so vLLM's budget is deterministic and reproducible —
which is exactly what a spec needs. The honest comparable column is therefore
**process footprint = peak − that run's own baseline**, cross-validated against
`torch.cuda.max_memory_reserved()`, which is baseline-independent by construction.

| config | quant | r | gens | ctx | max_comp | standby | base MiB | peak MiB | **process MiB** | torch GiB | s/step | tok/s | turns/ep | trunc |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| notebook (reference) | bf16 | 32 | 4 | 4096 | 1024 | no | 11526 | 31399 | **19873** | 17.74 | 22.6 | 94 | 5.5 | 3/16 |
| bf16_r16_g4 | bf16 | 16 | 4 | 4096 | 1024 | no | 11661 | 30738 | **19077** | 17.91 | 21.8 | 133 | 5.44 | 2/16 |
| q4_r32_g4 | 4bit | 32 | 4 | 4096 | 1024 | no | 11577 | 31328 | **19751** | 17.49 | 22.5 | 170 | 5.12 | 8/16 |
| q4_r16_g4 | 4bit | 16 | 4 | 4096 | 1024 | no | 11561 | 30570 | **19009** | 17.80 | 20.6 | 174 | 5.38 | 8/16 |
| q4_r32_g8 | 4bit | 32 | **8** | 4096 | 1024 | no | 10266 | 29591 | **19325** | 17.99 | **39.0** | 181 | 5.08 | 8/24 |
| bf16_r32_ctx8k | bf16 | 32 | 4 | 8192 | 2048 | no | 2781 | 21532 | **18751** | 17.85 | 22.1 | 137 | 5.88 | **0/8** |
| q4_r32_ctx8k | 4bit | 32 | 4 | 8192 | 2048 | no | 3243 | 22803 | **19560** | 18.80 | 20.3 | 184 | 5.38 | **0/8** |
| q4_r32_ctx16k | 4bit | 32 | 4 | 16384 | 4096 | no | 2618 | 23029 | **20411** | 18.80 | 20.8 | 182 | 5.0 | **0/8** |
| bf16_r32_ctx16k | bf16 | 32 | 4 | 16384 | 4096 | no | 3092 | 21679 | **18587** | 17.31 | 21.8 | 134 | 5.0 | **0/8** |
| **q4_r32_ctx32k** | 4bit | 32 | 4 | **32768** | 8192 | no | 3201 | 23648 | **20447** | 18.80 | **18.5** | 171 | 5.0 | **0/8** |
| q4_r32_g4_standby | 4bit | 32 | 4 | 4096 | 1024 | **yes** | 10192 | 31773 | **21581** | 28.13 | 38.0 | 59 | 4.38 | 5/16 |
| bf16_r32_g4_standby | bf16 | 32 | 4 | 4096 | 1024 | **yes** | 3446 | 31651 | **28205** | 28.12 | 32.6 | 91 | 5.62 | 4/16 |

**All twelve configurations ran to completion; none OOM'd.** Non-standby process footprint spans
a narrow 18.6–20.4 GiB across every combination of quantisation, LoRA rank, group size and
context from 4,096 to 32,768.

### What the matrix actually says

1. **The process footprint is ~19–20 GiB and essentially flat** across bf16 vs 4-bit and
   r16 vs r32. This is the headline, and it is *not* what the research doc predicted. The
   reason: Unsloth pins vLLM to ~15 GiB regardless, and vLLM **fills whatever it is given**.
   Quantisation does not shrink the total — it changes how much of that 15 GiB is left for KV
   cache (**7.14 GiB at bf16 → 11.01 GiB at 4-bit**, measured from vLLM's own log line).

   **So "4-bit to save VRAM" is the wrong model here.** 4-bit buys *KV cache and throughput*,
   not footprint. If #11 wants a smaller footprint it must pass
   `gpu_memory_utilization` explicitly; leaving it to Unsloth gets ~19–20 GiB every time.

2. **4-bit is substantially faster**: 170–184 tok/s vs 94–137 bf16, at equal or better s/step.
   That is the opposite of the usual QLoRA expectation and is worth re-measuring before being
   relied on, but it is consistent across four 4-bit runs.

3. **LoRA rank 32 → 16 saves ~700–800 MiB** (19873→19077 bf16; 19751→19009 4-bit) and costs
   nothing measurable in speed. Cheap, but small — this feeds #10 item 5.

4. **`num_generations` 4 → 8 almost exactly doubles s/step** (22.5 → 39.0) with no footprint
   change. Group size is a pure wall-clock multiplier, which is the number #11 needs for its
   arithmetic.

5. **Context is nearly free, and 8192 fixes the truncation.** Raising `max_seq_length` to 8192
   and 16384 cost only ~0.7–1.7 GiB and **drove truncation from 3–8 episodes in 16 to zero**.
   Both 8k and 16k reported an identical 18.80 GiB torch peak, because `max_model_len` only
   partitions the KV budget rather than enlarging it. **Recommendation for #11: 8192 context
   with `max_completion_length` 2048 is strictly better than the notebook's 4096/1024 — it
   fits, it is no slower, and it stops the reference config silently clipping its own
   episodes.**

6. **`UNSLOTH_VLLM_STANDBY=1` works, and is a net loss on this GPU.** It raises Unsloth's
   utilisation target from 47.13% to **80.59%** (KV cache 17.79/21.67 GiB) — so it does not
   *save* memory, it *spends* more, deferring vLLM's allocation around the training step.
   The cost is real: **s/step +44–69% and tok/s −37–65%**. It earns its place only when
   KV-starved, which at 4096–16384 context on 32 GiB we are not. The map should record this as
   measured, because Unsloth's docs present Standby as a straight win (their 14.5 GiB T4 figure
   is a *single-turn* 4B case, where the trade runs the other way).

### Largest context that fits: 32,768 — but the real limit is concurrency

The context question has a cleaner answer than expected, straight from vLLM's own startup log
rather than derived. **The KV cache is a fixed token budget**, and context length trades
against how many sequences fit in it at once:

| quant | KV budget | **KV capacity** | ctx 4096 | ctx 8192 | ctx 16384 | ctx 32768 |
|---|---|---|---|---|---|---|
| bf16 | 7.14 GB | **49,184 tokens** | 12.01x | 6.00x | 3.00x¹ | — |
| 4-bit | 11.01 GB | **79,824 tokens** | 19.49x | 9.74x | 4.87x | **2.44x** |

(vLLM's own "Maximum concurrency for N tokens per request" figures. ¹ derived from the
49,184-token budget; the others are quoted.)

**`max_seq_length` costs no memory at all.** The torch peak was *identical* — 18.803 GiB — at
8192, 16384 **and 32768**. `max_model_len` only partitions the fixed KV budget; it never
enlarges it. **The full 32,768-token native window of Qwen3-4B runs on this machine**, with
truncation at zero and s/step actually slightly *faster* (18.5 s).

This closes the map's "reasoning-token budget" fog item far more favourably than it was
written. The map assumed "a 4B model at 4-bit on 21 GB free VRAM cannot afford" the paper's
16,384 sequence / 14,000 completion. **It can** — the paper's sequence length is reachable.

The binding constraint is instead **batching**, and it is a direct instruction to #11:

- the notebook's rollout generates **one sequence per call**, so concurrency 2.44x is ample and
  **32,768 context is available today**;
- if #11 batches a group of **G = 4** into one generate call → 16,384 is the ceiling (4.87x);
- if #11 batches **G = 8** → 8,192 is the ceiling (9.74x);
- exceeding concurrency does not OOM, it makes vLLM preempt and recompute, which shows up as
  lost throughput rather than a crash — so this needs measuring, not just arithmetic, once
  batching exists.

**This is the real payoff of 4-bit: a 62% larger KV budget** (79,824 vs 49,184 tokens), which
is what buys either longer context or a wider group — not a smaller footprint.

7. **The desktop baseline is the real constraint, not the config.** Every 4096-context run
   peaked at **30.5–31.8 GiB of 32.6 GiB** when the desktop held ~11.5 GiB — i.e. **~1–2 GiB
   headroom**. The same configs at a ~3 GiB baseline peaked at 21.5–23 GiB. Nothing OOM'd, but
   the margin at a *busy* desktop is thin enough that opening more browser tabs mid-run is a
   plausible OOM. **#11 must either pin `gpu_memory_utilization` below Unsloth's default or
   state that training requires a quiet desktop.** This is the one place where the user's own
   machine habits enter the spec.

## What this means for the tickets downstream

Nothing here is a decision — #2 is a `task` ticket and these are measurements. But they are
the inputs three other tickets were explicitly waiting on, so the handover is spelled out.

**For #10 (loss + LoRA decision), item 5 — "resolve LoRA vs full FT using #2's measured VRAM":**
- LoRA r32 and r16 both run with ~19–20 GiB of footprint; r16 saves ~700–800 MiB for no
  measurable speed cost.
- **Full fine-tuning was not measured and is not plausible on this card**: LoRA already sits at
  ~19–20 GiB with vLLM colocated, and full FT of a 4B model needs optimiser state and gradients
  for all 4B parameters on top. The measurement does not *prove* full FT impossible, but it
  leaves no room for it, and #10 can treat LoRA as forced rather than chosen.
- `adamw_8bit` and bitsandbytes `Linear4bit` are both verified working on sm_120, so the
  memory-saving optimiser path #10 may want is available.

**For #11 (the scaled recipe):**
- **s/step ≈ 22.6 s** at the notebook's config, **39.0 s** at `num_generations=8`. Group size is
  a clean linear multiplier on wall-clock.
- **Generation is ~100% of the cost**; the environment was 0.1 s against 111.6 s. Budget the
  oracle (#4) against that, and note Wordle's 1 ms is not a stand-in for docking.
- **Rollouts are batch-of-one.** 88 sequential generate calls per step at 94–184 tok/s. Batching
  a group into one `generate_rollout_completions` call is the single biggest available speedup
  and interacts with the concurrency table above.
- **Use 8192 context / 2048 completion, not 4096 / 1024.** Free, no slower, and eliminates the
  truncation the reference config suffers.
- **Pin `gpu_memory_utilization` explicitly** rather than accepting Unsloth's 47.13%.
- **Do not enable `UNSLOTH_VLLM_STANDBY`** unless KV-starved; measured as a 37–65% throughput
  loss here.

**For #8 (can Qwen3-4B score above zero on Tier-1 cold):**
- The harness it needs already exists and is verified: a `rollout_func` + `env_mask` loop,
  training on this GPU, with an in-process local environment. #8 needs to swap Wordle for the
  Tier-1 task, not build machinery.
- Qwen3-4B produced **5.0–5.9 turns per episode of a 6-turn budget**, so the base model does
  engage with a multi-turn loop rather than terminating immediately. That is weak evidence
  against total format collapse, on a *much* easier task than Tier-1 — do not over-read it.

## Recommendation on the environment layer

**Drop OpenEnv for this project.** It earned its place here as the notebook's reference
implementation, and running the server locally was the right call for measurement, but as a
dependency it is a liability:

- its PyPI core (0.3.0) and its git env code (0.8.1.dev0) are mutually incompatible, with
  identical `__version__` strings;
- it must be on `sys.path` before Unsloth, for reasons nothing documents;
- it adds an HTTP hop, FastAPI, gradio and nltk to the dependency set;
- and it buys this project **nothing** — `rollout_func` is ordinary Python, and the measured
  environment cost is 0.1 s, so there is no performance argument for a server either.

A plain in-process object with `reset()` / `step()` removes the entire surface. This is a
recommendation to #11 and #7, not a decision taken here.

## Open items this ticket deliberately did not settle

- **FlashInfer is unavailable** (no `nvcc`, no `ninja`, no `libcuda.so` stub; `sudo` needs a
  password). vLLM falls back to `FLASH_ATTN`, which works. Whether installing the CUDA toolkit
  to unlock FlashInfer is worth it is unmeasured — it would need a passworded `apt` step, so it
  is a HITL task if anyone wants it.
- **`beta`**: measured at the notebook's 0.02, which loads a reference model. `beta=0.0` was
  not measured and would free VRAM. #10 item 3 owns this.
- **Throughput was measured at batch-of-one only.** Every tok/s figure here will change once
  rollouts are batched.
- **No OOM boundary was found** for the footprint itself — every configuration fitted. The
  ~1–2 GiB headroom figure at a busy desktop is the practical limit, not a measured failure.

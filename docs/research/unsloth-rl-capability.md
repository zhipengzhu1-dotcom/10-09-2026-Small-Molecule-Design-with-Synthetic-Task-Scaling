# Can Unsloth (and Unsloth Studio) do multi-turn, tool-calling RL with custom Python reward functions?

Research date: **2026-10-09**. All claims traced to primary sources (unsloth.ai docs, unslothai/unsloth + unslothai/notebooks GitHub, huggingface.co/docs/trl, docs.vllm.ai). Every claim is tagged:

- **[DOC]** = documented by Unsloth (or the project that owns the claim) on its own docs site
- **[REPO]** = Unsloth's own GitHub repo: source code, maintainer comments, issues, PRs, notebooks
- **[COMMUNITY]** = third-party / user report
- **[INFERENCE]** = my reasoning, not stated by any source

---

## TL;DR

| Question | Answer |
|---|---|
| Unsloth Studio GUI → GRPO/RL? | **No.** Train page is SFT-only (QLoRA / LoRA / Full FT). GRPO in the GUI exists only as an unmerged **draft PR #12601** (opened 2 Oct 2026, still `Draft` + `conflicts` as of 9 Oct 2026). |
| Studio GUI → custom Python reward function? | **No**, not even in the draft PR — it uses `REWARD.md` rule rewards that "contain data rather than executable code". |
| Studio → drop to Python/notebook? | **No code/notebook export.** Config export is YAML only. |
| Unsloth **library** (Core) → GRPO/GSPO/RLVR with custom Python reward funcs? | **Yes**, documented and mature. It patches TRL's `GRPOTrainer`. |
| Unsloth library → **multi-turn, tool-calling** rollouts? | **Yes, as of 15 Sep 2026** — but *only* via `rollout_func` in notebooks + a maintainer announcement. **Not documented anywhere on unsloth.ai/docs.** |
| Native Windows? | Studio/Desktop yes. **GRPO is not viable on native Windows** — Unsloth's own docs: "vLLM does not support Windows directly but only via WSL or Linux." WSL2 is the path. |
| Smallest realistic multi-turn config | ~4B model, QLoRA r=16–32, ~4096 ctx, `num_generations=4`, 24 GB. Unsloth's own multi-turn notebook asks for an **A100 (40 GB)**. |
| Better tool for the job? | **TRL v1.15.0 (2026-10-08)** has native non-experimental `tools=` / `environment_factory=` agent training and an official "1 GPU, recommended" colocate claim. Unsloth's TRL pin (`<=1.13.0`) likely excludes that API — see §3. |

---

## 1. Unsloth Studio

### What it is

Unsloth now ships in three forms **[DOC]** (https://github.com/unslothai/unsloth, README):

> "Unsloth can be used in three ways: Unsloth Desktop, the desktop app; Unsloth Studio, the web UI; or Unsloth Core, the code based version."

Studio is **[DOC]** (https://unsloth.ai/docs/new/studio):

> "an open-source, no-code web UI for training, running and exporting open models in one unified **local** interface."

Install **[DOC]** (https://unsloth.ai/docs/new/studio/install):
- macOS/Linux/WSL: `curl -fsSL https://unsloth.ai/install.sh | sh`
- Windows PowerShell: `irm https://unsloth.ai/install.ps1 | iex`
- Launch: `unsloth studio` → "This will start Unsloth on your local **8888** port." and "By default `unsloth studio` binds to `127.0.0.1` (this machine only)."

So the user's `http://localhost:8888` is the stock Studio bind.

Latest release at time of writing: **v0.1.904-beta, 2026-10-08** **[DOC]** (https://unsloth.ai/docs/new/changelog).

### What the Train page actually exposes

**[DOC]** (https://unsloth.ai/docs/new/studio/start) — the complete training surface:

- **Training method (pill selector):** `QLoRA` ("4-bit quantized base model + LoRA adapter"), `LoRA` ("Full-precision base model + LoRA adapter"), `Full Fine-tuning` ("All weights are trained"). **That is the entire list. No DPO, no ORPO, no GRPO, no RL.**
- **Model types:** Text, Vision, Audio, Embeddings
- **Datasets:** HuggingFace Hub or Local (PDF, DOCX, JSONL, JSON, CSV, Parquet); format dropdown `auto` / `alpaca` / `chatml` / `sharegpt`; column roles `instruction`, `input`, `output`, `image`
- **Core hyperparameters:** Max Steps `0`, Context Length `2048` (options 512–32768), Learning Rate `2e-4`
- **LoRA:** Rank `16` (slider 4–128), Alpha `32` (4–256), Dropout `0.05`, LoRA Variant `LoRA`/`RS-LoRA`/`LoftQ`, Target Modules `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`
- **Optimization:** Epochs `3`, Batch Size `4`, Grad Accum `8`, Weight Decay `0.01`, Optimizer `AdamW 8-bit`
- **Schedule:** LR Scheduler `linear`, Warmup `5`, Gradient Checkpointing `unsloth`, Seed `3407`, Save Steps `0`, Eval Steps `0`, Packing `false`, Train on Completions `false`
- **Logging:** W&B, TensorBoard, Log Frequency `10`
- **Config buttons:** Upload / Save (**exports YAML** with `training`, `lora`, `logging` sections) / Reset
- **Export section:** GGUF, Safetensors, LoRA. "It is not described as producing code or a notebook."

**No reward function field. No prompt-only dataset mode. No rollout/generation config. No "open in notebook" button.**

The Studio overview page lists feature headings "Execute code + heal Tool calling", "Web search upgraded", "Unsloth as an API endpoint", "No-code training", "Run models locally", "Data Recipes", "Observability", "Export / Save models", "Privacy first + Secure" **[DOC]**. Note that "Execute code + heal Tool calling" is an **inference/chat** feature (the agentic chat loop), **not** an RL training feature **[INFERENCE]**.

### Primary-source confirmation that Studio is SFT-only

**[REPO]** Issue **#8777**, "[Feature] Unsloth Studio / Desktop: add GRPO (RL) as a training method, not just SFT", opened **14 Aug 2026** by LeoBorcherding (https://github.com/unslothai/unsloth/issues/8777):

> "Unsloth Studio's Train page can only run supervised fine-tuning."
> "There is no RL path in the app."
> "the only way to do RL with Unsloth today is to leave the app and open Colab or a local Jupyter."

The issue notes the `training_type` field is a closed literal limited to LoRA/QLoRA, Full Finetuning, Continued Pretraining, and lists the missing pieces: reward functions, prompt-only dataset handling, rollout config fields, GRPO-specific metrics, and a generation backend for rollouts. Labelled "Feature request pending on roadmap". **Closed as completed by the issue author (not a maintainer) on 26 Sep 2026; no maintainer ever commented.**

**[REPO]** PR **#12601**, "Unsloth Studio / Desktop: train with DPO, ORPO and GRPO, with a rule reward library", author LeoBorcherding, description dated **3 Oct 2026**, first commits 2 Oct 2026 (https://github.com/unslothai/unsloth/pull/12601). **State: `Draft`**, 49 commits, a `conflicts` label added **9 Oct 2026**. "Awaiting requested review from danielhanchen." It would add:

- an **Objective selector (SFT, DPO, ORPO, GRPO)** on the Train page
- GRPO scored by a reward library of `REWARD.md` **rule rewards, which contain data rather than executable code**
- live RL charts, and an `rl:` section in saved training YAMLs

danielhanchen (maintainer) commented 3 Oct 2026 on failing CI checks and on 8 Oct 2026 merged `main` into the branch and self-assigned. Earlier PR **#9310** ("Unsloth Studio: add GRPO (RL) as a training method", OnePunchMonk) also exists and is not merged.

**Conclusion (Q1):** Studio's GUI **cannot** run GRPO today, and even when PR #12601 lands it will offer **rule-based declarative rewards, not arbitrary Python reward functions**, and no custom rollout/environment. There is no documented escape hatch from Studio to a notebook. **[REPO] + [INFERENCE]**

### Studio on Windows

**[DOC]** (https://unsloth.ai/docs/get-started/install/windows-installation): Studio "works on Windows out of the box" via `irm https://unsloth.ai/install.ps1 | iex`.
**[DOC]** (https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements): Studio "works directly on Windows without WSL"; Windows 10/11 64-bit + NVIDIA GPU; training on Windows needs **Visual Studio Build Tools 2022**.
**[DOC]** Sandboxing: "Unsloth uses bubblewrap on Linux, Seatbelt on macOS, and MXC on Windows" (https://unsloth.ai/docs/new/studio/sandboxing-in-unsloth).

---

## 2. Unsloth library (Core) GRPO support

### Yes — and it is a patched TRL

**[REPO]** `unsloth/models/rl.py` (main branch) imports TRL directly:

```python
from trl import __version__ as trl_version_raw
from trl.models.utils import unwrap_model_for_generation
import trl.trainer
import trl.trainer.sft_trainer as sft_trainer_module
```

It discovers trainers dynamically — `trainers = [x for x in trainers if x.endswith("_trainer")]` — and wraps `_generate_and_score_completions` for GRPO and `train` for PPO. Version gates present in the file include:

```python
if Version(trl.__version__) >= Version("0.24.0"):
# TRL >= 0.29 keeps PPO only under trl.experimental, which the trl.trainer walk above never sees.
# TRL >= 1.7 enables the aux loss whenever output_router_logits is set
```

A sibling file `unsloth/models/rl_replacements.py` does **regex-driven source rewriting of TRL's `GRPOTrainer`** — this is the mechanism, and it is version-fragile: PR **#11169** ("Do not require TRL's vision token ids in the injected GRPO prompt trim", danielhanchen) exists precisely because a regex substitution fired on TRL versions whose `GRPOTrainer` does not set the attributes the injected block reads. **[REPO]**

**PyPI:** `unsloth` latest **2026.10.3**; `requires_python = ">=3.9,<3.15"`; TRL constraint **`trl!=0.19.0,<=1.13.0,>=0.18.2`** **[REPO]** (https://pypi.org/pypi/unsloth/json).

### Algorithms documented

**[DOC]** (https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide):

- GRPO is the headline. "We support GSPO and most other new GRPO techniques."
- `loss_type` ∈ `'grpo'`, `'dr_grpo'`, `'dapo'`, `'bnpo'`, `'gspo'` — **default `"dapo"`** **[DOC]** (https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide/advanced-rl-documentation)
- PPO notebook exists ("PPO with Llama", "new PPO notebook") **[DOC]**
- RLVR / RFT / RLHF are discussed as concepts; **DPO and ORPO are not covered by the RL guide** (DPO is supported by the library generally — Unsloth's own README lists "RL, GRPO, DPO" — but the RL guide page itself does not cover them)
- Dedicated sub-pages: GSPO, FP8 RL, Memory-Efficient RL, GRPO long-context, Vision RL (VLM RL), reward hacking, FP16-vs-BF16 for RL, "Training AI Agents with RL"

### Custom Python reward functions: yes

**[DOC]** The RL guide describes rewards as functions returning numeric scores, with GSM8K examples named `correctness_reward_func`, `int_reward_func`, `soft_format_reward_func`, `strict_format_reward_func`, `xmlcount_reward_func`. It explicitly says: "Verifiers can also execute code (e.g., in Python) to validate logic, syntax, and correctness."

The strongest concrete primary evidence is the gpt-oss 2048 tutorial **[DOC]** (https://unsloth.ai/docs/models/gpt-oss-how-to-run-and-fine-tune/gpt-oss-reinforcement-learning/tutorial-how-to-train-gpt-oss-with-rl), where the reward function **executes the model's generated Python** inside a sandbox:

```python
new_strategy = create_locked_down_function(function)
steps, state = execute_strategy(new_strategy, game)
```

with rewards `function_works` (+1.0 / −0.5 / −2.0), `no_cheating` (`scores.append(1.0 if ok else -20.0)  # heavy penalty if cheating`), `strategy_succeeds` (+20.0 on reaching 2048, +2.0 if it ran but didn't, −1.0 timeout, −3.0 crash). Safety rails: `check_python_modules` (stdlib imports only), `create_locked_down_function` ("errors if globals / imports are used"), `execute_with_time_limit` ("hard wall-clock limit").

So **arbitrary Python reward functions, including ones that run a scorer or a simulator, are a first-class documented pattern.** **[DOC]**

### GRPO config surface

**[DOC]** (advanced-rl-documentation): `beta` (default 0.0 → no reference model loaded), `num_iterations`, `epsilon` (0.2), `epsilon_high` (DAPO suggests 0.28), `delta`, `importance_sampling_level` (`"token"`/`"sequence"`), `reward_weights`, `scale_rewards` (default `"group"`), `loss_type` (default `"dapo"`), `mask_truncated_completions` (**"There are some KL issues with this flag, so we recommend to disable it"**), `vllm_importance_sampling_correction` (True with fast_inference), `vllm_importance_sampling_cap` (2.0), plus generation params `temperature`, `top_p`, `top_k`, `min_p`, `repetition_penalty`, `steps_per_generation`.

Constraint to respect: **`num_generations` "Must be > 2 for GRPO to work"** and

```
effective_batch_size = steps_per_generation * num_processes * train_batch_size
unique_prompts = effective_batch_size / num_generations   # must be > 2
```

### Model families and sizes

**[DOC]** Named in RL guide / notebook index: Llama 3.1 (8B), Llama 3.2 (1B/3B), Phi-4 (14B), Mistral v0.3 (7B), Mistral Ministral 3, Qwen2.5 (3B/7B), Qwen3 (4B/8B), Qwen3.5 (4B), Qwen3-VL (8B), Qwen2.5-VL, Gemma 3 (1B/4B), Gemma 4 (E2B), DeepSeek-R1-0528-Qwen3 (8B), gpt-oss-20b, Muse Glimmer (30B).

Guidance **[DOC]**: "apply GRPO to a model at least 1.5B in parameters to correctly generate thinking tokens as smaller models may not."

Models vLLM does not support can still do RL with `fast_inference=False` **[DOC]**:

```python
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen3.5-4B",
    fast_inference=False,
)
```

### Documented VRAM for GRPO

Unsloth publishes **no GRPO-specific VRAM table**. What exists:

**General fine-tuning minimums [DOC]** (https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements) — these are **SFT**, not RL:

| Model size | QLoRA (4-bit) | LoRA (16-bit) |
|---|---|---|
| 3B | 3.5 GB | 8 GB |
| 7B | 5 GB | 19 GB |
| 8B | 6 GB | 22 GB |
| 14B | 8.5 GB | 33 GB |

**RL rules of thumb [DOC]** (RL guide):
- "With 15GB VRAM, Unsloth allows you to transform any model up to 17B parameters…"
- "Just 5GB VRAM is enough to train your own reasoning model locally (for any model with 1.5B parameters or less)."
- QLoRA 4-bit GRPO: **VRAM needed ≈ model parameter count in GB**; LoRA 16-bit needs **≥4× more**. More context ⇒ more VRAM.
- `gpt-oss-20b` GRPO on **15 GB** (free Colab).
- FP8 RL (announced **26 Nov 2025**): "Qwen3-1.7B FP8 GRPO now works on just 5GB of VRAM"; FP8 notebooks use **24GB L4** GPUs because T4 lacks FP8.

**Llama 3.1 8B, 20K context, 8 generations/prompt [DOC]** (RL guide):

| Metric | Unsloth | Standard + FA2 |
|---|---|---|
| Training memory | 42 GB | 414 GB |
| GRPO memory | 9.8 GB | 78.3 GB |
| Inference | 0 GB | 16 GB |
| KV cache (20K) | 2.5 GB | 2.5 GB |
| **Total** | **54.33 GB** (90% less) | 510.8 GB |

→ 8B GRPO at 20K context / 8 gens needs **~54 GB**, i.e. **not a 24 GB card**. **[DOC]**

**24 GB data points [DOC]** (https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide/grpo-long-context, dated **15 Jan 2026** for the ultra-long-context release):
- "On 24GB VRAM, gpt-oss reaches 20K context and 32K for Qwen3-VL-8B QLoRA"
- "Qwen3-8B GRPO reaches **110K context** on an 80GB VRAM H100 via vLLM and QLoRA"
- "gpt-oss QLoRA with **380K context** on a single 192GB NVIDIA B200"

**Memory-Efficient RL / "Unsloth Standby" [DOC]** (https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide/memory-efficient-rl) — enable with `os.environ["UNSLOTH_VLLM_STANDBY"] = "1"` before importing unsloth, plus `gpu_memory_utilization = 0.95`. Benchmarks:
- **Qwen3 4B on a T4 (16 GB): 14.5 GiB used at `vllm_gpu_util=0.95` with Standby; 40 steps in 40 min. Without Standby, 0.8 and 0.9 OOM'd.** ← best public single-consumer-GPU 4B GRPO data point
- Llama-3.1-8B QLoRA 4-bit: 47,500 context (up from 42,000)
- Qwen3-32B LoRA 16-bit: 6,144 context on 1×H100 80GB
- A100 40GB, Qwen2.5-3B-Instruct, 8 generations: 10K+ seq len with Standby vs 6K without ("TRL reaches up to 1K at the same batch size")
- Stack versions cited: **vLLM 0.10, Torch 2.8 / 2.9 nightly**, `max_lora_rank = 32`

---

## 3. Multi-turn / agentic RL

### Short answer: yes since 15 Sep 2026, via TRL's `rollout_func` — but undocumented on the docs site

#### Maintainer announcements [REPO]

Issue **#3615** "[Feature] Support for Multi Turn GRPO" (opened 19 Nov 2025 by dipta007) — https://github.com/unslothai/unsloth/issues/3615:
- shimmyshimmer, **19 Nov 2025**: "We have a 2048 GRPO notebook which mimics this interaction." … "However, yes we are working on multi turn support for GRPO coming soon :)"
- danielhanchen, **15 Sep 2026**, closing as completed: **"Multi turn GRPO is here!"** — "environment tokens are masked out of the loss so per-step and final rewards both count"; the **Openenv wordle, gpt-oss 2048, Minesweeper and NeMo-Gym notebooks** "are all end to end examples."

Issue **#2541** "[Feature] GRPO rollout by interaction with tools" (opened 15 May 2025) — https://github.com/unslothai/unsloth/issues/2541:
- danielhanchen, **15 Sep 2026**, closing as completed: **"Tool and environment rollouts for GRPO are in now!"** — the OpenEnv rollout path works with a **shared vLLM engine**, the **environment server is launched automatically**, and **tool and environment tokens are masked out of the loss**. Points to the OpenEnv Wordle GRPO and OpenEnv gpt-oss 2048 notebooks.

#### Documentation gap — important

The docs index at https://unsloth.ai/docs/llms.txt has **no page** for OpenEnv, multi-turn, tool rollouts, NeMo-Gym, Wordle, Minesweeper, or environments. The RL guide page does not mention multi-turn rollouts, tool calling, agentic RL or custom rollout functions; `advanced-rl-documentation` documents no `rollout_func`. The changelog "has no entries explicitly about reward functions or multi-turn training."

The only RL page with "agent" in the title — **"Training AI Agents with RL"** (https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide/training-ai-agents-with-rl) — **does not teach Unsloth's own multi-turn API at all. It teaches OpenPipe ART**: `pip install openpipe-art`, `art.TrainableModel(name="agent-001", project="my-agentic-task", base_model="Qwen/Qwen2.5-14B-Instruct")  # Any Unsloth-supported model`, with

```python
async def rollout(model: art.Model, scenario: Scenario) -> art.Trajectory:
    openai_client = model.openai_client()
    trajectory = art.Trajectory(
        messages_and_choices=[
    # Your agent logic here...
    return trajectory

groups = await art.gather_trajectory_groups(
    (
        art.TrajectoryGroup(rollout(model, scenario) for _ in range(8))
        for scenario in scenarios
    ),
    after_each=lambda group: ruler_score_group(
)
await model.train(groups)
```

Trajectories "also support tool calls and responses"; the page says you can "wrap your existing agent loop and use it for training". It cites **no VRAM figures** and only the 14B example model. **[DOC]**

So: Unsloth's *documented* agentic-RL story is "use OpenPipe ART on top of Unsloth." Unsloth's *actual* native multi-turn story lives only in notebooks. **[INFERENCE]**

#### The real native mechanism: `rollout_func` + `env_mask`

**[REPO]** `unslothai/notebooks/nb/Openenv_wordle_grpo.ipynb` (the canonical true-multi-turn example):

Pins:
```
"vllm==0.15.1" "torch>=2.8.0" "triton>=3.4.0" torchvision bitsandbytes "transformers==4.57.6" trackio
!uv pip install --upgrade --no-deps transformers==4.57.6 "tokenizers>=0.22.0,<=0.23.0" "huggingface_hub>=0.34.0,<1.0" trl==0.29.1 unsloth unsloth_zoo
!pip install "openenv-core[core]>=0.2.1" "huggingface_hub>=0.34.0,<1.0"
!pip install -qqq fastapi uvicorn requests open_spiel --prefer-binary
```

Config:
```python
model_name = 'unsloth/Qwen3-4B',
max_seq_length = 4096
lora_rank = 32
fast_inference = True,
load_in_4bit = False,     # i.e. bf16 LoRA, not QLoRA
num_generations = 4,
max_completion_length = 1024,
# gpu_memory_utilization: not set in this notebook
env = TextArenaEnv(base_url = wordle_url).sync()
```

Wiring: **the environment is NOT a `GRPOTrainer` kwarg.** There is no `environment=` or `env_factory=` in this notebook. The trainer gets `rollout_func = rollout_func`, and the rollout closes over a global `env`.

```python
def rollout_func(prompts, trainer):   # returns dict with keys:
    # prompt_ids, completion_ids, logprobs, env_mask,
    # correct_reward, position_reward, format_reward

def rollout_once(trainer, env, tokenizer, dataset_prompt, system_prompt, max_turns, max_new_tokens):
    # resets env; for each turn up to max_turns:
    #   rebuild chat prompt from accumulated conversation
    #   generate_rollout_completions(...)
    #   extract guess -> env.step(guess)
    #   append env feedback to the completion AND to conversation history
    # returns prompt_ids, completion_ids, logprobs, env_mask,
    #         raw_rewards, correct_reward, position_reward, model_outputs
```

Rewards are thin adapters reading values the rollout computed:
```python
def reward_correct(completions, **kwargs):
    rewards = kwargs.get("correct_reward")
    return [float(r) for r in rewards]
```
(same shape for `reward_position`, `reward_format_strict`).

Loss masking, from the notebook's own markdown: in multi-turn environments the completion contains both model tokens and environment-feedback tokens; `env_mask` is a list of 1s (model-generated) and 0s (environment), and **"The GRPOTrainer uses this mask to exclude environment tokens from the loss calculation."**

Hardware: "vLLM is not optional here" because rollouts generate through the trainer's **colocated vLLM engine**; the notebook says to "Run all on your **A100 Google Colab Pro** instance", and its metadata sets `"gpuType": "A100"`. **[REPO]**

#### What the other "agentic" notebooks actually are — caveat

- **OpenEnv gpt-oss (20B) 2048** (`OpenEnv_gpt_oss_(20B)_Reinforcement_Learning_2048_Game.ipynb`): `trl==0.22.2`, `transformers==4.57.6`, OpenEnv cloned at commit `83dda10`, `unsloth/gpt-oss-20b`, `max_seq_length = 768`, `lora_rank = 4`, `load_in_4bit = True`, `num_generations = 2`, log shows **Tesla T4, "Max memory: 14.741 GB"**, and "`load_in_16bit` will be faster but will need a 64GB GPU or more (MI300)". **It does NOT use `rollout_func`** — `reward_funcs = [function_works, no_cheating, strategy_succeeds]`. The LLM emits **one strategy function per rollout**; the *environment* is stepped many times (`while not current_state.done: openenv_process.step(action)`) **by the generated code**, not by the model turn-by-turn. This is single-turn RLVR with a code-executing verifier, **not** multi-turn agentic RL. **[REPO]**
- **NeMo-Gym Multi-Environment** (`NeMo-Gym-Multi-Environment.ipynb`): `trl==0.22.2`, `transformers==4.57.6`, `unsloth/Qwen2.5-1.5B-Instruct`, `full_finetuning = True` (LoRA commented out, `# lora_rank = 4`), `max_seq_length = 4096`, `num_generations = 8`, metadata `"gpuType": "T4"`, prose says developed on "1 H100 GPU through NVIDIA Brev". **No environment or tool object reaches the trainer** — only `reward_funcs = [reward_fn]`; each row carries `"resources_server_ref"` and `reward_fn` POSTs the finished completion to a resources server `/verify` endpoint with `"tools": []`. **Environments are used only for post-hoc reward scoring. No mid-rollout tool execution.** **[REPO]**
- Other relevant notebooks in the index **[REPO]**: `gpt_oss_(20B)_Reinforcement_Learning_GRPO_Minesweeper_Game_BF16.ipynb`, `Gemma4_(E2B)_Reinforcement_Learning_2048_Game.ipynb`, `gpt_oss_(20B)_Reinforcement_Learning_2048_Game_DGX_Spark.ipynb`, `NeMo-Gym-Sudoku.ipynb`, `Qwen3_(4B)-GRPO.ipynb`, and (SFT, not RL) `FunctionGemma_(270M)-Multi-Turn-Tool-Calling.ipynb`.

**Bottom line (Q3):** Unsloth **can** do multi-turn tool-calling RL today. The mechanism is TRL's `rollout_func` hook, with Unsloth supplying the colocated vLLM engine, and TRL supplying `generate_rollout_completions` and `env_mask` loss masking.

> **Correction (2026-10-10, from [#2](https://github.com/zhipengzhu1-dotcom/10-09-2026-Small-Molecule-Design-with-Synthetic-Task-Scaling/issues/2)):** `env_mask` is **TRL's**, not Unsloth's. Read in the installed `trl==0.29.1`: `GRPOTrainer` pops `env_mask` from the rollout's extra fields (`trl/trainer/grpo_trainer.py:1605`) and applies it as `tool_mask` for loss computation (`:2048`); `generate_rollout_completions` lives in `trl/experimental/openenv/utils.py:88`. Unsloth contributes the colocated vLLM engine and its patched trainer, not the masking. `grep -rn env_mask unsloth_zoo/` returns nothing. This matters because it means the multi-turn path is governed by the TRL pin, which is exactly the pin Unsloth's regex source-rewriting makes fragile. **Exactly one official notebook demonstrates it end-to-end** (Wordle, Qwen3-4B bf16, A100). It is **not** in the docs, **not** in Studio, and **not** in the changelog. Anyone building this is working from one notebook plus maintainer GitHub comments. **[REPO] + [INFERENCE]**

### Alternatives for single-GPU multi-turn agentic RL

#### The upstream picture: TRL is now ahead of Unsloth here

**[DOC]** HuggingFace TRL, read at **v1.15.0 (released 2026-10-08 19:26**, https://github.com/huggingface/trl/releases/tag/v1.15.0; recent chain v1.14.2 06 Oct, v1.14.1 29 Sep, v1.14.0 25 Sep, v1.13.0 10 Sep, v1.10.0 13 Aug; TRL v1.0 announced 31 Mar 2026). `GRPOTrainer` has a documented **"## Agent Training"** section (https://huggingface.co/docs/trl/v1.15.0/en/grpo_trainer) with two first-class modes:

> "For agentic tasks, it supports two modes: **tools**, where the model can call external functions but each call is stateless and independent, and **environments**, which maintain state across turns, enabling genuine multi-turn interaction where the agent's actions shape future observations."

- `tools=[multiply, async_add]` — plain Python functions; schema auto-derived from type hints + Google-style docstring; async supported; tool exceptions are fed back to the model as the tool response.
- `environment_factory=MyEnv` (a class, not an instance) — **requires `transformers>=5.2.0`**. `reset()` required, `get_reward()` optional, **every other public method is auto-exposed as a tool**. The trainer runs the loop itself: "generates a completion, parses tool calls, executes `echo()`, appends the result, and generates again, until the model stops calling tools or `max_completion_length` is reached."
- Multi-environment routing: `environment_factory={"coding": CodingEnv, "game": GameEnv}` keyed off an `environment` dataset column.
- `GRPOConfig(max_tool_calling_iterations: int | None = None)`; `max_completion_length` in multi-turn = **total tokens across the whole conversation**; metrics `tools/call_frequency`, `tools/failure_frequency`. Requires a **prefix-preserving chat template**.
- Reward signature **[DOC]**: `reward_funcs` callables must accept `prompts`, `completions`, `completion_ids`, `trainer_state`, `log_extra`, `log_metric`, and `environments` (when `environment_factory` is used) — "The easiest way to comply with this requirement is to use `**kwargs`." Sync or `async def`. Per-sample `None` excludes that function for that sample. Env-state reward pattern: `def reward_func(environments, **kwargs): return [env.reward for env in environments]`.
- `rollout_func` (the hook Unsloth's Wordle notebook uses) is documented as **"This feature is experimental and may change or be removed at any time without prior notice"**, with official guidance to prefer `environment_factory` and reserve `rollout_func` for "external agent servers where an external server owns the generation loop."
- **vLLM is optional:** `use_vllm: bool = False` is the **default**; `vllm_mode='colocate'` ("vLLM will run in the same process and share the training GPUs") vs `'server'`. Non-vLLM fallbacks: `use_transformers_continuous_batching` (needs `transformers>=5.8.0`) and `cache_implementation`.
- **Single-GPU claim, official [DOC]** (https://huggingface.co/docs/trl/main/en/openenv, Wordle example, Qwen3-1.7B, `num_generations=4`, `gradient_accumulation_steps=64`): **"Colocate mode (1 GPU, recommended) … This runs vLLM in the same process as training, requiring only a single GPU."** v1.15.0 also turns on a fused Triton LM head by default for GRPO: "Up to 6.9× longer sequences on the same GPU… At 8k tokens that is 52% to 82% less peak VRAM."
- In-repo examples: `grpo_echo`, `grpo_catch`, `grpo_wordle`, `grpo_sudoku`, `grpo_multi_env`, `grpo_browsergym`, `grpo_carla`, `async_grpo_harbor`. Environment standards that plug into the same `environment_factory` slot: **OpenEnv**, **OpenReward**, **Harbor**.
- `trl.experimental` relevant modules **[DOC]** (https://huggingface.co/docs/trl/main/en/experimental): `gfpo` (`GFPOTrainer`, `num_remains_in_group`, `group_filter_func`), `gspo_token` (`importance_sampling_level="sequence_token"` — **there is no separate `trl.experimental.gspo` page**; plain GSPO is a `loss_type`), `grpo_with_replay_buffer`, `async_grpo`, `bema_for_ref_model`. Contract: "Anything under `trl.experimental` may change or be removed in *any* release (including patch versions) without prior deprecation."
- `AsyncGRPOTrainer` (experimental, added v1.10.0, 13 Aug 2026) trains **loop-owning** harnesses: "A production coding agent harness like `opencode` or `claude-code` has its own planner, tool set, context management, and stop condition." Needs `vllm>=0.22.0`, `transformers>=5.2.0`, FSDP2 only, a vLLM **server** and E2B/Docker sandboxes → effectively ≥2 GPUs. **[DOC]**
- TRL docs state **no OS requirement anywhere** (the Installation page gives only `pip install trl`). **[DOC]**

**Critical version-compatibility inference [INFERENCE]:** Unsloth's PyPI metadata allows `trl<=1.13.0`, and its multi-turn Wordle notebook pins `trl==0.29.1` + `transformers==4.57.6`. TRL's `environment_factory` needs `transformers>=5.2.0`. **So the clean, documented, non-experimental TRL agent API (`tools=` / `environment_factory=`) is almost certainly NOT usable under Unsloth today** — Unsloth's path is the experimental `rollout_func` hook on an older TRL line. If you want TRL's native tool/environment loop, you likely have to give up Unsloth's kernels (or wait for Unsloth to widen its TRL pin).

#### Framework comparison for single-consumer-GPU multi-turn tool-calling RL

All rows below are from each project's own docs/repo; `[INFERENCE]` marks my reasoning.

| Framework | Version / date | Multi-turn tool calling | Custom Python reward | Single 24 GB GPU, sub-8B | OS (official) | Windows/WSL2 verdict |
|---|---|---|---|---|---|---|
| **HF TRL** | **v1.15.0, 2026-10-08** | **YES, native** (`tools=`, `environment_factory=`, `max_tool_calling_iterations`; experimental `rollout_func`, `AsyncGRPOTrainer`) | **YES**, documented signature, sync or async | **YES — officially "requiring only a single GPU"** (colocate, Qwen3-1.7B Wordle) | **Not stated** | **WSL2 = best.** Windows-native *architecturally* possible since `use_vllm=False` is the default — `[INFERENCE]`, never claimed or tested by HF |
| **Unsloth Core** | pip `2026.10.3` | **YES** via experimental `rollout_func` + `env_mask`; one notebook only; **undocumented** | **YES**, incl. sandboxed code-executing verifiers | **Partly** — 4B single-turn at 14.5 GiB on a T4 [DOC]; its own multi-turn notebook wants an **A100 40 GB** | Studio: Windows native. **Core GRPO: WSL/Linux** (own docs) | **WSL2.** Docs: "vLLM does not support Windows directly but only via WSL or Linux" |
| **OpenPipe ART** | `0.5.20` (pyproject; GitHub releases empty) | YES — "multi-turn agents", `art.Trajectory`, RULER auto-rewards, MCP-RL, LangGraph, OpenEnv | YES (RULER or your own) | **Unclear — no VRAM number published.** "any machine with a GPU"; Colab T4 suffices for the 2048 toy; LoRA | **Not stated** (no Linux-only claim) | **WSL2** `[INFERENCE]` — LocalBackend "runs a vLLM server and either an Unsloth or torchtune instance". Pins `unsloth==2026.3.3`, `trl==0.20.0`, `transformers==5.2.0`, `torch==2.11.0+cu128`, Python ≥3.12. Note: **"Gemma 3 does not appear to be supported for the time being."** |
| **verl** | no version on install page | **YES, richest surface.** `rollout.multi_turn=True`, `BaseTool` subclass, `@function_tool`, `tool_config_path`, `function_tool_path`, hermes format, delta tokenization masking — **SGLang only** for multi-turn | YES — tool returns can carry reward + metrics | **Officially 1 GPU @ "at least 24 GB HBM" — but with Qwen2.5-0.5B.** `[INFERENCE]` **NO** for 7–8B | **Linux** (uv workflow x86_64/aarch64, Py 3.12, CUDA ≥12.8; "uv fails on macOS") | **WSL2 only; Windows never mentioned.** SGLang needs `glibc >= 2.34` |
| **prime-rl** | no releases (2,599 commits) | **YES** via vendored `verifiers` + Environments Hub. Named: Wordle (multi-turn SFT+RL), Alphabet Sort ("multi-turn RL training via **LoRA without SFT warmup**"), Wiki Search (web-search tool use) | YES — `verifiers` `Rubric` funcs | **Partly.** "Currently, you need at least one NVIDIA GPU"; "we develop and test on NVIDIA RTX 3090/4090/5090, A100, H100, H200, and B200"; Reverse Text "can be trained on a single consumer GPU". **But the documented full RL stack check = 2 GPUs** (trainer + inference server). No VRAM figure | **Not stated**; Python 3.12 | **WSL2** `[INFERENCE]` — FSDP2 + hard vLLM dep, bash installer |
| **verifiers** (willccbb → PrimeIntellect-ai) | no releases; **v0 deprecated**, v1 current | **YES — best environment API.** `vf.Environment` → `MultiTurnEnv` (`env_response`, `max_turns=-1`) → `ToolEnv(tools=[...], max_turns=10)` → `StatefulToolEnv` (`setup_state`, `update_tool_args`). v1 harnesses include Claude Code, Codex, `bash`, `browser_use`, tools as MCP servers | **YES — this is the point.** `vf.Rubric(funcs=[...])`, per-rollout and group-level async funcs | **N/A — ships no trainer.** Docs: "We recommend using `prime-rl` for training with Verifiers environments on self-managed GPU infrastructure"; also Tinker, SkyRL, rLLM | **Not stated** | Env *authoring* is pure Python/HTTP → fine on Windows; **training inherits prime-rl's WSL2 constraint** |
| **SkyRL** | **v0.3.0, 2026-07-16** | YES — skyrl-gym tool envs (math/coding/search/SQL, Gymnasium API), skyrl-agent, "Multi-Turn Text2SQL", "Search with SkyRL", "Using Tools" | YES (Gym-style env rewards) | **Unclear — no GPU count or VRAM claim anywhere** | **Not stated** (apt commands imply Debian/Ubuntu); CUDA 13.0 + driver r580+, Py 3.12, Ray 2.57.0 | **WSL2 at best; heavy prereqs** |
| **Atropos** (NousResearch) | `0.3.0` — **ARCHIVED, read-only** | YES as *environments* (`tool_calling_server.py`: BFCL parallel tasks 10% → 46%; "deepresearch, internal tool calling") | YES — you write the env scorer | **N/A — ships no trainer and no inference engine.** No GPU needed for env dev | Not stated; **has a Windows venv command in troubleshooting** | Env authoring genuinely Windows-friendly, but **"no longer maintained" → do not adopt** |
| **Agent Lightning** (Microsoft) | **v1.0, Aug 2026** | Implied via examples (Search-R1 "multi-turn retrieval and reasoning agent", LLM-in-Sandbox, Coding Agent, AutoGen+MCP) | Yes (reward from gateway-captured calls) | **"requiring only one GPU"** for the Calc-X example; no VRAM figure | Not stated; CUDA 13.0 install example | **WSL2** `[INFERENCE]` — trainer runs verl + vLLM |
| **rLLM** | no version; "rLLM UI" blog **Mar 2026** | YES — 10+ CLI harnesses (Claude Code, Codex, mini-swe-agent), `@rllm.rollout` decorator, Harbor task dirs, Docker/Daytona/Modal sandboxes; GRPO/REINFORCE/RLOO | Yes | **Not stated.** Backends: verl ("distributed multi-GPU"), tinker ("single-machine"), fireworks | Not stated; Python ≥3.11 | **WSL2** `[INFERENCE]`. Use `rllm-org/rllm`; `agentica-project/rllm` is archived |
| **RAGEN** | **RAGEN-2, 2026-03-12** | YES — StarPO, "a unified RL framework for training multi-turn, trajectory-level agents"; 10 built-in envs + Gym interface; Echo Trap diagnostics | Yes | **Not stated** | Not stated; conda Py 3.12 | **WSL2** `[INFERENCE]` (verl submodule) |
| **AgentRL** (THUDM) | no releases; arXiv 2510.04206 | YES — multi-turn, multi-task; `group_id` keeps whole interactions together | Yes | Not stated; headline results at 32B ⇒ not consumer-targeted | Not stated | **WSL2** `[INFERENCE]` (Ray + SGLang + FSDP, verl-derived) |
| **nano-verl** | page "Last updated: 07/15/2025" | YES — "Tool Agent Loop" for multi-turn (`agent_name` → `tool_agent_loop`), SGLang default, LangGraph `RectAgentLoop` | Yes | **Not specified**; mentions multiple GPUs for load balancing | Not stated | **WSL2** `[INFERENCE]` |
| **"nanoRL"** | — | **No project by that name found.** Closest is `nanoRLHF` (hyunwoongko), an educational single-task SFT+RL pipeline, **not multi-turn agentic** | — | — | — | `[COMMUNITY]` identification |
| **NeMo-RL** (NVIDIA) | — | **Not verified.** No agentic multi-turn evidence reached in this pass | — | `[COMMUNITY]` single-GPU GRPO on Qwen2.5-1.5B reported | — | Unverified against NVIDIA's own docs |

**Ranked recommendation for this user's box [INFERENCE], built on the quotes above:**

1. **TRL v1.15.0 directly, in WSL2** — the only option with an *official* single-GPU multi-turn claim, a native non-experimental tool/environment loop, a documented reward signature, and a vLLM-free fallback. Cost: you lose Unsloth's memory kernels (see the version-pin inference above).
2. **Unsloth + `rollout_func`, in WSL2** — keeps Unsloth's VRAM wins (Standby, chunked logits, 4-bit GRPO) and there is a working reference notebook. Cost: experimental hook, zero documentation, one example, and a TRL pin that excludes TRL's newer agent API.
3. **prime-rl + verifiers** — best environment-authoring ergonomics and the only project that explicitly names **RTX 3090/4090/5090** as tested hardware, with a multi-turn LoRA-without-SFT-warmup recipe. Cost: canonical layout wants 2 GPUs.
4. **OpenPipe ART** — most ergonomic agent harness (RULER removes reward engineering) and it is what Unsloth's own "Training AI Agents with RL" page tells you to use. Cost: **zero published VRAM or OS numbers**; you validate 4–8B @ 24 GB yourself.
5. **verl / SkyRL / RAGEN / AgentRL / Agent Lightning / rLLM** — cluster-shaped. verl's own 24 GB quickstart is a **0.5B** model.
6. **Atropos — excluded, archived.**

---

## 4. Windows reality check

### Unsloth's own statements [DOC]

From https://unsloth.ai/docs/get-started/install/windows-installation:

> **"If you're using GRPO or plan to use vLLM, currently vLLM does not support Windows directly but only via WSL or Linux."**

This is the single most important sentence for the user's question. **[DOC]**

Other Windows facts **[DOC]**:
- Unsloth **Desktop** = Windows `.exe` installer. **Studio** = native, `irm https://unsloth.ai/install.ps1 | iex`, "works directly on Windows without WSL".
- **Unsloth Core** (the pip library — the only thing that can run GRPO): "For **Unsloth Core** on Windows, choose Conda, Docker, or WSL below."
- "Docker might be the easiest way for Windows users to get started with Unsloth as there is no setup needed or dependency issues."
- Troubleshooting if Docker doesn't see the GPU: "Try doing WSL".
- Conda path: `conda create --name unsloth_env python==3.12 -y` → `pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130` → `pip install unsloth`
- WSL path: `wsl.exe --install Ubuntu-24.04` → `pip install torch torchvision --force-reinstall --index-url https://download.pytorch.org/whl/cu130` → `pip install unsloth jupyter` → `jupyter notebook`
- Docker path: `NVIDIA_CONTAINER_TOOLKIT_VERSION=1.17.8-1`, `docker run -d -e JUPYTER_PASSWORD=... -p 8888:8888 -p 2222:22 --gpus all unsloth/unsloth`
- Dependency troubleshooting is manual on Windows: "Install `torch` and `triton`" (`pip install torch torchvision torchaudio triton`), "Install `xformers` manually" (verify `python -m xformers.info`), "install `bitsandbytes` and check it with `python -m bitsandbytes`", `flash-attn` offered "for Ampere GPUs". The page **does not** claim triton fails on Windows; it just tells you to install it by hand. Example run output shows **Torch 2.10.0+cu130, Triton 3.6.0, Xformers 0.0.34**.
- "GPU support for Docker containers on Windows is not automatic."
- Requirements page **[DOC]**: Python **3.11–3.13** required for training (the general requirements say `>=3.11,<3.14`; PyPI metadata says `>=3.9,<3.15` — the docs do not reconcile this). Minimum CUDA Capability 7.0. CUDA 12.4+ recommended, 12.8+ for Blackwell. "CPU only" supported for GGUF chat and Data Recipes **but not for training**.

### Unsloth's own workaround for Windows + vLLM

**[REPO]** PR **#12024**, "Studio: run vLLM and SGLang on Windows inside a private WSL2 distro", author **danielhanchen**, opened **26 Sep 2026**, **MERGED 2 Oct 2026** into `main` (commit `619cd71`, 166 commits) — https://github.com/unslothai/unsloth/pull/12024:

> "On native Windows x64 with an NVIDIA GPU, Settings > System > Inference engines no longer reads 'unsupported.'"
> "Imports a private distro `Unsloth-Engines-<hash of the Studio home>` from a pinned Ubuntu 24.04 WSL rootfs"
> "The user's own distros are never touched."

Engines launch via `wsl.exe`; Studio reaches them on `127.0.0.1` through WSL2 localhost forwarding. Marked "Experimental until validated on a real Windows + NVIDIA machine", with the UAC prompt, restart flow, GPU access inside WSL, localhost forwarding, and SGLang-in-WSL all listed as unverified.

**Note carefully:** this covers Studio's **inference** engines (chat/serving), **not** GRPO training rollouts. It is nonetheless proof from the maintainer that **Unsloth's own answer to "vLLM on Windows" is "put it in WSL2."** **[REPO] + [INFERENCE]**

### Community data point

**[COMMUNITY]** Issue #1775 "GRPO trainer without fast inference and vllm, trained for 1000 steps on Windows OS, resulting in 0 reward" — a user on Windows / RTX 2080 Ti reports (a) a native-Windows GRPO run without vLLM reaching 0 reward after 1000 steps, and (b) a WSL2 + vLLM attempt OOMing after 3 steps. One report, old GPU; treat as anecdote, not evidence that native-Windows GRPO is *numerically* broken.

### vLLM on native Windows

**[DOC]** vLLM's own installation page, https://docs.vllm.ai/en/stable/getting_started/installation/gpu.html (page dated **11 May 2026**), Requirements block:

```
OS: Linux
Python: 3.10 -- 3.13
GPU: compute capability 7.5 or higher (e.g., T4, RTX20xx, A100, L4, H100, B200, etc.)
```

and verbatim:

> **"vLLM does not support Windows natively."**
> "To run vLLM on Windows, you can use the Windows Subsystem for Linux (WSL) with a compatible Linux distribution, or use some community-maintained forks"

The latest/dev page (https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html) says the same, with `OS: Linux`, `Python: 3.11 -- 3.14`, pre-compiled CUDA 12.9 binaries, and CUDA ≥ 12.8 required for Blackwell. Neither page prints a version number; the nightly-wheel example on `latest` shows `0.23.1rc1.dev901`. **[DOC]**

### Windows verdict

| Component | Native Windows | Notes |
|---|---|---|
| Unsloth Desktop | ✅ | `.exe` installer |
| Unsloth Studio (chat, SFT training, export) | ✅ **[DOC]** | "works directly on Windows without WSL"; needs VS Build Tools 2022 |
| Studio's vLLM/SGLang **inference** engines | ⚠️ via auto-provisioned private WSL2 distro | PR #12024, merged 2 Oct 2026, "Experimental until validated on a real Windows + NVIDIA machine" |
| Unsloth Core (pip library) | ⚠️ "choose Conda, Docker, or WSL" **[DOC]** | triton/xformers/bitsandbytes/flash-attn all need manual install |
| **GRPO with vLLM rollouts (what you need)** | ❌ **[DOC]** | "vLLM does not support Windows directly but only via WSL or Linux" |
| GRPO with `fast_inference=False` | 🟡 **[INFERENCE]** | Documented as an option *for models vLLM doesn't support*; never claimed to work on Windows. Rollout generation falls back to HF `generate()` — correct but far slower, and it loses the Standby memory trick that makes 4B fit in 24 GB |

**Recommendation: run GRPO in WSL2 Ubuntu 24.04 (or the `unsloth/unsloth` Docker image on WSL2 backend).** Keep Studio on native Windows for chat/SFT/GGUF export if you like — the two can coexist. **[INFERENCE]**

---

## 5. Realistic smallest-viable config for multi-turn tool-calling RL of a <8B model on one consumer GPU

**This section is [INFERENCE]**, built from the documented numbers above. Unsloth publishes **no** VRAM figure for multi-turn/`rollout_func` GRPO.

Anchors:
- Unsloth's only real multi-turn notebook: **Qwen3-4B, bf16 LoRA r32, 4096 ctx, num_generations=4, max_completion_length=1024 → A100 (40 GB)** **[REPO]**
- Qwen3-4B single-turn GRPO with Standby: **14.5 GiB on a T4** **[DOC]**
- 8B at 20K ctx / 8 gens: **54.3 GB** **[DOC]**
- QLoRA 4-bit GRPO ≈ 1 GB per 1 B params, LoRA-16bit ≥4× that **[DOC]**

### Recommended starting point (24 GB card, e.g. RTX 4090/5090, under WSL2)

| Knob | Value | Why |
|---|---|---|
| Model | **Qwen3-4B** (or Qwen3-1.7B to de-risk first) | the only size with a published multi-turn + a published 24 GB-class data point |
| Quantization | **`load_in_4bit=True`** (QLoRA) | the Wordle notebook's bf16 needs an A100; 4-bit cuts the ~4× LoRA-16 penalty |
| LoRA rank | **16** (Studio default; 32 matches the Wordle notebook and Standby benchmarks) | r=4 is enough for the 2048 notebook; r=32 for harder tasks |
| Context / `max_seq_length` | **4096** total, `max_prompt_length` ~2048, `max_completion_length` ~1024–2048 | multi-turn transcripts grow; TRL guidance for env episodes is to raise completion length |
| `max_turns` | **4–8** | each turn appends env feedback into one completion |
| `num_generations` | **4** (hard floor >2) | Wordle uses 4; drop to 3 before dropping context |
| `per_device_train_batch_size` | 1, `gradient_accumulation_steps` 4–8 | keep `unique_prompts = effective_batch/num_generations > 2` |
| `beta` | **0.0** | documented: "no reference model loaded (lower memory, faster)" |
| Memory flags | `UNSLOTH_VLLM_STANDBY=1`, `gpu_memory_utilization=0.95`, `fast_inference=True` | documented to turn a 4B OOM into 14.5 GiB on a T4 |
| `loss_type` | `"dapo"` (default) or `"gspo"` | GSPO documented as supported |
| `mask_truncated_completions` | **False** | docs: "some KL issues with this flag, so we recommend to disable it" |
| OS | **WSL2 Ubuntu 24.04** (or Docker-on-WSL2, or native Linux) | vLLM required and not available on native Windows |
| VRAM | **24 GB workable; 40–48 GB comfortable** | 4B bf16 multi-turn needed 40 GB in Unsloth's own notebook |

### Honest verdict on 8B multi-turn

An 8B model doing multi-turn tool-calling RL on 24 GB is **not supported by any published Unsloth number**. The nearest documented points are 8B / 20K ctx / 8 gens = 54 GB, and "Qwen3-VL-8B QLoRA reaches 32K context on 24GB" (single-turn). An 8B QLoRA at ~4K context with `num_generations=3–4` and Standby is **plausible but unverified** — expect to be VRAM-bound and slow. **[INFERENCE]**

### Steps I would take, in order

1. Do it in **WSL2 Ubuntu 24.04**, not native Windows. Install `torch` cu130 + `unsloth` + `trl` + `vllm`.
2. Start from **`nb/Openenv_wordle_grpo.ipynb`** verbatim on a known-good GPU; it is the only end-to-end multi-turn reference Unsloth ships.
3. Swap `TextArenaEnv` for a plain local Python object with `.reset()` / `.step()` — `rollout_func` is ordinary Python, so an external scoring function needs no OpenEnv at all.
4. Downsize to Qwen3-4B + `load_in_4bit=True` + Standby and re-verify the reward curve before scaling context or turns.
5. Pin the stack. Unsloth patches TRL by **regex-rewriting its source** (`rl_replacements.py`), so a TRL bump can silently break the GRPO path; the Wordle notebook's own pin is `trl==0.29.1` while PyPI allows up to `trl<=1.13.0`.

---

## Explicitly NOT documented (do not assume)

- No Unsloth VRAM number for **multi-turn** GRPO at any model size.
- No Unsloth docs page on multi-turn RL, `rollout_func`, `env_mask`, OpenEnv, environments, or tool rollouts — only notebooks and GitHub comments.
- No GRPO/DPO/RL in Unsloth Studio's GUI, and no documented path from Studio to a Python notebook.
- No statement that Unsloth Core's GRPO works on **native** Windows with vLLM; the docs say the opposite.
- The RL guide never names TRL, even though the implementation is a TRL patch.
- Reward-function *signature* is not formally documented on any Unsloth docs page (only shown by example in notebooks and the 2048 tutorial).

## Source list

- https://github.com/unslothai/unsloth (README)
- https://unsloth.ai/docs (docs root; `docs.unsloth.ai` 301-redirects here) and https://unsloth.ai/docs/llms.txt (index)
- https://unsloth.ai/docs/new/studio , /studio/start , /studio/install , /studio/security , /studio/sandboxing-in-unsloth , /studio/export , /studio/data-recipe
- https://unsloth.ai/docs/new/changelog
- https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements
- https://unsloth.ai/docs/get-started/install/windows-installation
- https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide (+ /advanced-rl-documentation , /grpo-long-context , /memory-efficient-rl , /fp8-reinforcement-learning , /training-ai-agents-with-rl , /tutorial-train-your-own-reasoning-model-with-grpo)
- https://unsloth.ai/docs/models/gpt-oss-how-to-run-and-fine-tune/gpt-oss-reinforcement-learning/tutorial-how-to-train-gpt-oss-with-rl
- https://unsloth.ai/docs/get-started/unsloth-notebooks
- https://github.com/unslothai/unsloth/issues/8777 , /issues/3615 , /issues/2541 , /issues/1775
- https://github.com/unslothai/unsloth/pull/12601 , /pull/12024 , /pull/11169 , /pull/9310
- https://raw.githubusercontent.com/unslothai/unsloth/main/unsloth/models/rl.py
- https://raw.githubusercontent.com/unslothai/notebooks/main/README.md
- https://raw.githubusercontent.com/unslothai/notebooks/main/nb/Openenv_wordle_grpo.ipynb
- https://raw.githubusercontent.com/unslothai/notebooks/main/nb/OpenEnv_gpt_oss_(20B)_Reinforcement_Learning_2048_Game.ipynb
- https://raw.githubusercontent.com/unslothai/notebooks/main/nb/NeMo-Gym-Multi-Environment.ipynb
- https://pypi.org/pypi/unsloth/json
- https://huggingface.co/docs/trl/v1.15.0/en/grpo_trainer , /docs/trl/main/en/openenv , /docs/trl/main/en/async_grpo_trainer , /docs/trl/main/en/experimental , /docs/trl/en/unsloth_integration
- https://github.com/huggingface/trl/releases/tag/v1.15.0 and `docs/source/_toctree.yml` on main
- https://docs.vllm.ai/en/stable/getting_started/installation/gpu.html and /en/latest/...
- https://github.com/OpenPipe/ART , https://art.openpipe.ai/fundamentals/art-backend/
- https://verl.readthedocs.io/en/latest/sglang_multiturn/multiturn.html , /start/install.html , /start/quickstart.html
- https://github.com/PrimeIntellect-ai/prime-rl , https://docs.primeintellect.ai/verifiers (legacy/environments, legacy/training)
- https://github.com/NovaSky-AI/SkyRL , https://docs.skyrl.ai/docs/getting-started/installation
- https://github.com/NousResearch/atropos (archived) , https://github.com/microsoft/agent-lightning , https://github.com/rllm-org/rllm , https://github.com/RAGEN-AI/RAGEN , https://github.com/THUDM/AgentRL , https://nano-verl.readthedocs.io/en/latest/start/agentic_rl.html

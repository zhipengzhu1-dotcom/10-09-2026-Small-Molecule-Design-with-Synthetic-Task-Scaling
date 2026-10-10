# 01 — Environment bring-up and multi-turn GRPO smoke test

Type: task
Status: open
Blocked by: —
Map: [Synthetic Task Scaling at <8B](../map.md)

## Question

Can this machine actually run multi-turn, tool-calling GRPO on a 4B model at all — and what are
its real numbers?

This is the foundation ticket. Every compute estimate in this map is currently arithmetic, not
measurement. It is a `task` because nothing here is a decision: it is manual work that must
happen before the training recipe (ticket 10) can be decided.

Work to do:

1. **Install WSL2 Ubuntu with CUDA passthrough.** Required: vLLM, which GRPO rollouts depend on,
   does not run on native Windows. HITL — the user runs `wsl --install` and driver setup.
2. **Verify Blackwell / sm_120 support.** The GPU is an RTX 5090. Confirm the
   PyTorch + vLLM + Unsloth + triton + bitsandbytes stack actually builds and runs on sm_120,
   and pin the exact working versions. This is an unverified risk, not a known-good path —
   Unsloth's published multi-turn example ran on an A100.
3. **Run Unsloth's one working multi-turn example end to end** (`nb/Openenv_wordle_grpo.ipynb`
   — Qwen3-4B, bf16 LoRA r32, 4096 ctx, `num_generations=4`, trl==0.29.1, vllm==0.15.1). Get it
   training, not just importing. The mechanism is TRL's experimental `rollout_func` plus
   Unsloth's `env_mask`; neither is documented, so the notebook is the specification.
4. **Measure and record**, with the desktop in its normal state (~11 GB VRAM already consumed by
   Edge, Discord, VS Code etc. — do not measure on an artificially idle machine):
   - peak VRAM at 4-bit and at bf16, LoRA r16 and r32
   - the largest context length that fits
   - generation throughput (tokens/sec) under rollout batching
   - wall-clock seconds per trainer step at `num_generations` 4 and 8
   - whether `UNSLOTH_VLLM_STANDBY=1` works here and what it saves
5. **Record what broke and the fix**, version-pinned, as the basis of the spec's setup section.

## Answer

<!-- append on resolution -->

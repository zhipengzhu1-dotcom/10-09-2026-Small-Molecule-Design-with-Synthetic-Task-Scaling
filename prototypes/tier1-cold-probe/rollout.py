"""PROTOTYPE -- throwaway. Cold multi-turn rollouts of Qwen3-4B on Tier-1 tasks (issue #8).

Inference only: no trainer, no LoRA, no OpenEnv. Plain vLLM + the HF tokenizer's chat
template, which is the lightest path the #2 bring-up record leaves open and the one with
fewest moving parts.

Runs inside WSL, where vLLM lives:

    wsl.exe -d Ubuntu-24.04 -- bash /mnt/c/Users/zhipe/run_probe.sh

All episodes are kept in flight and advanced one turn at a time, so each turn is a single
large vLLM batch rather than 3,200 sequential calls -- the #2 record's 94 tok/s was a
batch-of-one artifact. Prefix caching makes the shared prompt of a task's G rollouts nearly
free on turns 2+.

Episodes are appended to the output JSONL as they finish, so an interrupted run resumes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tier1
from tier1 import parse_message, render_prompt, run_tool

TURN_NUDGE = "[Turn {used} of {budget} used. {left} remaining.]"

# The #2 bring-up record's trap 5: nvidia-smi reports memory system-wide, the Windows desktop
# is a live co-tenant under WDDM, and 4096-ctx runs peaked at 30.5-31.8 GiB of 32.6 with an
# ~11.5 GiB desktop -- 1-2 GiB of headroom. Unsloth's own derived figure was 0.4713 of TOTAL
# (~15 GiB) on every measured run, and that is known to work here. vLLM preallocates the whole
# KV cache up front, so gpu_memory_utilization is the ONLY lever: too high and the desktop
# starves, with no later chance to give memory back.
UTIL_CAP = 0.4713
MIN_UTIL = 0.30


def gpu_budget(reserve_gib, util_cap, verbose=True):
    """Pick gpu_memory_utilization from *free* VRAM, never from total.

    Returns (util, info). Raises SystemExit if the reserve cannot be honoured, which is the
    point: refusing to start beats evicting the desktop mid-run.
    """
    import torch

    free, total = torch.cuda.mem_get_info()
    gib = 1024 ** 3
    reserve = reserve_gib * gib
    allowed = free - reserve
    raw = allowed / total
    util = min(raw, util_cap)
    info = {
        "total_gib": round(total / gib, 2),
        "free_gib": round(free / gib, 2),
        "in_use_by_others_gib": round((total - free) / gib, 2),
        "reserve_gib": reserve_gib,
        "util_uncapped": round(raw, 4),
        "util_cap": util_cap,
        "util_chosen": round(util, 4),
        "vllm_budget_gib": round(util * total / gib, 2),
        "left_for_desktop_gib": round((total - util * total) / gib, 2),
    }
    if verbose:
        print("[regulator] " + json.dumps(info), flush=True)
    if util < MIN_UTIL:
        raise SystemExit(
            f"[regulator] REFUSING TO START: only {info['free_gib']} GiB free and "
            f"{reserve_gib} GiB is reserved, leaving util {raw:.3f} < {MIN_UTIL}. "
            f"Close GPU-heavy apps, or lower --reserve-gib deliberately."
        )
    return util, info


class Episode:
    __slots__ = ("task", "rollout", "messages", "turns", "n_tool_calls", "proposals",
                 "events", "done", "stop_reason")

    def __init__(self, task, rollout, system, user):
        self.task = task
        self.rollout = rollout
        self.messages = [{"role": "system", "content": system},
                         {"role": "user", "content": user}]
        self.turns = 0
        self.n_tool_calls = 0
        self.proposals = []          # every parsable SMILES it proposed, in order
        self.events = []             # one record per turn, for the format/tool statistics
        self.done = False
        self.stop_reason = None

    @property
    def key(self):
        return f"{self.task['task_id']}#{self.rollout}"


def build_waves(tasks, group_size, turn_budget, done_keys, tasks_per_wave):
    """Episodes grouped into waves that fit the KV cache.

    Keeping every episode in flight at once looks like the obvious batching win and is a trap:
    80 episodes x ~5k tokens of context is roughly 4x the measured KV budget, so vLLM preempts
    and recomputes continuously. Measured: 80-in-flight produced no finished episode in 15
    minutes. A wave sized to fit does the same total work with no recompute, and a whole task's
    group stays in one wave so prefix caching covers its shared ~1.5k-token prompt.
    """
    waves, cur = [], []
    for task in tasks:
        user = render_prompt(task, turn_budget=turn_budget)
        group = [Episode(task, g, tier1.SYSTEM_PROMPT, user) for g in range(group_size)]
        group = [e for e in group if e.key not in done_keys]
        if not group:
            continue
        cur.append(group)
        if len(cur) >= tasks_per_wave:
            waves.append([e for grp in cur for e in grp])
            cur = []
    if cur:
        waves.append([e for grp in cur for e in grp])
    return waves


def finish(ep, turn_budget):
    """Score the episode exactly as the paper does: on its final proposed molecule."""
    last = ep.events[-1] if ep.events else None
    # Requirement 3: the LAST message must carry the answer tags.
    format_ok = bool(
        last
        and last["n_answer_tags"] == 1
        and last["n_summary_tags"] == 1
        and last["answer_parses"]
    )
    final_smiles = last["answer"] if (last and last["answer_parses"]) else None
    if final_smiles is None and ep.proposals:
        # It proposed something valid earlier but not in its last message: the molecule still
        # gets scored, the format penalty still applies. Keeps r_obj and r_format independent.
        final_smiles = ep.proposals[-1]

    rec = tier1.reward(ep.task, final_smiles, ep.n_tool_calls, format_ok)
    rec_no_tool = tier1.reward(ep.task, final_smiles, ep.n_tool_calls, format_ok,
                               include_tool_penalty=False)

    n_valid_props = sum(1 for e in ep.events if e.get("tool_all_props_valid"))
    # Requirement 1 of the paper's prompt: "Molecule proposals and tool calls must be in
    # separate messages." Measured separately from r_format rather than folded into it: the
    # paper has one -0.5 penalty and does not say which of its three requirements trips it,
    # so inventing a second penalty would change the reward. Question 2 of #8 asks for this
    # number explicitly.
    n_mixed = sum(1 for e in ep.events if e["has_tool_call"] and e["n_answer_tags"] > 0)
    return {
        "key": ep.key,
        "task_id": ep.task["task_id"],
        "arm": ep.task["arm"],
        "rollout": ep.rollout,
        "objective": ep.task["objective"],
        "n_constraints": len(ep.task["constraints"]),
        "turns_used": ep.turns,
        "stop_reason": ep.stop_reason,
        "n_tool_calls": ep.n_tool_calls,
        "n_tool_calls_all_props_valid": n_valid_props,
        "tool_syntaxes": sorted({e["tool_syntax"] for e in ep.events if e.get("tool_syntax")}),
        "n_mixed_messages": n_mixed,
        "separate_messages_respected": n_mixed == 0,
        "n_proposals": len(ep.proposals),
        "n_distinct_proposals": len(set(ep.proposals)),
        "proposed_seed_unchanged": bool(
            ep.proposals and set(ep.proposals) == {ep.task["seed_smiles"]}),
        "final_smiles": final_smiles,
        "format_ok": format_ok,
        "last_message_answer_tags": last["n_answer_tags"] if last else 0,
        "last_message_summary_tags": last["n_summary_tags"] if last else 0,
        "reward": {k: v for k, v in rec.items() if k != "constraint_scores"},
        "constraint_scores": rec["constraint_scores"],
        # Reward with the tool penalty excluded. At trainer step 0 the warmup makes r_tool
        # exactly 0, so this -- not the penalised total -- is what the group would actually
        # see. Reported separately so a group cannot look "usable" purely because its
        # rollouts made different numbers of tool calls.
        "total_no_tool_penalty": rec_no_tool["total"],
        "events": ep.events,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="unsloth/Qwen3-4B")
    ap.add_argument("--group-size", type=int, default=8)
    ap.add_argument("--turn-budget", type=int, default=15)
    ap.add_argument("--max-tokens", type=int, default=448, help="per turn")
    ap.add_argument("--max-model-len", type=int, default=12288)
    ap.add_argument("--reserve-gib", type=float, default=12.0,
                    help="VRAM left untouched for the desktop and anything else on the GPU")
    ap.add_argument("--util-cap", type=float, default=UTIL_CAP,
                    help=f"hard ceiling on gpu_memory_utilization (default {UTIL_CAP}, the "
                         "value Unsloth derived and #2 measured as working)")
    ap.add_argument("--check-only", action="store_true",
                    help="print the VRAM budget and the wave size, load nothing, exit")
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--top-p", type=float, default=0.95)
    ap.add_argument("--top-k", type=int, default=50)
    ap.add_argument("--limit-tasks", type=int, default=0)
    ap.add_argument("--tasks-per-wave", type=int, default=0,
                    help="tasks in flight at once (0 = derive from the measured KV capacity)")
    ap.add_argument("--enable-thinking", action="store_true")
    args = ap.parse_args()

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    tasks = []
    for path in args.tasks:
        with open(path, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
        tasks.extend(rows[: args.limit_tasks] if args.limit_tasks else rows)
    print(f"[probe] {len(tasks)} tasks x {args.group_size} rollouts "
          f"= {len(tasks) * args.group_size} episodes, budget {args.turn_budget} turns",
          flush=True)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done_keys = set()
    if out_path.exists():
        with open(out_path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    done_keys.add(json.loads(line)["key"])
                except Exception:
                    pass
        print(f"[probe] resuming: {len(done_keys)} episodes already recorded", flush=True)

    util, budget = gpu_budget(args.reserve_gib, args.util_cap)

    if args.check_only:
        est = int(0.5 * args.max_model_len)
        print(f"[regulator] would load with gpu_memory_utilization={util:.4f}; "
              f"wave size then derived from the KV cache vLLM reports, assuming "
              f"~{est} tokens per episode.")
        return

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    llm = LLM(
        model=args.model,
        dtype="bfloat16",
        max_model_len=args.max_model_len,
        gpu_memory_utilization=util,
        enable_prefix_caching=True,
        disable_log_stats=True,
    )

    # Confirm the reserve survived the load rather than trusting the arithmetic. vLLM
    # preallocates KV up front, so if the figure is going to be wrong it is wrong here, before
    # any generation, and the run can still be abandoned cheaply.
    import torch

    free_after, total = torch.cuda.mem_get_info()
    print(f"[regulator] after load: {free_after / 1024 ** 3:.2f} GiB free of "
          f"{total / 1024 ** 3:.2f} (reserve was {args.reserve_gib} GiB)", flush=True)

    # --- size the wave to the KV cache that actually exists ---------------------------------
    # Over-admitting does not OOM: vLLM preempts and recomputes. It is a throughput cliff, and
    # a steep one -- 80 episodes in flight finished nothing in 15 minutes. An episode is
    # budgeted at half of max_model_len, the mid-run context, not its worst case.
    kv_tokens = None
    try:
        cc = llm.llm_engine.cache_config
        kv_tokens = int(cc.num_gpu_blocks * cc.block_size)
    except Exception:
        pass
    est_tokens = max(1, int(0.5 * args.max_model_len))
    if args.tasks_per_wave > 0:
        tasks_per_wave = args.tasks_per_wave
    elif kv_tokens:
        tasks_per_wave = max(1, (kv_tokens // est_tokens) // args.group_size)
    else:
        tasks_per_wave = 1
    print(f"[regulator] KV capacity {kv_tokens} tokens; episode budgeted at {est_tokens}; "
          f"{tasks_per_wave} task(s) per wave = {tasks_per_wave * args.group_size} episodes",
          flush=True)

    waves = build_waves(tasks, args.group_size, args.turn_budget, done_keys, tasks_per_wave)
    n_eps = sum(len(w) for w in waves)
    if not n_eps:
        print("[probe] nothing to do")
        return
    print(f"[probe] {n_eps} episodes in {len(waves)} waves", flush=True)
    sampling = SamplingParams(n=1, temperature=args.temperature, top_p=args.top_p,
                              top_k=args.top_k, max_tokens=args.max_tokens)

    def template(ep):
        return tokenizer.apply_chat_template(
            ep.messages, add_generation_prompt=True, tokenize=False,
            enable_thinking=args.enable_thinking)

    fh_out = open(out_path, "a", encoding="utf-8")
    t0 = time.time()
    completion_tokens = 0

    finished = 0
    for wi, episodes in enumerate(waves, 1):
        for turn in range(args.turn_budget):
            active = [e for e in episodes if not e.done]
            if not active:
                break
            prompts, keep = [], []
            for ep in active:
                text = template(ep)
                if len(tokenizer.encode(text)) > args.max_model_len - args.max_tokens:
                    ep.done, ep.stop_reason = True, "context_exhausted"
                    fh_out.write(json.dumps(finish(ep, args.turn_budget)) + "\n")
                    finished += 1
                    continue
                prompts.append(text)
                keep.append(ep)
            if not keep:
                break

            outs = llm.generate(prompts, sampling_params=sampling, use_tqdm=False)

            for ep, out in zip(keep, outs):
                text = out.outputs[0].text
                completion_tokens += len(out.outputs[0].token_ids)
                ep.messages.append({"role": "assistant", "content": text})
                ep.turns += 1

                p = parse_message(text)
                event = {
                    "turn": ep.turns,
                    "n_answer_tags": p["n_answer_tags"],
                    "n_summary_tags": p["n_summary_tags"],
                    "has_tool_call": p["has_tool_call"],
                    "tool_syntax": p["tool_syntax"],
                    "answer": p["answer"],
                    "answer_parses": p["answer_parses"],
                    "finish_reason": out.outputs[0].finish_reason,
                    "completion_tokens": len(out.outputs[0].token_ids),
                }

                if p["answer_parses"]:
                    ep.proposals.append(p["answer"])

                if p["has_tool_call"]:
                    ep.n_tool_calls += 1
                    result, stats = run_tool(p["tool_properties"] or [], p["tool_smiles"] or [])
                    event.update(tool_all_props_valid=stats["all_props_valid"], tool_stats=stats)
                    feedback = result
                else:
                    feedback = None

                ep.events.append(event)

                left = args.turn_budget - ep.turns
                if left <= 0:
                    ep.done, ep.stop_reason = True, "turn_budget"
                    fh_out.write(json.dumps(finish(ep, args.turn_budget)) + "\n")
                    finished += 1
                    continue

                nudge = TURN_NUDGE.format(used=ep.turns, budget=args.turn_budget, left=left)
                content = f"{feedback}\n\n{nudge}" if feedback is not None else nudge
                ep.messages.append({"role": "user", "content": content})
            fh_out.flush()

        for ep in episodes:
            if not ep.done:
                ep.done, ep.stop_reason = True, "loop_end"
                fh_out.write(json.dumps(finish(ep, args.turn_budget)) + "\n")
                finished += 1
        fh_out.flush()
        el = time.time() - t0
        print(f"[probe] wave {wi}/{len(waves)} done: {finished}/{n_eps} episodes, "
              f"{el / 60:.1f} min, {completion_tokens} tok ({completion_tokens / max(el, 1):.0f} tok/s), "
              f"eta {(el / finished * (n_eps - finished)) / 60:.0f} min", flush=True)
    fh_out.close()

    dt = time.time() - t0
    print(f"[probe] done in {dt / 60:.1f} min; {completion_tokens} completion tokens "
          f"({completion_tokens / max(dt, 1):.0f} tok/s) -> {out_path}", flush=True)


if __name__ == "__main__":
    main()

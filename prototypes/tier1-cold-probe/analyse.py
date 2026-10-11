"""PROTOTYPE -- throwaway. The five measurements issue #8 asks for, plus #16's arm rule.

    .venv/Scripts/python.exe prototypes/tier1-cold-probe/analyse.py \
        data/tier1-cold-probe/episodes_span.jsonl data/tier1-cold-probe/episodes_gate.jsonl
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict

import numpy as np

TOL = 1e-9


def load(paths):
    eps = []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            eps += [json.loads(line) for line in fh if line.strip()]
    return eps


def pct(n, d):
    return f"{100.0 * n / d:5.1f}%" if d else "    --"


def groups_of(eps):
    g = defaultdict(list)
    for e in eps:
        g[e["task_id"]].append(e)
    return g


def arm_report(arm, eps):
    n = len(eps)
    print(f"\n{'=' * 78}\nARM: {arm}   ({n} episodes, {len(groups_of(eps))} groups)\n{'=' * 78}")

    # --- 1. format compliance ----------------------------------------------------------------
    fmt_ok = sum(1 for e in eps if e["format_ok"])
    one_ans = sum(1 for e in eps if e["last_message_answer_tags"] == 1)
    one_sum = sum(1 for e in eps if e["last_message_summary_tags"] == 1)
    parsable = sum(1 for e in eps if e["final_smiles"] and e["reward"]["valid"])
    print("\n1. FORMAT COMPLIANCE (on the final message, as requirement 3 defines it)")
    print(f"   exactly one answer block            {pct(one_ans, n)}")
    print(f"   exactly one reasoning summary       {pct(one_sum, n)}")
    print(f"   final SMILES parses                 {pct(parsable, n)}")
    print(f"   all three (format_ok, r_format = 0) {pct(fmt_ok, n)}")

    # --- 2. tool use -------------------------------------------------------------------------
    any_tool = sum(1 for e in eps if e["n_tool_calls"] > 0)
    valid_props = sum(1 for e in eps if e["n_tool_calls_all_props_valid"] > 0)
    separate = sum(1 for e in eps if e["separate_messages_respected"])
    syn = Counter(s for e in eps for s in e["tool_syntaxes"])
    calls = [e["n_tool_calls"] for e in eps]
    print("\n2. TOOL USE")
    print(f"   called the tool at least once       {pct(any_tool, n)}")
    print(f"   >=1 call with every property valid  {pct(valid_props, n)}")
    print(f"   kept calls/proposals separate (req 1){pct(separate, n)}")
    print(f"   tool calls per episode: mean {np.mean(calls):.2f}  median {np.median(calls):.0f}  max {max(calls)}")
    print(f"   syntaxes used: {dict(syn) or 'none'}")

    # --- 3. multi-turn behaviour -------------------------------------------------------------
    turns = [e["turns_used"] for e in eps]
    props = [e["n_proposals"] for e in eps]
    distinct = [e["n_distinct_proposals"] for e in eps]
    seed_only = sum(1 for e in eps if e.get("proposed_seed_unchanged"))
    print("\n3. MULTI-TURN BEHAVIOUR")
    print(f"   turns used: mean {np.mean(turns):.2f}  median {np.median(turns):.0f}"
          f"  min {min(turns)}  max {max(turns)}")
    print(f"   stop reasons: {dict(Counter(e['stop_reason'] for e in eps))}")
    print(f"   proposals per episode: mean {np.mean(props):.2f}   distinct: mean {np.mean(distinct):.2f}")
    print(f"   only ever re-proposed the seed      {pct(seed_only, n)}")
    print(f"   single-turn episodes (collapse sig) {pct(sum(1 for t in turns if t <= 1), n)}")

    # --- 4. reward distribution: the go/no-go ------------------------------------------------
    print("\n4. REWARD DISTRIBUTION  (the go/no-go statistic)")
    grouped = groups_of(eps)
    stats = {}
    for label, key in (("with tool penalty", lambda e: e["reward"]["total"]),
                       ("tool penalty excluded (step 0)", lambda e: e["total_no_tool_penalty"])):
        spreads, sds, usable = [], [], 0
        for _, members in grouped.items():
            r = np.array([key(m) for m in members], dtype=float)
            spread = float(np.ptp(r))
            spreads.append(spread)
            sds.append(float(r.std()))
            if spread > TOL:
                usable += 1
        ng = len(grouped)
        stats[label] = (usable, ng, spreads)
        print(f"   [{label}]")
        print(f"      usable groups (any spread)       {usable}/{ng} = {pct(usable, ng)}")
        print(f"      DISCARDED, zero advantage        {ng - usable}/{ng} = {pct(ng - usable, ng)}")
        print(f"      within-group range: mean {np.mean(spreads):.4f}  median {np.median(spreads):.4f}")
        print(f"      within-group sd:    mean {np.mean(sds):.4f}  median {np.median(sds):.4f}")
    totals = np.array([e["reward"]["total"] for e in eps])
    print(f"   episode reward: mean {totals.mean():.4f}  sd {totals.std():.4f} "
          f" min {totals.min():.4f}  max {totals.max():.4f}")
    print(f"   episodes scoring above zero         {pct(int((totals > 0).sum()), n)}")

    # --- 5. objective vs constraint ----------------------------------------------------------
    r_obj = np.array([e["reward"]["r_obj"] for e in eps])
    r_con = np.array([e["reward"]["r_constraint"] for e in eps])
    print("\n5. OBJECTIVE vs CONSTRAINT DECOMPOSITION")
    print(f"   r_obj:        mean {r_obj.mean():+.4f}  sd {r_obj.std():.4f}"
          f"   nonzero {pct(int((np.abs(r_obj) > TOL).sum()), n)}"
          f"   positive {pct(int((r_obj > TOL).sum()), n)}")
    print(f"   r_constraint: mean {r_con.mean():+.4f}  sd {r_con.std():.4f}"
          f"   == 1.0 {pct(int((r_con >= 1 - TOL).sum()), n)}")
    collapse = int(((np.abs(r_obj) <= TOL) & (r_con >= 0.999)).sum())
    print(f"   mode-collapse signature (r_obj = 0 AND all constraints met) {pct(collapse, n)}")

    # r_obj by objective kind -- #16's secondary, reported-but-not-deciding number
    print("\n   r_obj movement by objective kind (#16's secondary report):")
    for kind in ("integer", "continuous"):
        sel = [e for e in eps if e["objective"]["kind"] == kind]
        if not sel:
            continue
        v = np.array([e["reward"]["r_obj"] for e in sel])
        print(f"      {kind:10s} n={len(sel):4d}  nonzero {pct(int((np.abs(v) > TOL).sum()), len(sel))}"
              f"  mean {v.mean():+.4f}  max {v.max():+.4f}")

    return stats


def main():
    paths = sys.argv[1:]
    if not paths:
        raise SystemExit(__doc__)
    eps = load(paths)
    by_arm = defaultdict(list)
    for e in eps:
        by_arm[e["arm"]].append(e)

    per_arm = {arm: arm_report(arm, rows) for arm, rows in sorted(by_arm.items())}

    if {"span", "gate"} <= set(per_arm):
        print(f"\n{'=' * 78}\n#16's DECIDING COMPARISON\n{'=' * 78}")
        key = "tool penalty excluded (step 0)"
        shares = {}
        for arm in ("span", "gate"):
            usable, ng, _ = per_arm[arm][key]
            shares[arm] = 100.0 * usable / ng if ng else 0.0
            print(f"   {arm:5s}: usable-group share {shares[arm]:5.1f}%  ({usable}/{ng})")
        delta = shares["span"] - shares["gate"]
        print(f"\n   span - gate = {delta:+.1f} percentage points")
        print("   Rule: adopt span unless it is MORE THAN 10 points below gate. Ties to span.")
        if delta > -10.0:
            print("\n   => ADOPT THE SPAN ARM. #7's deviation #1 (integer sigma >= 2.5 gate) is WITHDRAWN.")
        else:
            print("\n   => ADOPT THE GATE ARM. #7's deviation #1 STANDS.")
        if abs(delta) < 3.0:
            print("   NOTE: within 3 points -- #16 says re-check once #19's 13 oe_* columns land.")


if __name__ == "__main__":
    main()

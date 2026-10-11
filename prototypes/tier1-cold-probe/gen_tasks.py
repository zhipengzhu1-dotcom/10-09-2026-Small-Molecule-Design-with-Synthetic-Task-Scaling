"""PROTOTYPE -- throwaway. Generate the two task samples issue #16 asked #8 to compare.

Run on Windows, where RDKit is 2026.09.1 (the sigma cache's provenance key):

    .venv/Scripts/python.exe prototypes/tier1-cold-probe/gen_tasks.py --n 200

Writes to data/tier1-cold-probe/ -- NOT the repo tree -- because every task carries
seed_smiles, and ZINC's terms forbid redistributing structures in bulk. data/ is gitignored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from rdkit import Chem

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tier1
from tier1 import KIND, NAMES, SIZE_MONOTONE

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "tier1-cold-probe"
POOL_TSV = REPO / "data" / "pool" / "pool.tsv"
POOL_PARQUET = REPO / "data" / "pool" / "pool_properties.parquet"

GENERATOR_VERSION = "cold-probe-1"


def load_pool():
    table = pq.read_table(POOL_PARQUET)
    zinc_ids = [str(v) for v in table.column("zinc_id").to_pylist()]
    matrix = np.column_stack([table.column(n).to_numpy(zero_copy_only=False).astype("float64") for n in NAMES])
    smiles = {}
    with open(POOL_TSV, encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            zid, smi = line.rstrip("\n").split("\t")
            smiles[zid] = smi
    return zinc_ids, matrix, smiles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200, help="tasks per arm")
    ap.add_argument("--seed", type=int, default=20261011)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    sigma, rho, rho_ix = tier1.load_caches()
    pools, constraint_pool = tier1.arm_pools(sigma)
    zinc_ids, matrix, smiles_by_id = load_pool()
    prop_ix = {n: i for i, n in enumerate(NAMES)}

    print(f"objective pools: span={len(pools['span'])}  gate={len(pools['gate'])}")
    print(f"constraint pool: {len(constraint_pool)}   seeds: {len(zinc_ids)}")

    def collinear(a, b):
        if a not in rho_ix or b not in rho_ix:
            return False
        return abs(float(rho[rho_ix[a], rho_ix[b]])) > 0.95

    for arm, objective_pool in pools.items():
        rng = random.Random(args.seed + (0 if arm == "span" else 1))
        rejections = Counter()
        tasks = []
        attempts = 0
        while len(tasks) < args.n:
            attempts += 1
            if attempts > args.n * 400:
                raise SystemExit(f"{arm}: generator not converging; {rejections}")

            obj_name = objective_pool[rng.randrange(len(objective_pool))]
            direction = rng.choice(["maximize", "minimize"])
            obj_stats = sigma[obj_name]

            # --- seed-only redraw loop (#16 decision 4) -------------------------------------
            task = None
            for _ in range(500):
                si = rng.randrange(len(zinc_ids))
                zid = zinc_ids[si]
                seed_smiles = smiles_by_id.get(zid)
                if not seed_smiles:
                    continue
                row = matrix[si]
                y_ref = row[prop_ix[obj_name]]
                if not np.isfinite(y_ref):
                    rejections["seed_objective_nonfinite"] += 1
                    continue

                # Test 1: saturation, read inclusively (#16).
                if direction == "maximize" and y_ref >= obj_stats["p95"]:
                    rejections["test1_saturated"] += 1
                    continue
                if direction == "minimize" and y_ref <= obj_stats["p5"]:
                    rejections["test1_saturated"] += 1
                    continue

                mol = Chem.MolFromSmiles(seed_smiles)
                if mol is None:
                    rejections["seed_unparsable"] += 1
                    continue
                core = tier1.brics_scaffold(mol, rng)
                if not core:
                    rejections["no_brics_bond"] += 1
                    continue
                core_mol = Chem.MolFromSmiles(core)
                if core_mol is None or not mol.HasSubstructMatch(core_mol, useChirality=False):
                    rejections["scaffold_not_contained"] += 1
                    continue

                # Test 3: scaffold floor on a minimised size-monotone objective.
                if direction == "minimize" and obj_name in SIZE_MONOTONE:
                    core_vals = tier1.props_of(Chem.MolToSmiles(core_mol))
                    if core_vals is None:
                        rejections["scaffold_unscorable"] += 1
                        continue
                    if (y_ref - core_vals[prop_ix[obj_name]]) < 0.26 * obj_stats["sigma"]:
                        rejections["test3_scaffold_floor"] += 1
                        continue

                # --- constraints -------------------------------------------------------------
                n_con = rng.randint(2, 4)
                chosen: list[str] = []
                for _ in range(400):
                    if len(chosen) == n_con:
                        break
                    cand = constraint_pool[rng.randrange(len(constraint_pool))]
                    if cand in chosen or cand == obj_name:
                        continue
                    if collinear(cand, obj_name) or any(collinear(cand, c) for c in chosen):
                        continue
                    if not np.isfinite(row[prop_ix[cand]]):
                        continue
                    chosen.append(cand)
                if len(chosen) != n_con:
                    rejections["constraint_draw_failed"] += 1
                    continue
                if not any(KIND[c] == "continuous" for c in chosen):
                    # Sampler rule 1: at least one continuous constraint per task.
                    rejections["no_continuous_constraint"] += 1
                    continue

                perturb_ix = rng.randrange(n_con)
                constraints = []
                ok = True
                for j, cname in enumerate(chosen):
                    v = float(row[prop_ix[cname]])
                    s_i = sigma[cname]["sigma"]
                    perturbed = j == perturb_ix
                    if KIND[cname] == "integer":
                        iv = int(round(v))
                        if not perturbed:
                            con = {"property": cname, "kind": "integer", "op": "==",
                                   "bound": iv, "perturbed": False, "sigma_i": s_i}
                        else:
                            up = rng.random() < 0.5 or iv <= 0  # never perturb below 0
                            if up:
                                con = {"property": cname, "kind": "integer", "op": ">=",
                                       "bound": iv + 1, "render_against": iv,
                                       "perturbed": True, "sigma_i": s_i}
                            else:
                                con = {"property": cname, "kind": "integer", "op": "<=",
                                       "bound": iv - 1, "render_against": iv,
                                       "perturbed": True, "sigma_i": s_i}
                    else:
                        if s_i <= 0:
                            ok = False
                            break
                        h = rng.uniform(0.25, 0.75) * s_i
                        lo, hi = v - h, v + h
                        if perturbed:
                            delta = rng.uniform(0.05, 0.2) * s_i
                            if rng.random() < 0.5:
                                lo, hi = v + delta, v + delta + 2 * h  # seed just below the range
                            else:
                                lo, hi = v - delta - 2 * h, v - delta  # seed just above it
                        con = {"property": cname, "kind": "continuous", "lo": lo, "hi": hi,
                               "perturbed": perturbed, "sigma_i": s_i}
                    constraints.append(con)
                if not ok:
                    rejections["degenerate_sigma_constraint"] += 1
                    continue

                # Test 4: scaffold alone already breaks a size-monotone upper bound.
                core_canon = Chem.MolToSmiles(core_mol)
                core_vals = tier1.props_of(core_canon)
                broke = False
                for con in constraints:
                    if con["property"] not in SIZE_MONOTONE or core_vals is None:
                        continue
                    cv = core_vals[prop_ix[con["property"]]]
                    upper = con.get("hi") if con["kind"] == "continuous" else (
                        con["bound"] if con["op"] in ("<=", "==") else None)
                    if upper is not None and cv > upper:
                        broke = True
                        break
                if broke:
                    rejections["test4_scaffold_upper_bound"] += 1
                    continue

                constraints.append({"kind": "scaffold", "core": core_canon, "perturbed": False})

                # Test 5: pool-satisfiability, vectorised over the 1 M descriptor matrix.
                mask = np.ones(len(zinc_ids), dtype=bool)
                for con in constraints:
                    if con["kind"] == "scaffold":
                        continue
                    col = matrix[:, prop_ix[con["property"]]]
                    if con["kind"] == "integer":
                        if con["op"] == "==":
                            mask &= np.isclose(col, con["bound"])
                        elif con["op"] == ">=":
                            mask &= col >= con["bound"]
                        else:
                            mask &= col <= con["bound"]
                    else:
                        mask &= (col >= con["lo"]) & (col <= con["hi"])
                    if not mask.any():
                        break
                n_satisfying = int(mask.sum())
                if n_satisfying == 0:
                    rejections["test5_pool_unsatisfiable"] += 1
                    continue

                # The invariant #7 makes checkable: the seed violates exactly the perturbed one.
                canon_seed = Chem.MolToSmiles(mol)
                scores = [tier1.score_constraint(c, canon_seed) for c in constraints]
                violated = [i for i, s in enumerate(scores) if s < 1.0]

                task = {
                    "task_id": f"{arm}-{len(tasks):04d}",
                    "arm": arm,
                    "seed_zinc_id": zid,
                    "seed_smiles": canon_seed,
                    "objective": {"property": obj_name, "direction": direction,
                                  "y_ref": float(y_ref), "tau": obj_stats["sigma"],
                                  "kind": KIND[obj_name]},
                    "constraints": constraints,
                    "seed_constraint_scores": scores,
                    "seed_violated_indices": violated,
                    "n_pool_satisfying": n_satisfying,
                    "provenance": {"pool_sha256": "92c62a4e", "rdkit_version": Chem.rdBase.rdkitVersion,
                                   "sample_seed": args.seed, "generator_version": GENERATOR_VERSION},
                }
                break

            if task is None:
                rejections["seed_redraw_exhausted"] += 1
                continue
            tasks.append(task)

        path = OUT / f"tasks_{arm}.jsonl"
        with open(path, "w", encoding="utf-8") as fh:
            for t in tasks:
                fh.write(json.dumps(t) + "\n")

        # --- the rejection summary #7 asked for, which is what makes test 5 actionable ------
        obj_counts = Counter(t["objective"]["property"] for t in tasks)
        int_share = sum(1 for t in tasks if t["objective"]["kind"] == "integer") / len(tasks)
        viol = Counter(len(t["seed_violated_indices"]) for t in tasks)
        summary = {
            "arm": arm,
            "n_tasks": len(tasks),
            "attempts": attempts,
            "objective_pool_size": len(objective_pool),
            "rejections": dict(rejections),
            "integer_objective_share": round(int_share, 4),
            "distinct_objectives_drawn": len(obj_counts),
            "seed_violated_count_histogram": dict(sorted(viol.items())),
            "median_pool_satisfying": int(np.median([t["n_pool_satisfying"] for t in tasks])),
        }
        (OUT / f"rejections_{arm}.json").write_text(json.dumps(summary, indent=2))
        print(f"\n[{arm}] {len(tasks)} tasks in {attempts} attempts -> {path}")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

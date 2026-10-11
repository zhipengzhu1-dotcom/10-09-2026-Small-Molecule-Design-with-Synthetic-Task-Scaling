"""PROTOTYPE -- throwaway. Does the oracle fit inside the RL loop?

Separates the three ways to spend the cost: one process per molecule, one process
per rollout group (batched multi-model SDF), and many processes in parallel.
"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent))
from PROTOTYPE_dock_oracle import (  # noqa: E402
    gen_analogs, embed_to_template, smina_score, smina_score_batch,
)
from rdkit import Chem  # noqa: E402

STRUCT = Path(os.environ["STRUCT_DIR"])
BINS = Path(os.environ["BIN_DIR"])
SMINA = str(BINS / "smina")


def _embed_one(args):
    smi, lig_sdf = args
    core = next(Chem.SDMolSupplier(lig_sdf, removeHs=False))
    t0 = time.perf_counter()
    m, err = embed_to_template(smi, core)
    return time.perf_counter() - t0, err


def _dock_one(args):
    sdf, rec, lig = args
    s, dt, err = smina_score(SMINA, rec, lig, sdf, "minimize", "vinardo", cpu=1)
    return dt, err


def main(n_per=30):
    manifest = json.loads((STRUCT / "manifest.json").read_text())
    work = Path(os.environ["WORK_DIR"])
    work.mkdir(parents=True, exist_ok=True)

    # ---- build embedded poses once; docking timings below exclude embedding ----
    per_target = {}
    for pid, info in manifest.items():
        core = next(Chem.SDMolSupplier(info["ligand"], removeHs=False))
        singles, mols = [], []
        for smi, sub, site in gen_analogs(core, n_per):
            m, err = embed_to_template(smi, core)
            if err:
                continue
            p = work / f"{pid}_{len(mols)}.sdf"
            w = Chem.SDWriter(str(p)); w.write(m); w.close()
            singles.append(str(p)); mols.append(m)
        batch = work / f"{pid}_batch.sdf"
        w = Chem.SDWriter(str(batch))
        for m in mols:
            w.write(m)
        w.close()
        per_target[pid] = dict(info=info, singles=singles, batch=str(batch), n=len(mols))
        print(f"{pid}: {len(mols)} poses staged")

    total_mols = sum(v["n"] for v in per_target.values())
    print(f"\n{total_mols} poses total\n" + "=" * 70)

    # ---- A. one smina process per molecule, sequential ----
    t0 = time.perf_counter()
    dts = []
    for pid, v in per_target.items():
        for s in v["singles"]:
            dt, err = _dock_one((s, v["info"]["receptor"], v["info"]["ligand"]))
            dts.append(dt)
    wall_a = time.perf_counter() - t0
    print(f"A. per-molecule process, sequential : {wall_a:7.2f}s total, "
          f"{wall_a / total_mols * 1000:6.1f} ms/mol  (median call {median(dts) * 1000:.1f} ms)")

    # ---- B. one smina process per target (batched multi-model SDF) ----
    t0 = time.perf_counter()
    nb = 0
    for pid, v in per_target.items():
        scores, dt, err = smina_score_batch(
            SMINA, v["info"]["receptor"], v["info"]["ligand"], v["batch"],
            "minimize", "vinardo", cpu=1)
        nb += len(scores)
        print(f"   batch {pid}: {len(scores)}/{v['n']} scores in {dt:.2f}s "
              f"({dt / max(1, len(scores)) * 1000:.1f} ms/mol){' ERR=' + str(err) if err else ''}")
    wall_b = time.perf_counter() - t0
    print(f"B. batched per target, --cpu 1      : {wall_b:7.2f}s total, "
          f"{wall_b / total_mols * 1000:6.1f} ms/mol   ({nb} scores)")

    # ---- C. batched, smina's own threading ----
    t0 = time.perf_counter()
    for pid, v in per_target.items():
        smina_score_batch(SMINA, v["info"]["receptor"], v["info"]["ligand"],
                          v["batch"], "minimize", "vinardo", cpu=8)
    wall_c = time.perf_counter() - t0
    print(f"C. batched per target, --cpu 8      : {wall_c:7.2f}s total, "
          f"{wall_c / total_mols * 1000:6.1f} ms/mol")

    # ---- D. many single-molecule processes in parallel ----
    jobs = [(s, v["info"]["receptor"], v["info"]["ligand"])
            for v in per_target.values() for s in v["singles"]]
    for workers in (4, 12, 24):
        t0 = time.perf_counter()
        with ProcessPoolExecutor(max_workers=workers) as ex:
            list(ex.map(_dock_one, jobs))
        wall = time.perf_counter() - t0
        print(f"D. per-molecule, {workers:2d} processes      : {wall:7.2f}s total, "
              f"{wall / total_mols * 1000:6.1f} ms/mol  ({total_mols / wall:5.1f} mol/s)")

    # ---- E. embedding in parallel (RDKit is the other half of the cost) ----
    ejobs = []
    for pid, v in per_target.items():
        core = next(Chem.SDMolSupplier(v["info"]["ligand"], removeHs=False))
        for smi, _, _ in gen_analogs(core, n_per):
            ejobs.append((smi, v["info"]["ligand"]))
    for workers in (1, 12, 24):
        t0 = time.perf_counter()
        if workers == 1:
            [_embed_one(j) for j in ejobs]
        else:
            with ProcessPoolExecutor(max_workers=workers) as ex:
                list(ex.map(_embed_one, ejobs))
        wall = time.perf_counter() - t0
        print(f"E. ConstrainedEmbed, {workers:2d} processes  : {wall:7.2f}s total, "
              f"{wall / len(ejobs) * 1000:6.1f} ms/mol  ({len(ejobs) / wall:5.1f} mol/s)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 30)

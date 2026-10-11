"""One RDKit pass over the pool, emitting the Parquet table and the three cached statistics.

The three statistics all come from the same pass, under one provenance key, because the Tier-1
reward is defined in terms of them:

  sigma        per-property population standard deviation (ddof=0), the tau of Eq A2 and the
               sigma_i of Eq A6. The whole reward scale.
  spearman     the 101x101 rank-correlation matrix, for issue #7's collinearity rule (no
               constraint with |rho| > 0.95 against the objective or another constraint).
  quantiles    per-property 1st/5th/95th/99th percentiles, for issue #7's saturation test.

They must never be regenerated mid-sweep: doing so silently rescales every reward and
invalidates every cross-arm comparison. See the map's Known traps.

Drop rules, from docs/research/zinc-seed-source.md section 5.2 rule 6:
  * sigma below 1e-8 (or sigma/|mean| < 1e-6) -> dropped:degenerate; tau = 0 divides by zero.
  * any non-finite value anywhere -> dropped:nonfinite.
Both are recorded with counts rather than applied silently, so the gate can be revisited with
evidence.

Usage:
  python compute_caches.py <pool.tsv> <pool_provenance.json> <parquet-out> <cache-dir>
                           [--workers N] [--timing-sample 5000]
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import properties as P  # noqa: E402

CHUNK = 2000
DEGENERATE_ABS = 1e-8
DEGENERATE_REL = 1e-6
TAUTOMER_CAP = 1000


def _worker(smiles_chunk):
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    rows = np.empty((len(smiles_chunk), len(P.NAMES)), dtype=np.float32)
    failed = []
    for i, smi in enumerate(smiles_chunk):
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            rows[i, :] = np.nan
            failed.append(i)
            continue
        rows[i, :] = P.compute(mol)
    return rows, len(failed)


def descriptor_pass(pool_tsv: str, workers: int):
    ids: list[str] = []
    smiles: list[str] = []
    with open(pool_tsv, encoding="utf-8") as fh:
        fh.readline()
        for line in fh:
            zid, smi = line.rstrip("\n").split("\t")
            ids.append(zid)
            smiles.append(smi)
    n = len(smiles)
    print(f"pool: {n:,} molecules, {len(P.NAMES)} numeric properties", flush=True)

    values = np.empty((n, len(P.NAMES)), dtype=np.float32)
    chunks = [smiles[i:i + CHUNK] for i in range(0, n, CHUNK)]
    t0 = time.perf_counter()
    at = 0
    unparsed = 0
    with Pool(workers) as pool:
        for k, (rows, nfail) in enumerate(pool.imap(_worker, chunks), 1):
            values[at:at + len(rows)] = rows
            at += len(rows)
            unparsed += nfail
            if k % 50 == 0 or at == n:
                el = time.perf_counter() - t0
                print(f"  {at:,}/{n:,}  {el:6.0f}s  {at / max(el, 1e-9):7.0f} mol/s  "
                      f"eta {(n - at) / max(at / max(el, 1e-9), 1e-9):5.0f}s", flush=True)
    elapsed = time.perf_counter() - t0
    print(f"descriptor pass: {elapsed:.0f}s  ({elapsed / n * 1000:.3f} ms/molecule, "
          f"{workers} workers), unparseable {unparsed}")
    return ids, smiles, values, elapsed, unparsed


def _timing_sample(smiles: list[str], k: int):
    """Per-property cost on a real subsample, to name the pathologically slow ones."""
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    rng = np.random.default_rng(0)
    pick = rng.choice(len(smiles), size=min(k, len(smiles)), replace=False)
    mols = [Chem.MolFromSmiles(smiles[i]) for i in pick]
    mols = [m for m in mols if m is not None]
    out = {}
    for name, fn in P._GETTERS:
        t = time.perf_counter()
        for m in mols:
            fn(m)
        out[name] = (time.perf_counter() - t) / len(mols) * 1000.0
    return out, len(mols)


def spearman(values: np.ndarray, usable: list[int]) -> np.ndarray:
    """Rank-transform each usable column (ties averaged) then Pearson on the ranks."""
    from scipy.stats import rankdata

    n = values.shape[0]
    ranks = np.empty((n, len(usable)), dtype=np.float64)
    for j, col in enumerate(usable):
        ranks[:, j] = rankdata(values[:, col].astype(np.float64), method="average")
    ranks -= ranks.mean(axis=0)
    sd = ranks.std(axis=0)
    sd[sd == 0] = 1.0
    ranks /= sd
    return (ranks.T @ ranks) / n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pool_tsv")
    ap.add_argument("pool_provenance")
    ap.add_argument("parquet_out")
    ap.add_argument("cache_dir")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--timing-sample", type=int, default=5000)
    args = ap.parse_args()

    with open(args.pool_provenance, encoding="utf-8") as fh:
        prov = json.load(fh)
    os.makedirs(args.cache_dir, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.parquet_out)), exist_ok=True)

    import rdkit

    ids, smiles, values, elapsed, unparsed = descriptor_pass(args.pool_tsv, args.workers)
    n = values.shape[0]

    # --- Parquet table ---------------------------------------------------------------------
    table = pa.table(
        {"zinc_id": pa.array(ids, type=pa.string()),
         **{name: pa.array(values[:, j], type=pa.float32())
            for j, name in enumerate(P.NAMES)}}
    )
    pq.write_table(table, args.parquet_out, compression="zstd")
    print(f"parquet -> {args.parquet_out} "
          f"({os.path.getsize(args.parquet_out) / 1024**2:.0f} MB)", flush=True)

    # --- per-property statistics -------------------------------------------------------------
    print("computing sigma / quantiles ...", flush=True)
    stats: dict[str, dict] = {}
    usable: list[int] = []
    for j, name in enumerate(P.NAMES):
        col = values[:, j].astype(np.float64)
        finite = np.isfinite(col)
        n_finite = int(finite.sum())
        rec: dict = {"kind": P.KIND[name], "group": P.GROUP[name], "n_finite": n_finite,
                     "n_nonfinite": n - n_finite}
        if n_finite == 0:
            rec["status"] = "dropped:nonfinite"
            stats[name] = rec
            continue
        good = col[finite]
        mean = float(good.mean())
        sigma = float(good.std(ddof=0))
        p1, p5, p95, p99 = (float(x) for x in np.percentile(good, [1, 5, 95, 99]))
        rec.update({"sigma": sigma, "mean": mean, "min": float(good.min()),
                    "max": float(good.max()), "p1": p1, "p5": p5, "p95": p95, "p99": p99})
        if rec["n_nonfinite"] > 0:
            rec["status"] = "dropped:nonfinite"
        elif sigma < DEGENERATE_ABS or (mean != 0 and sigma / abs(mean) < DEGENERATE_REL):
            rec["status"] = "dropped:degenerate"
        else:
            rec["status"] = "ok"
            usable.append(j)
        stats[name] = rec

    # num_tautomers is censored at the enumerator cap; a high rate would distort its sigma.
    tj = P.NAMES.index("num_tautomers")
    cap_hits = int(np.sum(values[:, tj] >= TAUTOMER_CAP))
    stats["num_tautomers"]["cap"] = TAUTOMER_CAP
    stats["num_tautomers"]["n_at_cap"] = cap_hits

    # --- the gate the decision is waiting on -------------------------------------------------
    gates = {}
    for g in (1.8, 2.5, 3.2):
        survivors = sorted(
            name for name, r in stats.items()
            if r.get("status") == "ok" and r["kind"] == "integer" and r.get("sigma", 0) >= g
        )
        gates[f"{g}"] = {"n": len(survivors), "survivors": survivors}

    # --- Spearman --------------------------------------------------------------------------
    print(f"computing {len(usable)}x{len(usable)} Spearman matrix ...", flush=True)
    t0 = time.perf_counter()
    rho = spearman(values, usable)
    print(f"  {time.perf_counter() - t0:.0f}s", flush=True)
    usable_names = [P.NAMES[j] for j in usable]
    iu = np.triu_indices(len(usable), k=1)
    collinear = [
        {"a": usable_names[a], "b": usable_names[b], "rho": round(float(rho[a, b]), 4)}
        for a, b in zip(*iu) if abs(rho[a, b]) > 0.95
    ]
    collinear.sort(key=lambda d: -abs(d["rho"]))

    timing, n_timed = _timing_sample(smiles, args.timing_sample)

    provenance = {
        "schema_version": 1,
        "pool": {**prov, "source": "files.docking.org/2D (ZINC20 2D, purchasability A+B)"},
        "rdkit_version": rdkit.__version__,
        "ddof": 0,
        "property_table": "docs/reference/table-a4-properties.md",
        "n_numeric_properties": len(P.NAMES),
        "string_property": P.STRING_PROPERTY,
        "descriptor_pass_seconds": round(elapsed, 1),
        "descriptor_pass_workers": args.workers,
        "unparseable_in_pass": unparsed,
    }

    with open(os.path.join(args.cache_dir, "sigma_cache.json"), "w", encoding="utf-8") as fh:
        json.dump({**provenance, "properties": stats}, fh, indent=1)
    with open(os.path.join(args.cache_dir, "quantile_cache.json"), "w", encoding="utf-8") as fh:
        json.dump({**provenance,
                   "quantiles": {k: {q: v[q] for q in ("p1", "p5", "p95", "p99")
                                     if q in v} for k, v in stats.items()}}, fh, indent=1)
    np.savez_compressed(os.path.join(args.cache_dir, "spearman_cache.npz"),
                        names=np.array(usable_names), rho=rho.astype(np.float32))
    with open(os.path.join(args.cache_dir, "spearman_cache.json"), "w", encoding="utf-8") as fh:
        json.dump({**provenance, "names": usable_names,
                   "collinear_pairs_abs_rho_gt_0.95": collinear}, fh, indent=1)
    with open(os.path.join(args.cache_dir, "objective_pool_gates.json"), "w",
              encoding="utf-8") as fh:
        json.dump({**provenance, "rule": "integer properties with sigma_y >= gate",
                   "gates": gates}, fh, indent=1)
    with gzip.open(os.path.join(args.cache_dir, "pool_zinc_ids.txt.gz"), "wt",
                   encoding="utf-8") as fh:
        fh.write("\n".join(ids))
    with open(os.path.join(args.cache_dir, "property_timing_ms.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"n_molecules_timed": n_timed,
                   "ms_per_molecule_single_core": {k: round(v, 5) for k, v in
                                                   sorted(timing.items(), key=lambda kv: -kv[1])}},
                  fh, indent=1)

    # --- report ----------------------------------------------------------------------------
    dropped = {k: v["status"] for k, v in stats.items() if v["status"] != "ok"}
    print("\n=== REPORT ===")
    print(f"n_pool {n:,}   usable properties {len(usable)}/{len(P.NAMES)}")
    print(f"dropped {len(dropped)}: {json.dumps(dropped, indent=1)}")
    for g, d in gates.items():
        print(f"integer sigma >= {g}: {d['n']} survivors")
    print(f"gate 2.5 survivors: {gates['2.5']['survivors']}")
    for name in ("molecular_weight", "logp", "heavy_atom_count", "num_bonds", "tpsa",
                 "num_tautomers", "fr_benzene", "fr_halogen", "fr_nitro", "fr_furan",
                 "fr_morpholine", "num_valence_electrons", "atom_count_C", "kappa3",
                 "max_partial_charge", "num_leadopt_disallowed_atoms"):
        r = stats[name]
        print(f"  {name:34s} {r['kind'][:4]} sigma={r.get('sigma', float('nan')):10.4f} "
              f"mean={r.get('mean', float('nan')):10.4f} status={r['status']}")
    print(f"num_tautomers at cap {TAUTOMER_CAP}: {cap_hits:,}")
    print(f"collinear pairs |rho|>0.95: {len(collinear)}")
    print("slowest properties (ms/molecule, single core):")
    for k, v in sorted(timing.items(), key=lambda kv: -kv[1])[:8]:
        print(f"  {v:8.4f}  {k}")
    print(f"caches -> {args.cache_dir}")


if __name__ == "__main__":
    main()

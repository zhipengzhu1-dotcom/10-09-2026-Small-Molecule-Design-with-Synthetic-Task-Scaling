"""Filter ZINC20 in-stock to MW 300-450 and sample exactly 1,000,000 molecules.

Two stages, each resumable:

  filter   stream every downloaded <TT><R><P>.txt, keep rows whose ZINC `mwt` column is in
           [300, 450], and consolidate them into one survivors TSV. ZINC's own column is used
           here and only here: it is the cheap pre-filter that avoids running RDKit over all
           ~11.2 M in-stock molecules. Every property that reaches the reward comes from RDKit.

  sample   draw a seeded permutation of the survivors, walk it in order, RDKit-canonicalise,
           and keep the first 1,000,000 that parse. Walking a permutation rather than drawing
           a fixed 1 M means parse failures are topped up deterministically instead of
           silently shrinking the pool.

The MW window is not cosmetic. ZINC20 in-stock unfiltered has sigma_MW = 88.4 Da against an
inferred 30-45 Da for the ZINC-22 pool the paper calibrated its reward against; the window
brings it to ~38 Da. See docs/research/zinc-seed-source.md section 5.5.

Usage:
  python build_pool.py filter <manifest.json> <txt-dir> <survivors.tsv>
  python build_pool.py sample <survivors.tsv> <pool.tsv> [--n 1000000] [--seed 20261011]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

MW_LO, MW_HI = 300.0, 450.0
DEFAULT_SEED = 20261011
DEFAULT_N = 1_000_000


# --- stage 1: filter -------------------------------------------------------------------------

def filter_stage(manifest_path: str, txt_dir: str, out_path: str) -> None:
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    names = sorted(f["name"] for f in manifest["files"] if f["ext"] == "txt")

    t0 = time.perf_counter()
    seen = kept = bad = 0
    tmp = out_path + ".part"
    with open(tmp, "w", encoding="utf-8", newline="\n") as out:
        out.write("zinc_id\tsmiles\tzinc_mwt\tzinc_logp\ttranche_file\n")
        for i, name in enumerate(names, 1):
            path = os.path.join(txt_dir, name)
            with open(path, encoding="utf-8", errors="replace") as fh:
                header = fh.readline()
                if not header.startswith("smiles"):
                    raise RuntimeError(f"{name}: unexpected header {header!r}")
                for line in fh:
                    cols = line.rstrip("\r\n").split("\t")
                    if len(cols) < 5:
                        bad += 1
                        continue
                    seen += 1
                    try:
                        mwt = float(cols[3])
                    except ValueError:
                        bad += 1
                        continue
                    if MW_LO <= mwt <= MW_HI:
                        out.write(f"{cols[1]}\t{cols[0]}\t{cols[3]}\t{cols[4]}\t{name}\n")
                        kept += 1
            if i % 200 == 0 or i == len(names):
                print(f"  {i}/{len(names)} files  seen {seen:,}  kept {kept:,}  "
                      f"{time.perf_counter() - t0:.0f}s", flush=True)
    os.replace(tmp, out_path)
    print(f"\nin-stock molecules scanned : {seen:,}")
    print(f"survivors MW {MW_LO:.0f}-{MW_HI:.0f}  : {kept:,}  ({kept / seen:.1%})")
    print(f"unparseable lines          : {bad:,}")
    print(f"-> {out_path}  ({os.path.getsize(out_path) / 1024**2:.0f} MB, "
          f"{time.perf_counter() - t0:.0f}s)")


# --- stage 2: sample -------------------------------------------------------------------------

def _canonicalise(chunk):
    """Worker: (index, zinc_id, smiles) -> (index, zinc_id, canonical) for what parses."""
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    out = []
    for idx, zid, smi in chunk:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        out.append((idx, zid, Chem.MolToSmiles(mol)))
    return out


def sample_stage(survivors: str, out_path: str, n: int, seed: int, workers: int) -> None:
    # Binary mode throughout: text-mode tell()/seek() traffic in opaque cookies, not byte
    # offsets, so indexing a text handle and seeking back into it is not safe.
    t0 = time.perf_counter()
    offsets = []
    with open(survivors, "rb") as fh:
        pos = len(fh.readline())
        for line in fh:
            offsets.append(pos)
            pos += len(line)
    total = len(offsets)
    print(f"survivors: {total:,}  ({time.perf_counter() - t0:.0f}s to index)", flush=True)
    if total < n:
        raise SystemExit(f"only {total:,} survivors, need {n:,}")

    rng = np.random.default_rng(seed)
    perm = rng.permutation(total)

    # Walk the permutation in blocks, reading the chosen lines in file order within each block,
    # until exactly n molecules have canonicalised. A parse failure consumes a draw and the
    # walk continues, so the pool is always exactly n.
    kept: list[tuple[int, str, str]] = []
    cursor = 0
    failures = 0
    block = max(n // 8, 50_000)
    with open(survivors, "rb") as fh, Pool(workers) as pool:
        while len(kept) < n and cursor < total:
            take = perm[cursor:cursor + block]
            cursor += len(take)
            rows = []
            for idx in sorted(take.tolist()):
                fh.seek(offsets[idx])
                cols = fh.readline().decode("utf-8").rstrip("\r\n").split("\t")
                rows.append((idx, cols[0], cols[1]))
            chunks = [rows[i:i + 2000] for i in range(0, len(rows), 2000)]
            got = 0
            for part in pool.imap(_canonicalise, chunks):
                kept.extend(part)
                got += len(part)
            failures += len(rows) - got
            print(f"  drawn {cursor:,}  kept {len(kept):,}  parse failures {failures:,}  "
                  f"{time.perf_counter() - t0:.0f}s", flush=True)
    kept = kept[:n]
    if len(kept) < n:
        raise SystemExit(f"exhausted survivors with only {len(kept):,} parseable")

    # Keep the draw order (permutation order) so a prefix of the pool is itself a uniform sample.
    with open(out_path + ".part", "w", encoding="utf-8", newline="\n") as out:
        out.write("zinc_id\tcanonical_smiles\n")
        for _, zid, smi in kept:
            out.write(f"{zid}\t{smi}\n")
    os.replace(out_path + ".part", out_path)

    ids = np.array([int(z.replace("ZINC", "") or 0) if z.startswith("ZINC") else int(z)
                    for _, z, _ in kept], dtype=np.int64)
    smiles_sorted = sorted(s for _, _, s in kept)
    digest = hashlib.sha256("\n".join(smiles_sorted).encode("utf-8")).hexdigest()

    provenance = {
        "n_pool": len(kept),
        "sample_seed": seed,
        "survivors_total": total,
        "draws_consumed": cursor,
        "parse_failures": failures,
        "duplicate_zinc_ids": int(len(ids) - len(np.unique(ids))),
        "duplicate_canonical_smiles": int(len(smiles_sorted) - len(set(smiles_sorted))),
        "smiles_sha256": digest,
        "mw_window": [MW_LO, MW_HI],
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }
    with open(os.path.splitext(out_path)[0] + "_provenance.json", "w", encoding="utf-8") as fh:
        json.dump(provenance, fh, indent=1)
    for k, v in provenance.items():
        print(f"{k:28s} {v}")
    print(f"-> {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("filter")
    f.add_argument("manifest")
    f.add_argument("txt_dir")
    f.add_argument("out")
    s = sub.add_parser("sample")
    s.add_argument("survivors")
    s.add_argument("out")
    s.add_argument("--n", type=int, default=DEFAULT_N)
    s.add_argument("--seed", type=int, default=DEFAULT_SEED)
    s.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    args = ap.parse_args()

    if args.cmd == "filter":
        filter_stage(args.manifest, args.txt_dir, args.out)
    else:
        sample_stage(args.survivors, args.out, args.n, args.seed, args.workers)


if __name__ == "__main__":
    sys.exit(main())

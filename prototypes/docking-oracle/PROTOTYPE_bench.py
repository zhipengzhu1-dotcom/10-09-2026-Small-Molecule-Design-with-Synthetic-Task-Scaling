"""PROTOTYPE -- throwaway. Entry point for ticket #4's measurements.

  python PROTOTYPE_bench.py prep  <struct_dir>
  python PROTOTYPE_bench.py bench <struct_dir> <bin_dir> [n_per_target] [mode] [scoring]

Surfaces the full state of every call: per-stage timing, score, and failure reason.
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from statistics import median, mean

sys.path.insert(0, str(Path(__file__).resolve().parent))
from PROTOTYPE_dock_oracle import (  # noqa: E402
    prep, gen_analogs, embed_to_template, smina_score,
)
from rdkit import Chem  # noqa: E402


def pct(xs, q):
    if not xs:
        return float("nan")
    s = sorted(xs)
    i = min(len(s) - 1, max(0, int(round(q / 100 * (len(s) - 1)))))
    return s[i]


def bench(struct_dir, bin_dir, n_per=25, mode="minimize", scoring="vinardo"):
    struct_dir, bin_dir = Path(struct_dir), Path(bin_dir)
    manifest = json.loads((struct_dir / "manifest.json").read_text())
    smina = str(bin_dir / "smina")
    rows, failures = [], {}

    for pid, info in manifest.items():
        core = next(Chem.SDMolSupplier(info["ligand"], removeHs=False))
        analogs = gen_analogs(core, n_per)
        print(f"\n### {pid} ({info['ccd']}, {info['lig_heavy']} heavy atoms, "
              f"{info['lig_rotb']} rotb) -- {len(analogs)} analogs", flush=True)

        for smi, sub, site in analogs:
            t0 = time.perf_counter()
            m, err = embed_to_template(smi, core)
            t_embed = time.perf_counter() - t0
            if err:
                failures[err] = failures.get(err, 0) + 1
                rows.append(dict(target=pid, smiles=smi, sub=sub, t_embed=t_embed,
                                 t_dock=0.0, score=None, fail=err))
                continue

            with tempfile.NamedTemporaryFile("w", suffix=".sdf", delete=False) as fh:
                tmp = fh.name
            w = Chem.SDWriter(tmp)
            w.write(m)
            w.close()
            score, t_dock, err = smina_score(
                smina, info["receptor"], info["ligand"], tmp, mode, scoring)
            os.unlink(tmp)
            if err:
                failures[err] = failures.get(err, 0) + 1
            rows.append(dict(target=pid, smiles=smi, sub=sub, t_embed=t_embed,
                             t_dock=t_dock, score=score, fail=err,
                             heavy=m.GetNumHeavyAtoms()))
            print(f"  {sub:<12} site{site:<4} embed {t_embed:6.3f}s  dock {t_dock:6.3f}s  "
                  f"score {score if score is not None else 'FAIL(' + str(err) + ')'}",
                  flush=True)

    ok = [r for r in rows if r["score"] is not None]
    emb = [r["t_embed"] for r in rows]
    dock = [r["t_dock"] for r in ok]
    tot = [r["t_embed"] + r["t_dock"] for r in ok]

    print("\n" + "=" * 78)
    print(f"mode={mode} scoring={scoring}  n={len(rows)}  ok={len(ok)}  "
          f"failed={len(rows) - len(ok)}")
    for stage, xs in (("embed", emb), ("dock", dock), ("TOTAL", tot)):
        if xs:
            print(f"  {stage:<6} median {median(xs):6.3f}s  mean {mean(xs):6.3f}s  "
                  f"p90 {pct(xs, 90):6.3f}s  p99 {pct(xs, 99):6.3f}s  max {max(xs):6.3f}s")
    if ok:
        sc = [r["score"] for r in ok]
        print(f"  scores: median {median(sc):.2f}  min {min(sc):.2f}  max {max(sc):.2f} "
              f"(more negative = tighter)")
    if failures:
        print("  failures:", failures)

    out = Path(__file__).parent / f"PROTOTYPE_results_{mode}_{scoring}.json"
    out.write_text(json.dumps(rows, indent=1))
    print(f"  rows -> {out}")
    return rows


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prep":
        prep(sys.argv[2])
    elif cmd == "bench":
        bench(sys.argv[2], sys.argv[3],
              int(sys.argv[4]) if len(sys.argv) > 4 else 25,
              sys.argv[5] if len(sys.argv) > 5 else "minimize",
              sys.argv[6] if len(sys.argv) > 6 else "vinardo")

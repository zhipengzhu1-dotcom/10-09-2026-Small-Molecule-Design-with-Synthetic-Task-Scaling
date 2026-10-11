"""Download the ZINC20 2D in-stock tranche files listed in a manifest.

Modest concurrency on purpose: the research record measured that 10-12 parallel connections to
files.docking.org produce intermittent truncated responses, while 6 with retries is reliable.
Already-complete files are skipped by size, so the run resumes.

Usage:  python download_zinc20.py <manifest.json> <dest-dir> [--ext txt] [--workers 6]
"""

from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests

UA = "Mozilla/5.0 (academic reproduction; pool build)"


def fetch(entry: dict, dest: str, tries: int = 4) -> tuple[str, int, str]:
    path = os.path.join(dest, entry["name"])
    # Apache reports sizes rounded to K/M, so accept anything within 2 KiB of the estimate.
    if os.path.exists(path) and abs(os.path.getsize(path) - entry["size_bytes"]) <= 2048:
        return entry["name"], os.path.getsize(path), "cached"
    session = requests.Session()
    session.headers["User-Agent"] = UA
    for attempt in range(tries):
        try:
            r = session.get(entry["url"], timeout=300)
            if r.status_code == 200 and r.content:
                tmp = path + ".part"
                with open(tmp, "wb") as fh:
                    fh.write(r.content)
                os.replace(tmp, path)
                return entry["name"], len(r.content), "ok"
        except requests.RequestException:
            pass
        time.sleep(3 * (attempt + 1))
    return entry["name"], 0, "FAILED"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("dest")
    ap.add_argument("--ext", default="txt", choices=("txt", "smi"))
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as fh:
        manifest = json.load(fh)
    entries = [f for f in manifest["files"] if f["ext"] == args.ext]
    os.makedirs(args.dest, exist_ok=True)
    print(f"{len(entries)} {args.ext} files, "
          f"{sum(e['size_bytes'] for e in entries) / 1024**2:.0f} MB nominal", flush=True)

    t0 = time.perf_counter()
    done = total = 0
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for name, nbytes, status in pool.map(lambda e: fetch(e, args.dest), entries):
            done += 1
            total += nbytes
            if status == "FAILED":
                failures.append(name)
            if done % 100 == 0 or done == len(entries):
                el = time.perf_counter() - t0
                print(f"  {done}/{len(entries)}  {total / 1024**2:7.0f} MB  "
                      f"{el:5.0f}s  {total / 1024**2 / max(el, 1e-9):5.1f} MB/s", flush=True)

    print(f"downloaded {total / 1024**2:.1f} MB in {time.perf_counter() - t0:.0f}s")
    if failures:
        print(f"FAILED ({len(failures)}): {failures[:20]}")
        raise SystemExit(1)
    print("all files present")


if __name__ == "__main__":
    main()

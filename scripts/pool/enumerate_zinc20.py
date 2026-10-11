"""Enumerate the ZINC20 2D in-stock tranche files and write a manifest.

ZINC20's 2D export at files.docking.org/2D/ is a plain Apache directory tree: 121 first-level
tranches named <TT>, each holding files <TT><R><P>.{smi,txt} where R is a reactivity class and
P a purchasability class (A = premier, B = in-stock). This script lists all 121 directories and
records every A/B file with its server-reported size and timestamp.

The manifest is the provenance record: sigma is a function of the snapshot, and the site
refreshes every 60 days, so the timestamps must be captured at download time.

Usage:  python enumerate_zinc20.py <out-manifest.json>
"""

from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

BASE = "https://files.docking.org/2D/"
PURCHASABILITY = ("A", "B")  # premier + in-stock
ROW = re.compile(
    r'href="(?P<name>[A-K]{2}[A-K][A-K]\.(?:smi|txt))">[^<]*</a>\s*</td>'
    r'\s*<td[^>]*>\s*(?P<stamp>[\d-]{10} [\d:]{5})\s*</td>'
    r'\s*<td[^>]*>\s*(?P<size>[\d.]+[KMG]?)\s*</td>'
)
UNITS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}


def _session():
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (academic reproduction; pool build)"
    return s


def _to_bytes(size: str) -> int:
    unit = size[-1] if size[-1] in UNITS else ""
    return int(float(size[: len(size) - len(unit) or None]) * UNITS[unit])


def _get(session, url, tries=4):
    for attempt in range(tries):
        try:
            r = session.get(url, timeout=180)
            if r.status_code == 200:
                return r.text
        except requests.RequestException:
            pass
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"could not list {url}")


def list_tranches(session) -> list[str]:
    text = _get(session, BASE)
    return sorted(set(re.findall(r'href="([A-K][A-K])/"', text)))


def list_tranche(session, tranche: str) -> list[dict]:
    text = _get(session, f"{BASE}{tranche}/")
    out = []
    for m in ROW.finditer(text):
        name = m.group("name")
        if name[3] not in PURCHASABILITY:  # 4th char is purchasability
            continue
        out.append(
            {
                "tranche": tranche,
                "name": name,
                "ext": name.rsplit(".", 1)[1],
                "reactivity": name[2],
                "purchasability": name[3],
                "modified": m.group("stamp"),
                "size_bytes": _to_bytes(m.group("size")),
                "url": f"{BASE}{tranche}/{name}",
            }
        )
    if not out:
        raise RuntimeError(f"no A/B files parsed for tranche {tranche}")
    return out


def main(out_path: str) -> None:
    session = _session()
    tranches = list_tranches(session)
    print(f"{len(tranches)} tranches", flush=True)

    files: list[dict] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for i, rows in enumerate(pool.map(lambda t: list_tranche(session, t), tranches), 1):
            files.extend(rows)
            if i % 20 == 0:
                print(f"  listed {i}/{len(tranches)}", flush=True)

    by_ext: dict[str, dict] = {}
    for f in files:
        d = by_ext.setdefault(f["ext"], {"files": 0, "bytes": 0})
        d["files"] += 1
        d["bytes"] += f["size_bytes"]

    stamps = sorted({f["modified"] for f in files})
    manifest = {
        "source": BASE,
        "purchasability": list(PURCHASABILITY),
        "tranches": tranches,
        "listed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "snapshot_modified_min": stamps[0],
        "snapshot_modified_max": stamps[-1],
        "totals_by_ext": by_ext,
        "files": files,
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)

    for ext, d in sorted(by_ext.items()):
        print(f"{ext}: {d['files']} files, {d['bytes'] / 1024**2:.1f} MB")
    print(f"snapshot timestamps {stamps[0]} .. {stamps[-1]}")
    print(f"manifest -> {out_path}")


if __name__ == "__main__":
    main(sys.argv[1])

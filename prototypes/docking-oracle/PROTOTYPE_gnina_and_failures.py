"""PROTOTYPE -- throwaway. Two leftovers from ticket #4:
(a) time gnina --cnn fast on GPU, as the #9 candidate for an expensive held-out oracle;
(b) prove the failure contract returns a clean reason, never a garbage score.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from PROTOTYPE_dock_oracle import embed_to_template, smina_score  # noqa: E402
from rdkit import Chem  # noqa: E402

STRUCT = Path(os.environ["STRUCT_DIR"])
BINS = Path(os.environ["BIN_DIR"])
WORK = Path(os.environ["WORK_DIR"])


def vram_mib():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=30).stdout.strip().splitlines()
        return int(out[0])
    except Exception as e:
        return f"unavailable({e})"


def run_gnina(rec, lig, batch_sdf, cnn, scoring_mode, gpu=True):
    cmd = [str(BINS / "gnina"), "-r", rec, "-l", batch_sdf,
           "--autobox_ligand", lig, "--autobox_add", "4",
           "--minimize", "--cnn", cnn, "--cnn_scoring", scoring_mode]
    if not gpu:
        cmd.append("--no_gpu")
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    dt = time.perf_counter() - t0
    aff = [ln for ln in p.stdout.splitlines() if ln.strip().startswith("Affinity:")]
    cnnaff = [ln for ln in p.stdout.splitlines() if "CNNaffinity" in ln]
    return dt, len(aff), len(cnnaff), p.returncode, p.stdout, p.stderr


def main():
    manifest = json.loads((STRUCT / "manifest.json").read_text())
    pid = "1iep"
    info = manifest[pid]
    batch = str(WORK / f"{pid}_batch.sdf")
    n = sum(1 for _ in Chem.SDMolSupplier(batch, removeHs=False))

    print(f"=== gnina on {pid}, {n} poses (already embedded) ===")
    print(f"VRAM before: {vram_mib()} MiB")
    for cnn, mode, gpu in (("fast", "rescore", True),
                           ("default", "rescore", True),
                           ("fast", "rescore", False)):
        dt, naff, ncnn, rc, so, se = run_gnina(
            info["receptor"], info["ligand"], batch, cnn, mode, gpu)
        tag = f"--cnn {cnn} --cnn_scoring {mode} {'GPU' if gpu else 'CPU'}"
        if rc != 0:
            print(f"  {tag:<44} FAILED rc={rc}: {se.strip().splitlines()[-1:]}")
            continue
        print(f"  {tag:<44} {dt:7.2f}s  {dt / max(1, naff) * 1000:7.1f} ms/mol  "
              f"({naff} affinity, {ncnn} cnn lines)  VRAM now {vram_mib()} MiB")

    print("\n=== smina reference on the same batch, for the ratio ===")
    from PROTOTYPE_dock_oracle import smina_score_batch
    sc, dt, err = smina_score_batch(str(BINS / "smina"), info["receptor"],
                                    info["ligand"], batch, "minimize", "vinardo")
    print(f"  smina/vinardo batched: {dt:.2f}s, {dt / max(1, len(sc)) * 1000:.1f} ms/mol")

    print("\n=== failure contract: every bad input must yield a reason, not a score ===")
    core = next(Chem.SDMolSupplier(info["ligand"], removeHs=False))
    cases = [
        ("invalid SMILES",        "C1CC1C(((C"),
        ("empty string",          ""),
        ("valid but off-scaffold", "CCO"),
        ("valid, wrong scaffold", "c1ccccc1C(=O)NCCCN"),
        ("the lead itself",       info["smiles"]),
    ]
    for label, smi in cases:
        m, err = embed_to_template(smi, core)
        print(f"  {label:<24} -> {'ERR ' + err if err else 'embedded ok'}")

    print("\n  -- smina handed a garbage ligand file --")
    bad = WORK / "garbage.sdf"
    bad.write_text("this is not an sdf\n")
    s, dt, err = smina_score(str(BINS / "smina"), info["receptor"], info["ligand"],
                             str(bad), "minimize", "vinardo")
    print(f"  garbage SDF              -> score={s} err={err} ({dt:.2f}s)")

    print("\n  -- smina handed a missing file --")
    s, dt, err = smina_score(str(BINS / "smina"), info["receptor"], info["ligand"],
                             str(WORK / "nope.sdf"), "minimize", "vinardo")
    print(f"  missing SDF              -> score={s} err={err} ({dt:.2f}s)")


if __name__ == "__main__":
    main()

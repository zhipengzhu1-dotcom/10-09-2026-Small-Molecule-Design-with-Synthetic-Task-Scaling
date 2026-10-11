"""PROTOTYPE -- throwaway. Answers wayfinder ticket #4: which docking oracle
replaces POSIT + Chemgauss4, and what does one call cost on this machine?

Not production code. No tests, no error handling beyond what keeps it runnable.
The validated decision goes to the ticket; this file lives on a throwaway branch.

Mirrors the paper's Tier-2 logic: template-based placement from the lead's
crystallographic pose (POSIT) + an empirical score (Chemgauss4), substituted by
RDKit ConstrainedEmbed + smina local minimisation.

  prep   -- split PDBs into receptor + crystal ligand, fetch CCD bond orders
  bench  -- generate analogs, score them, time every stage
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from statistics import median

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem
from rdkit.Chem.AllChem import AssignBondOrdersFromTemplate

RDLogger.DisableLog("rdApp.*")

# solvents / buffers / ions that are never the ligand of interest
JUNK = {
    "HOH", "DOD", "SO4", "PO4", "GOL", "EDO", "PEG", "ACT", "DMS", "TRS", "MES",
    "EPE", "IMD", "CIT", "MLI", "FMT", "ACY", "BME", "NAG", "MAN", "BMA", "FUC",
    "NA", "CL", "MG", "ZN", "CA", "K", "MN", "FE", "CU", "NI", "CD", "HG", "BR",
    "IOD", "F", "CO", "CAC", "NH4", "AZI", "NO3", "SCN", "PG4", "P6G", "1PE",
}


def _atom_count_by_het(pdb_text):
    groups = {}
    for ln in pdb_text.splitlines():
        if not ln.startswith("HETATM"):
            continue
        res, chain, seq = ln[17:20].strip(), ln[21], ln[22:27].strip()
        if res in JUNK:
            continue
        if ln[76:78].strip() == "H":
            continue
        groups.setdefault((res, chain, seq), []).append(ln)
    return groups


def prep(struct_dir):
    struct_dir = Path(struct_dir)
    manifest = {}
    for pdb in sorted(struct_dir.glob("*.pdb")):
        pid = pdb.stem
        if pid.endswith(("_rec", "_lig")):
            continue
        text = pdb.read_text()

        groups = _atom_count_by_het(text)
        if not groups:
            print(f"{pid}: NO LIGAND FOUND", file=sys.stderr)
            continue
        (res, chain, seq), lines = max(groups.items(), key=lambda kv: len(kv[1]))

        # receptor: protein atoms only, first model, blank/A altloc
        rec_lines = []
        for ln in text.splitlines():
            if ln.startswith("ENDMDL"):
                break
            if ln.startswith("ATOM") and ln[17:20].strip() not in ("HOH", "DOD"):
                if ln[16] in (" ", "A"):
                    rec_lines.append(ln)
        rec_path = struct_dir / f"{pid}_rec.pdb"
        rec_path.write_text("\n".join(rec_lines) + "\nEND\n")

        # crystal ligand: bound coordinates, bond orders from the CCD ideal SDF
        lig_pdb = "\n".join(lines) + "\nEND\n"
        mol = Chem.MolFromPDBBlock(lig_pdb, sanitize=False, removeHs=True)
        tmpl_path = struct_dir / f"{res}_ideal.sdf"
        if not tmpl_path.exists():
            url = f"https://files.rcsb.org/ligands/download/{res}_ideal.sdf"
            urllib.request.urlretrieve(url, tmpl_path)  # noqa: S310
        tmpl = next(Chem.SDMolSupplier(str(tmpl_path), sanitize=True))

        try:
            mol = AssignBondOrdersFromTemplate(tmpl, mol)
        except Exception as e:
            print(f"{pid}: bond-order assignment failed ({e})", file=sys.stderr)
            continue
        Chem.SanitizeMol(mol)

        lig_path = struct_dir / f"{pid}_lig.sdf"
        w = Chem.SDWriter(str(lig_path))
        w.write(mol)
        w.close()

        manifest[pid] = {
            "ccd": res, "chain": chain, "seq": seq,
            "receptor": str(rec_path), "ligand": str(lig_path),
            "rec_atoms": len(rec_lines),
            "lig_heavy": mol.GetNumHeavyAtoms(),
            "lig_rotb": Chem.rdMolDescriptors.CalcNumRotatableBonds(mol),
            "smiles": Chem.MolToSmiles(mol),
        }
        print(f"{pid}: ligand {res} ({mol.GetNumHeavyAtoms()} heavy, "
              f"{manifest[pid]['lig_rotb']} rotb), receptor {len(rec_lines)} atoms")

    (struct_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


SUBS = ["C", "F", "Cl", "O", "N", "OC", "C#N", "CC", "C(F)(F)F", "S(C)(=O)=O"]


def gen_analogs(core, limit):
    """Decorate open aromatic CH positions -- a scaffold-preserving lead-op move,
    so the crystal ligand is always a clean template for the analog."""
    base = Chem.RemoveHs(core)
    out = []
    sites = [a.GetIdx() for a in base.GetAtoms()
             if a.GetIsAromatic() and a.GetSymbol() == "C" and a.GetTotalNumHs() >= 1]
    for sub_smi in SUBS:
        sub = Chem.MolFromSmiles(sub_smi)
        for idx in sites:
            rw = Chem.RWMol(Chem.CombineMols(base, sub))
            rw.AddBond(idx, base.GetNumAtoms(), Chem.BondType.SINGLE)
            m = rw.GetMol()
            try:
                Chem.SanitizeMol(m)
            except Exception:
                continue
            out.append((Chem.MolToSmiles(m), sub_smi, idx))
            if len(out) >= limit:
                return out
    return out


def embed_to_template(smiles, core, seed=0xF00D):
    """POSIT substitute: constrain the analog to the lead's crystallographic pose."""
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None, "parse_failed"
    m = Chem.AddHs(m)
    if not m.GetSubstructMatch(core):
        return None, "no_template_match"
    try:
        AllChem.ConstrainedEmbed(m, core, useTethers=True, randomseed=seed)
    except Exception as e:
        return None, f"embed_failed:{type(e).__name__}"
    if m.GetNumConformers() == 0:
        return None, "no_conformer"
    return m, None


def smina_score(binary, receptor, autobox_lig, lig_sdf, mode, scoring, cpu=1, extra=()):
    cmd = [binary, "-r", receptor, "-l", lig_sdf,
           "--autobox_ligand", autobox_lig, "--autobox_add", "4",
           "--scoring", scoring, "--cpu", str(cpu), f"--{mode}", *extra]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    dt = time.perf_counter() - t0
    if p.returncode != 0:
        return None, dt, f"smina_exit_{p.returncode}"
    score = None
    for ln in p.stdout.splitlines():
        s = ln.strip()
        if s.startswith("Affinity:"):
            score = float(s.split()[1])
            break
    if score is None:
        return None, dt, "no_score_parsed"
    return score, dt, None


def smina_score_batch(binary, receptor, autobox_lig, multi_sdf, mode, scoring,
                      cpu=1, extra=()):
    """One invocation, many ligands. smina reads a multi-model SDF and prints one
    Affinity line per ligand -- so receptor parsing and process startup amortise."""
    cmd = [binary, "-r", receptor, "-l", multi_sdf,
           "--autobox_ligand", autobox_lig, "--autobox_add", "4",
           "--scoring", scoring, "--cpu", str(cpu), f"--{mode}", *extra]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    dt = time.perf_counter() - t0
    if p.returncode != 0:
        return [], dt, f"smina_exit_{p.returncode}"
    scores = [float(ln.split()[1]) for ln in p.stdout.splitlines()
              if ln.strip().startswith("Affinity:")]
    return scores, dt, None

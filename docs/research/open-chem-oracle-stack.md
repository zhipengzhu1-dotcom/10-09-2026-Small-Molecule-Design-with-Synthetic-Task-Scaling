# Open / free substitute stack for the oracles in arXiv 2609.04735

**Question.** The paper *"Training Large Language Models for Small-Molecule Design with Synthetic Task Scaling"* (Hu et al., arXiv:2609.04735, submitted 4 Sep 2026) builds its RL reward oracles on commercial OpenEye software and on SQM2.20 semiempirical-QM rescoring. What is the fully free/open substitute for each oracle, and what does each cost in wall-clock time per molecule?

**Audience.** A beginner with no computational-chemistry background, no institutional software budget, one consumer GPU, on Windows 11.

**Conventions used below**
- **[FACT]** — stated in a primary source, with the URL given.
- **[INFER]** — my inference/estimate, not in any source.
- **"not documented"** — I looked and the primary source is silent.

Research date: 2026-10-09.

---

## 0. What the paper actually requires (baseline, from the paper itself)

Primary source: <https://arxiv.org/html/2609.04735v1> (full HTML, incl. Appendix A).

| Tier | What it is | Software in the paper | Stated wall-clock cost |
|---|---|---|---|
| Tier-1 (cheap) | 116 precomputed molecular properties; each task picks 1 target property + 2–4 constraints + a scaffold constraint | **101 properties from RDKit, 15 from OpenEye** (Table A4) | No per-call number given; "significantly" cheaper than Tier-2, tasks "can be rapidly generated" |
| Tier-2 (medium) | Structure-based binding score | **POSIT** template docking (template = the lead's crystallographic pose) → **Chemgauss4** scoring, wrapped in one tool `score_chemgauss4` | "This consolidated scoring tool takes on the order of **seconds**"; a single POSIT run's runtime is "negligible" |
| Held-out eval (expensive) | Generalization target, **never trained on** | **SQM2.20** (Pecina et al. 2024), tool `score_sqm` | "a single SQM evaluation takes on the order of **tens of minutes**"; models get "at most **five SQM calls** in their budget" |

Other load-bearing facts from the paper **[FACT]**:
- Tools exposed to the LLM: `calculate_multiple_properties`, `score_chemgauss4`, `score_sqm`, `contains_scaffold`.
- Tier-1 task pool: **200,000** synthetic open-ended design tasks, seeded from molecules sampled from **ZINC**.
- Tier-2 + eval systems come from **PLINDER**: 999 ligand–receptor training pairs, 40 held-out SQM-evaluable systems. Filters: MW 200–600 Da; no ions/cofactors/covalent binders/oligomers/crystallization artifacts; crystal resolution ≤ 3 Å; must pass all **PoseBusters** checks; must produce a valid **OpenEye design unit** file.
- Base model **Qwen3.6-35B-A3B** (~35B total, ~3B active); 500 optimizer steps per recipe; eval n = 200 rollouts (5 × 40 systems), max 20 turns.
- "a full rollout for a single Tier-2 task can take up to twice as long as a full rollout for a Tier-1 task."
- FEP is named only as a comparison: "can require multiple GPU-hours per calculation."
- Hardware is described only as "internal hardware" — **GPU model and count are not documented.**

**Key consequence [INFER]:** 101 of the 116 Tier-1 properties are RDKit, i.e. **~87% of Tier-1 is already free**. The 15 OpenEye-only ones (examples given in Table A4: `oe_molecular_complexity`, `oe_ring_system_count`, `oe_net_charge_neutral_ph`) are the only genuinely commercial part of Tier-1, and all three examples have close free analogues (BertzCT / RDKit ring-system counting / a pKa-free formal-charge-at-pH-7 rule or an open pKa predictor).

---

## 1. OpenEye licensing — can an unaffiliated individual get it free?

Primary source: <https://www.eyesopen.com/academic-licensing>

**[FACT] Short answer: no.** Every academic option on that page requires institutional employment. Verbatim from the page:

- All options: *"you must be employed by and actively participating in research (or teaching)"* at an accredited degree-granting college or university, and the licences are *"not for use in a direct revenue generating capacity."*
- **Free Public Domain Research License** — *"intended for pure non-commercial research."* Eligibility *"may differ among distinct research groups within a single institution"*, and *"Eligibility is not permanent and will be reevaluated annually."* No support, no IP rights.
- **Free Teaching License** — *"intended for use by educators and their students solely in the context of a specific time-limited course."*
- **Academic Package (paid)** — *"intended for small academic research groups (fewer than 10 members)"*; *"Larger academic groups or groups with an obvious commercial focus are not eligible for this licensing option."* Described only as a "paid annual subscription".

**Application process [FACT/partial]:** the page points to an Academic License Application form at <https://www.eyesopen.com/academic-license-application>, and to a commercial inquiry form at <https://www.eyesopen.com/contact> for paid/commercial. **Not documented:** the form's required fields, whether a supervisor or institutional email is needed, and the approval turnaround. (I fetched the application page; it returned only site navigation, no form content and no eligibility text.)

**Which products are covered [FACT, vague]:** the academic page says each option includes *"access to OpenEye's core applications and toolkits"* but **does not enumerate products** — OMEGA, FRED, POSIT, OEChem and Spruce are not named there. Their existence as products is documented separately, e.g. the OEDocking TK page <https://www.eyesopen.com/oedocking-tk> and the docking-toolkit theory docs <https://docs.eyesopen.com/toolkits/java/dockingtk/theory/theory.html>.

**Price [FACT]: not published.** No price appears for the Academic Package or for any commercial licence on eyesopen.com; third-party software directories list OpenEye pricing as quote-only with no free trial (e.g. <https://us.fitgap.com/products/023929/openeye>). OpenEye is now a Cadence business unit (rebranded "OpenEye, Cadence Molecular Sciences"), and the paper itself cites it as "OpenEye, Cadence Molecular Sciences, 2025".

**Verdict for this project [INFER]:** an independent learner with no university employment **cannot** obtain POSIT / FRED / Chemgauss4 / OMEGA at any price they would want to pay, free or academic. Treat the OpenEye tier as unavailable and substitute it entirely. This affects Tier-2 wholesale and ~13% of Tier-1.

---

## 2. Open docking substitutes for POSIT + Chemgauss4

All licence/platform/packaging claims below are from the repos' own LICENSE files, GitHub licence metadata, READMEs, release asset lists, the anaconda.org/PyPI APIs and the conda-forge feedstock recipes; all timing claims are from the named paper or README. **No tool in this set carries a non-commercial-only restriction** — a clear win over OpenEye.

| Tool | Licence | Native Windows | conda / pip | GPU | Documented s/ligand + hardware |
|---|---|---|---|---|---|
| **AutoDock Vina 1.2.7** <https://github.com/ccsb-scripps/AutoDock-Vina> | **Apache-2.0** (LICENSE; README: *"distributed under the Apache License, Version 2.0"*) | **Yes but undocumented** — release ships `vina_1.2.7_win.exe` + `vina_split_1.2.7_win.exe`; docs say *"Python bindings (Linux and Mac only)"* | conda-forge **`vina`** — **no win-64** (feedstock: `build: skip: true  # [win]`); PyPI **`vina`** manylinux/musllinux x86_64 wheels only; bioconda `autodock-vina` stale at 1.1.2 | **None.** CPU-only, multithreaded | **Not documented.** 2010 paper (DOI 10.1002/jcc.21334): *"approximately two orders of magnitude speed-up compared with… AutoDock 4"*, no absolute number. Third-party: **126 s/complex on 16 CPUs** (DiffDock Table 1); ≈53 s/lig on an i9-10900K (*arithmetic from the Vina-GPU paper's 133.90 h / 9,125 compounds*) |
| **smina** <https://sourceforge.net/projects/smina/> (GitHub mirrors only) | **Conflicting primary sources.** SourceForge + bioconda say **GPLv2**; conda-forge recipe + the GitHub fork say **Apache-2.0**; the tree ships *both* `LICENSE.APACHE` and `LICENSE.GNU`. Neither is non-commercial-only | **Yes** — conda-forge publishes real `win-64` artefacts (`win-64/smina-2020.12.10-he0c23c2_2.conda`), with a dedicated `build_smina.bat` | conda-forge **`smina`** 2020.12.10 (incl. **win-64**); bioconda `smina` 2017.11.9; **no PyPI** → drive as a subprocess | **None** | **Not documented for docking.** README: *"10-20x faster"* for `--minimize`/`local_only` only, no hardware. Paper (DOI 10.1021/ci300604z) gives no timings; it claims smina is *"specially optimized to support high-throughput scoring and user-specified custom scoring functions"*. Third-party: **126 s/complex on 16 CPUs** |
| **Vina-GPU / 2.0 / 2.1 / QuickVina2-GPU** (DeltaGroupNJUPT) | **Apache-2.0** (all three repos) | **Yes, first-class** — `.exe` + a Windows GUI; *"Visual Studio 2019 is recommended for build"*; 2.1 uses CUDA Toolkit v12.2 | **None anywhere** — source build only. This is the family's biggest practical cost | **OpenCL** (NVIDIA + AMD); CUDA Toolkit only supplies the OpenCL lib | **Not documented per ligand.** Only absolute: **9,125 DrugBank compounds in ~9.44 h** on **RTX 3090 + i9-10900K / Win 10 / 64 GB** (≈**3.7 s/lig**, *my arithmetic*) vs ~133.90 h for Vina. Speedups: 21× avg / 50× max (v1, DOI 10.3390/molecules27093041); **65.6× vs Vina on an RTX 3090** (2.0, DOI 10.1021/acs.jcim.2c01504); **+4.97× over 2.0** (2.1, DOI 10.1109/TCBB.2024.3467127). Dormant since Oct 2024 |
| **gnina 1.3.x** <https://github.com/gnina/gnina> | **Apache-2.0** | **No** — Linux static binaries only; README: *"The pre-built binary can be used in WSL"*, plus explicit WSL2 Ubuntu 22.04 build instructions | **None** (`pygnina` is an "initial implementation", unpackaged). Docker images at hub.docker.com/u/gnina | **CUDA ≥ 12.0** required to build; runs CPU-only much slower | **Best documented of the set.** GNINA 1.3 (DOI 10.1186/s13321-025-00973-x), 4 CPU cores, 100 PDBbind-core complexes: Caffe models ~129 s, PyTorch ~30 s, **1.3 Default Ensemble ~23 s**, **`--cnn=fast` ~16 s** (*"about 1.3 s slower than Vina scoring"*). GNINA 1.0 with no GPU: 458 s (best ensemble) / 72 s (single model). GNINA 1.0 on an **11 GB RTX 2080 Ti**: the CNN ensemble adds *"only two seconds"*. README: `--cnn_scoring refinement` is *"10 times slower"*, `all` *"1000 times slower"* than default `rescore` |
| **DiffDock / DiffDock-L** <https://github.com/gcorso/DiffDock> | **MIT — code *and* model weights** | **No** — conda env with `+cu117` wheels + `openfold`, or `rbgcsail/diffdock` Docker; Windows/WSL never mentioned | **None** (git clone + conda, Docker, or the HF Space) | **CUDA 11.7** pinned; *"For inference, only a single GPU is required"*; CPU fallback documented but *"significantly slower"* | **DiffDock: yes.** **10 s for 10 samples on an RTX A100 40GB**, 40 s for 40 samples (×4 extrapolation), preprocessing (ESM2, RDKit conformers) **excluded**; DiffDock-small 7 s / 28 s; *"3 to 12 times faster"* than GNINA. **DiffDock-L per-complex time: not documented** |
| **Uni-Dock 1.2.0** <https://github.com/dptech-corp/Uni-Dock> | **Apache-2.0 since 2025-03-10** (README: previously `unidock/` was LGPL-3 — pin a current release) | **No** — README: *"officially supports NVIDIA GPUs with compute capability >= 7.0 on Linux platform"*. Docker available. WSL2 is viable but undocumented | conda-forge **`unidock`** 1.2.0, **linux-64 only** (*"A pre-built Uni-Dock binary with all requirements is available at conda-forge"*); PyPI **`unidock-tools`** = I/O wrapper only | **CUDA ≥ 11.8**, **CC ≥ 7.0** → RTX 3090 (8.6) and 4090 (8.9) qualify. `--max_gpu_memory` explicitly controls batch size | **Not documented in text.** Paper (DOI 10.1021/acs.jctc.2c01145): *"more than 1000-fold speedup… compared with the AutoDock Vina running in single CPU core"*, and *"outperforming… AutoDock-GPU and Vina-GPU based on head-to-head experiments"*; README v1.1 claims *"more than 2000-fold speed-up on V100"*. Only absolute: **38.2 M molecules vs KRAS G12D in 12 h on 100 V100s** (≈**8.8 mol/s/V100 ≈ 0.11 s/lig**, *my arithmetic*, and it was a **hierarchical** screen so not a uniform rate). Per-GPU runtime charts exist **only as PNGs** |
| **AutoDock-GPU 1.6** <https://github.com/ccsb-scripps/AutoDock-GPU> | **GPL-2.0** — the only copyleft-by-default tool here | **Yes** — v1.6 release ships `AutoDock-GPU.exe`; notes: *"Attached are binaries for Linux, Windows, and macOS"* | **None** | **CUDA and OpenCL**; OpenCL path also targets CPU and FPGA; SYCL/Intel in development | **Not documented per ligand.** README: *"speedups of up to 4x (quad-core CPU) and 56x (GPU)"*; paper (DOI 10.1021/acs.jctc.0c01006): *"reduce docking runtime by up to 350-fold"* — no GPU model, no seconds |
| `andriusbern/vinaGPU` wrapper | **No licence declared** (GitHub `license: None`) → treat as all-rights-reserved | No (Docker / nvidia-docker) | `pip install -e .` from clone | via the Vina-GPU Docker image, CUDA 11.7 | **Not documented.** API shape is ideal though: `parallel_dock(target_pdb_path=…, smiles=[…], num_cpu_workers=8, gpu_ids=[0,1], workers_per_gpu=2, search_depth=5)` — takes **SMILES directly**, returns scores |

Also noted: **Vina-CUDA** (`HPCLab-933/Vina-CUDA`, Apache-2.0, a true CUDA rewrite of Vina-GPU 2.1, no quantified speedup published), `Glinttsd/Vina-GPU-CUDA` (**no licence**), `PKUGaoGroup/DSDP` (licence `NOASSERTION` — read before use), and **Ringtail** (`forlilab/Ringtail`, LGPL-2.1) for persisting thousands of screening results.

### Which are realistic inside an RL reward loop?

**[FACT] Primary-source precedent exists and it is Vina-shaped:** **DockStream** (Guo et al., *J. Cheminform.* **13**:89, 2021, DOI 10.1186/s13321-021-00563-7, code <https://github.com/MolecularAI/DockStream>, Apache-2.0) *"introduce[s] a structure-based scoring component for REINVENT"* and shows *"an informative docking configuration can inform the REINVENT agent to optimize towards improving docking scores using public data."* Its backends include AutoDock Vina and rDock. **This is the closest licence-clean template for exactly what the paper's Tier-2 does.** Its own caveat: *"Docking algorithms vary greatly in performance depending on the target."*

**[FACT] Reward-hacking warning from a primary source:** Sunseri & Koes, *Molecules* **26**(23):7369 (DOI 10.3390/molecules26237369) report gnina beating Vina on 89/117 DUD-E + LIT-PCBA targets with *"a median 1% early enrichment factor that is more than twice that of Vina"*, but warn that *"issues of bias linger in these sets… this bias obfuscates to what extent machine learning models are achieving their performance through a sophisticated interpretation of molecular interactions versus fitting to non-informative simplistic property distributions."* **[INFER]** A learned CNN reward is more gameable by an RL policy than a physics term. Prefer the Vina/Vinardo scalar as the primary reward.

**[FACT] DiffDock is not a scoring oracle.** Its own README FAQ: *"No, DiffDock does not predict the binding affinity of the ligand to the protein… it outputs a confidence score… **but it is not a direct measure of it**"*, with the recommendation to combine it with *"docking function (e.g. GNINA), MM/GBSA or absolute binding free energy calculations."* **[INFER]** DiffDock/DiffDock-L is a candidate *POSIT* replacement (pose generator), never a *Chemgauss4* replacement. Do not use its confidence as the RL reward.

**[INFER] Verdict, ranked for thousands of scores on one consumer GPU:**
1. **Uni-Dock in WSL2** (`conda install -c conda-forge unidock`, `--search_mode fast`, `--gpu_batch`) — batch-first CLI, Apache-2.0, your GPU qualifies, and it is the only tool with a documented ultralarge-screening campaign. But every absolute per-ligand number is in unreadable PNGs, so **measure it yourself** before budgeting.
2. **smina with `--minimize`/`--score_only` + an RDKit `ConstrainedEmbed` template pose** — the true POSIT+Chemgauss4 analogue, the only maintained **native-Windows** engine, and the README's own "10-20× faster for minimisation" claim puts it in the right cost class. Lowest setup risk by far.
3. **gnina `--cnn=fast`** at ~16 s/complex on 4 CPU cores (far less on GPU) if you want a learned score as a *secondary* or held-out oracle.
4. **Vina-GPU 2.1** only if you insist on native-Windows GPU and will budget a Visual Studio build of a dormant repo.
5. **Full-exhaustiveness CPU Vina/smina at ~126 s/complex is not viable** for thousands of RL rewards — that is ~35 h per 1,000 scores on 16 CPUs.

**[INFER] Unverified / measure-it-yourself:** DiffDock-L per-complex time; Uni-Dock per-GPU absolute runtimes; minimum VRAM for Vina-GPU, AutoDock-GPU, Uni-Dock and DiffDock (**none of the four documents a figure**); whether DiffDock runs at default settings on 24 GB (authors used 40–48 GB cards, and VRAM gates samples-in-parallel); smina's definitive licence.

## 2b. POSIT's open substitute: template-constrained pose generation

POSIT's distinguishing feature in the paper is **template docking from the lead's crystallographic pose**, not free docking. The free equivalent is a two-step recipe **[INFER, built from documented primitives]**:

1. **Generate a pose constrained to the template** — `rdkit.Chem.AllChem.ConstrainedEmbed(mol, core, useTethers=True, coreConfId=-1, randomseed=2342, ...)`, documented at <https://www.rdkit.org/docs/source/rdkit.Chem.AllChem.html>: *"generates an embedding of a molecule where part of the molecule is constrained to have particular coordinates"*; `core` is *"the molecule to use as a source of constraints"*, and with `useTethers=True` the final conformation is optimised with extra forces pulling matched atoms toward the core positions. Use the crystallographic ligand (or its MCS with the proposal) as `core`.
2. **Locally minimise + score in the pocket** — `smina --minimize` (or `--local_only --autobox_ligand <crystal_ligand>`), documented at <https://github.com/mwojcikowski/smina>: `--minimize` = "energy minimization … goes to convergence"; `--score_only` = "score provided ligand pose"; `--autobox_ligand` builds the box around a reference ligand with `--autobox_add` defaulting to 4 Å. **[FACT]** The repo states that for local-only minimisation workflows smina is **"10-20x faster"** than AutoDock Vina, with docking performance "roughly the same".

This is the closest free analogue of POSIT→Chemgauss4: template pose + local refinement + empirical score, in the "order of seconds" regime the paper describes for its own Tier-2 tool.

### What Chemgauss4 actually is (so you know what you are substituting)

Primary source: <https://docs.eyesopen.com/toolkits/java/dockingtk/scoring.html> **[FACT]**

Chemgauss4 is *"a modification of Chemgauss3 with improved hydrogen bonding and metal chelator terms"*; lower scores are better. Terms:
- **Shape** — united-atom (heavy atoms only) Gaussian overlap, precomputed on a smoothed grid; *"The shape and implicit solvent interaction terms are identical to those in Chemgauss3."*
- **Hydrogen bonding** — per donor–acceptor pair, `HBscore = strength * g(distance1) * g(distance2)` with `g` Gaussian; interactions exceeding a donor/acceptor's allowed count are dropped, *"with the lowest scoring interactions eliminated first."*
- **Metal chelator** — improved directionality perception; no formula published.
- **Implicit solvent / desolvation** — inherited from Chemgauss3: penalises broken protein–water and ligand–water H-bonds on smoothed grids.
- Sibling functions documented on the same page: Shapegauss, PLP, Chemscore, Chemgauss3. **No throughput statement appears on the page.**

**[INFER]** This is an *empirical, grid-based, Gaussian-smoothed* score with shape + H-bond + metal + desolvation terms and no explicit entropy. AutoDock Vina's function (steric Gaussians + repulsion + hydrophobic + H-bond + rotatable-bond penalty) and especially **Vinardo** are the same *family* of function. They will not reproduce Chemgauss4 numerically, but they occupy the same accuracy/cost niche, which is all the paper's Tier-2 needs: a noisy, seconds-scale, structure-aware reward that is harder than property counting.

### Protonation / charge-state substitute

`oe_net_charge_neutral_ph` has a free analogue in **Dimorphite-DL** (Ropp et al., *J. Cheminform.* **11**:14, 2019, <https://doi.org/10.1186/s13321-019-0336-9>), repo <https://github.com/durrantlab/dimorphite_dl>, **Apache-2.0**, PyPI `dimorphite-dl`. It *"adds or removes hydrogen atoms to achieve the appropriate molecular protonation state for a user-specified pH range."* **[FACT]** Caveat from its own README: it deprotonates indoles/pyrroles around pH 14.5 but does not protonate them around pH −3.5. Pure Python → **[INFER]** Windows-safe.

### Pose sanity filter used by the paper

**PoseBusters** <https://github.com/maabuu/posebusters> — **MIT**, `pip install posebusters`, *"Plausibility checks for generated molecule poses"*, paper DOI **10.1039/D3SC04185A** (*Chem. Sci.* 2024; preprint arXiv:2308.05777). Windows support and per-pose speed: **not documented**. The paper uses it as a hard filter on the PLINDER seeds, so you need it too; it is free, which removes one dependency worry.

**Supporting prep tools**

| Tool | Licence | Platform | conda-forge / PyPI | Role |
|---|---|---|---|---|
| **Meeko** <https://github.com/forlilab/Meeko> | **LGPL-2.1** | Windows support **not documented** on the repo page (pure Python → **[INFER]** should work) | `meeko` on both conda-forge and PyPI | *"prepares the input for AutoDock and processes its output"*; parameterises ligands **and receptors** (proteins, nucleic acids); SDF→PDBQT, results back to SDF/PDB |
| **Open Babel** <https://github.com/openbabel/openbabel> | **GPL-2.0** | <https://openbabel.org/docs/Installation/install.html>: *"available as a binary installer for Windows, both 64-bit (preferred) or 32-bit"* → **native Windows**, CLI + GUI. macOS = compile from source. conda **not mentioned** in the install docs. | not documented in install docs | Format conversion (90+ formats), *"Generate 2D and 3D coordinates for SMILES, InChI and other formats"*. PDBQT support **not confirmed on the pages read** |
| **rDock / RxDock** | GNU **LGPL** (SourceForge states LGPL 3.0 for that version); RxDock fork also LGPL-3.0: <https://github.com/rxdock/rxdock> | not documented | not documented | Alternative open docking engine; rDock paper = *PLoS Comput. Biol.* 2014, <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3983074/>; original project stalled 2014, RxDock maintained since 2019. **Per-ligand timing: not documented** in the sources read |

---

## 3. Tier-1 substitutes: cheap property oracles and ready-made MPO benchmarks

Timings marked **(measured here)** were benchmarked by a helper agent on this machine (Windows 11, native Python 3.14.5, single core) — they are empirical, **not** vendor claims, and are the only per-molecule numbers available because **no primary source documents RDKit descriptor throughput**.

### A) RDKit alone covers essentially all of Tier-1

**[FACT]** Licence **BSD 3-Clause** (<https://raw.githubusercontent.com/rdkit/rdkit/master/license.txt>). `pip install rdkit` — the docs state *"Linux, Windows, and macOS RDKit platform wheels are available"* (<https://www.rdkit.org/docs/Install.html>); `rdkit-pypi` is the **old** name. conda-forge `rdkit` lists `win-32, win-64` among its platforms and the 2026.09.1 feedstock recipe has **no `skip: # [win]`**. PyPI 2026.9.1 ships `win_amd64` wheels for CPython 3.10–3.15. → **native Windows, fully, no WSL.**

Every descriptor the paper's Tier-1 needs is confirmed in the official module docs:

| Property | RDKit module | Note from the docs |
|---|---|---|
| `MolWt`, `ExactMolWt`, `HeavyAtomMolWt` | `rdkit.Chem.Descriptors` | *"average molecular weight. Hydrogens are included"* / *"exact molecular weight, using isotope masses"* |
| `MolLogP`, `MolMR` | `rdkit.Chem.Crippen` | *"Wildman-Crippen LogP value"*; module = *"Atom-based calculation of LogP and MR using Crippen's approach"*, citing Wildman & Crippen, JCICS 39:868–873 (1999) |
| `TPSA` | `rdkit.Chem.MolSurf`, re-exported on `Descriptors` | cites *J. Med. Chem.* 43:3714–7 (2000); the RDKit Book documents deviations from the original paper |
| `qed` (+ `weights_max/mean/none`, `properties`, `ads`) | `rdkit.Chem.QED` | *"QED stands for quantitative estimation of drug-likeness"*, citing Bickerton et al., *Nat. Chem.* 4:90–98 (2012) |
| `NumHDonors`, `NumHAcceptors`, `NHOHCount`, `NOCount`, `NumHeteroatoms`, `NumRotatableBonds`, `HeavyAtomCount`, `FractionCSP3`, `RingCount`, `NumAromaticRings`, `NumSaturatedRings`, `NumAliphaticRings`, carbo/heterocycle counts, `NumAmideBonds`, `NumAtomStereoCenters`, `NumBridgeheadAtoms`, `NumSpiroAtoms` | `rdkit.Chem.Lipinski` | module = *"Calculation of Lipinski parameters for molecules"* |
| `BertzCT` (+ `BalabanJ`, `Ipc`, `HallKierAlpha`, `Chi0–Chi4n/v`, `Kappa1-3`) | `rdkit.Chem.GraphDescriptors` | *"A topological index meant to quantify 'complexity' of molecules"*, citing Bertz, *JACS* 103:3599–3601 (1981). **Documented caveats:** aromatic-bond handling changed so values differ from older RDKit versions, and it fails on a molecule with a 2nd-or-later single-atom fragment |
| Murcko scaffold: `GetScaffoldForMol`, `MurckoScaffoldSmiles`, `MakeScaffoldGeneric` | `rdkit.Chem.Scaffolds.MurckoScaffold` | module = *"Generation of Murcko scaffolds from a molecule"*; narrative docs: *"The RDKit provides standard Murcko-type decomposition"* |
| BRICS: `BRICSDecompose`, `FindBRICSBonds`, `BreakBRICSBonds`, `BRICSBuild` | `rdkit.Chem.BRICS` | *"BRICS provides another method for fragmenting molecules along synthetically accessible bonds"*; source header cites Degen et al., *ChemMedChem* 3:1503–7 (2008), BSD, © Novartis 2009 |

**Descriptor count [measured here]: `Descriptors.descList` has 217 entries in RDKit 2026.09.1.** The docs state no count — the only published number is an example `[3 rows x 208 columns]` from `CalcMolDescriptors()` on an older release. The list is configurable: `setupAUTOCorrDescriptors()` adds 192 `AUTOCORR2D_*` names, and 8 `BCUT2D_*` names exist. **[INFER] 217 built-in descriptors over-cover the paper's 101 RDKit properties outright, and plausibly cover the 15 OpenEye ones too** (`oe_molecular_complexity` ≈ `BertzCT`, `oe_ring_system_count` ≈ `RingCount`/`NumAromaticRings`, `oe_net_charge_neutral_ph` ≈ Dimorphite-DL, §6).

**Per-molecule cost (measured here, single core, osimertinib, 37 heavy atoms, 500 reps):**

| Call | ms/molecule |
|---|---|
| `MolWt` / `ExactMolWt` / `MolLogP` | 0.0002–0.0003 |
| `RingCount` / `HeavyAtomCount` / `NumAromaticRings` | 0.0001–0.0003 |
| `TPSA` | 0.0009 |
| `NumHDonors` / `NumHAcceptors` / `NumRotatableBonds` | 0.0027 / 0.0245 / 0.0519 |
| `BertzCT` | 0.245 |
| `QED.qed` | **0.879** — the expensive one, pure Python |
| `MolFromSmiles` (SMILES parse) | 0.107 |
| `sascorer.calculateScore` | 0.068 |
| `MurckoScaffoldSmilesFromSmiles` | 0.076 |
| 12-property "OpenEye-replacement" panel incl. QED + BertzCT | **0.65** |
| `CalcMolDescriptors` — all 217 | **5.21** |

→ **[INFER] a 116-property panel costs ~1–3 ms/molecule single-threaded**, i.e. hundreds to ~1,400 molecules/second/core. Tier-1 is effectively free.

### B) Synthesizability scores

| | **SA score** | **SCScore** | **SYBA** | **RAscore** | **AiZynthFinder** |
|---|---|---|---|---|---|
| Licence | **BSD-3** (file is © Novartis 2013, own BSD-3 header — cite both) | **MIT** (© 2017 Connor Coley) | **GPL-3.0-or-later** — the one copyleft tool here | **MIT** (© 2020 Reymond Group, U. Bern) | **MIT** (© 2020 Genheden & Bjerrum) |
| DOI | 10.1186/1758-2946-1-8 | 10.1021/acs.jcim.7b00622 | 10.1186/s13321-020-00439-2 | 10.1039/d0sc05401a | 10.1186/s13321-020-00472-1 |
| pip | ships **inside** `rdkit` | **no** (git clone; no `setup.py` at all) | **no — `pip install syba` installs an unrelated bacterial-gene tool** | **no — `pip install rascore` installs an unrelated RAS-protein tool** | `pip install aizynthfinder` 4.4.1 |
| conda-forge | via `rdkit` | no | no (only `-c lich`, noarch) | no | no |
| Native Windows | **yes, verified** — `rdkit/Contrib/SA_Score/` is in the `win_amd64` wheel | not documented, no CI | documented all-platform; recipe ships `conda_build/bld.bat` | not documented; CI Linux+py3.7 only | **documented** — README: *"Linux, Windows or macOS platforms are supported"*, *"tested on Windows 10"* |
| Speed | paper: *"SAscore for 100,000 molecules may be calculated in about 3 minutes"* (2009 Pipeline Pilot, hardware unspecified). **Measured here: 0.068 ms/mol ≈ 14,600 mol/s/core** | **not documented** — only *"fast enough that there is no real reason to use GPUs"* | **not documented** — only *"rapid classification"* | *"computes at least **4500 times faster** than retrosynthetic analysis performed by the underlying CASP tool"*; the labelling run took *"approximately 239 CPU days"* vs *"77 minutes"* for RAscore classification (**body says 77 min, Table 2 says 79 min — they disagree**) | *"typically find a solution in **less than 10 s** and perform a complete search in **less than 1 min**"*; benchmark **average search 38.7 s**, first solution 7.1 s, on *"a single CPU (Intel Xeon 4.00 GHz) and a single GPU (Nvidia GeForce RTX 2080 Ti)"* |
| Last commit | active (2026-10) | **2018-02-05** | **2021-01-18** | **2021-08-25** | 2026-04-13 |

**[FACT] Practical blockers worth knowing before you pick one:**
- **SA score** has no `__init__.py`, so the idiom is `sys.path.append(os.path.join(RDConfig.RDContribDir,'SA_Score')); import sascorer`. This snippet is **not in the RDKit manual** (a grep of the Cookbook, GettingStarted, Overview and RDKit_Book for `sascorer`/`SA_Score`/`ContribDir` returns zero hits) — it is community convention, inferable from RDKit's own `UnitTestSAScore.py`. Master now uses `rdFingerprintGenerator.GetMorganGenerator`, so pre-2024 vendored copies differ.
- **SCScore** uses `dtype=np.bool`, removed in numpy ≥ 1.24, and imports `six`. Retraining pins `tensorflow r0.12.0` (Dec 2016). Inference needs only RDKit + numpy.
- **RAscore** README "Known Installation Issues", verbatim: *"The following versions must be used in order to use the pretrained models: **python == 3.7, scikit-learn == 0.22.1, xgboost == 1.0.2, tensorflow-gpu == 2.5.0**"*. **The Python-3.7 pin, not the OS, is the blocker.** Inference does **not** import AiZynthFinder — that was only used to generate training labels. Authors' own caveat, directly relevant here: **"The models have not been tested for the use case of molecular generation."**
- **AiZynthFinder** at ~40 s/molecule is **4–5 orders of magnitude slower than RDKit descriptors — unusable as an inner-loop oracle.** Avoid the `[all]` extra: it pulls `timeout-decorator`, which uses Unix `signal.SIGALRM` and does not work on Windows.

### C) Open ADMET predictors

| | **ADMET-AI** | **Chemprop** |
|---|---|---|
| Licence | **MIT** (`LICENSE.txt`, © 2026 Kyle Swanson) | **MIT**; README: *"Chemprop is free to use under the MIT License"* |
| Install | `pip install admet-ai` (PyPI 2.0.1, `requires_python >=3.11`, classifier `OS Independent`). **conda-forge: NO** | `pip install chemprop` 2.3.1; **conda-forge: YES**, `noarch` → installs on Windows |
| Windows | *"can be installed in a few minutes on **any operating system** using pip"* — but no Windows CI, and the `[web]` extra pulls **gunicorn**, whose classifiers are MacOS/POSIX only. Core predictor (torch/chemprop/rdkit) is cross-platform | **CI proves it**: `.github/workflows/ci.yml` matrix is `os: [ubuntu-latest, macos-15-intel, windows-2022]`, with the comment `# use pip for windows instead, since conda doesn't work well with DLLs`. **Native Windows, pip, py3.11/3.12** |
| Throughput | **Documented**, abstract verbatim: *"**ADMET-AI can also be run locally with predictions for one million molecules taking just 3.1 h**"* and *"the fastest web-based ADMET predictor, with a 45% reduction in time"* (DOI 10.1093/bioinformatics/btae416). Body: 3.1 h on 32 CPU cores + 1 GPU; ~5 h on 8 cores no GPU. (≈90 mol/s is arithmetic, not stated.) v2 README has no numeric claim | **not documented** |
| Coverage | **41 TDC ADMET endpoints** (10 regression + 31 classification), plus **11 RDKit physchem properties returned by default** (`include_physchem=True`): `molecular_weight, logP, hydrogen_bond_acceptors, hydrogen_bond_donors, Lipinski, QED, stereo_centers, tpsa` + `PAINS_alert, BRENK_alert, NIH_alert`, plus DrugBank-approved percentiles. **No DRD2/GSK3B/JNK3 target oracles** — those are TDC's | general-purpose D-MPNN; you train it |

### D) Ready-made multi-objective benchmarks — reuse these instead of rebuilding Tier-1

**This is the most useful finding of section 3 [INFER]: GuacaMol v2 and PMO already *are* the paper's Tier-1, pre-built, benchmarked and leaderboarded.**

**GuacaMol** — **MIT** (© 2018 BenevolentAI); paper Brown, Fiscato, Segler, Vaucher, *JCIM* **59**(3):1096–1108 (2019), DOI 10.1021/acs.jcim.8b00839. pip `guacamol` 0.5.5; **conda-forge: YES**, `noarch` (its feedstock patches `rdkit-pypi` → `rdkit`).

**[FACT] The 20 goal-directed v2 tasks** (enumerated live by the helper agent, matching `benchmark_suites.py`): Celecoxib / Troglitazone / Thiothixene rediscovery; Aripiprazole / Albuterol / Mestranol similarity; C11H24; C9H10N2O2PF2Cl; Median molecules 1 & 2; **Osimertinib MPO, Fexofenadine MPO, Ranolazine MPO, Perindopril MPO, Amlodipine MPO, Sitagliptin MPO, Zaleplon MPO**; Valsartan SMARTS; Deco Hop; Scaffold Hop. The seven MPOs are geometric means of a similarity term plus TPSA / logP / ring-count / F-count / isomer terms — **structurally the same shape as the paper's "one target property + 2–4 constraints"**. Deco Hop and Scaffold Hop are arithmetic means of a clipped PHCO Tanimoto plus (inverse) SMARTS terms, i.e. **a built-in scaffold constraint**.

⚠️ **[FACT] logP, TPSA, CNS MPO and QED are *not* in v2** — they are v1/trivial-suite only. v1 adds `Cobimetinib MPO`, `Physchem MPO`, `logP (target −1.0)`, `logP (target 8.0)`, `TPSA (target 150.0)`, `CNS MPO`, `QED`.

**[FACT] All 20 v2 objectives are RDKit-only** — `standard_benchmarks.py`, `common_scoring_functions.py` and `utils/descriptors.py` import nothing but `rdkit.Chem` and `TanimotoSimilarity`. **No ML models, no docking, no binaries, no network.** **(measured here) all 20 v2 objectives scored one molecule on native Windows in 8.0 ms total = 0.40 ms per objective per molecule.** Distribution-learning suite is 5 metrics: Validity, Uniqueness, Novelty, KL divergence, Frechet ChemNet Distance — only FCD needs external software (the third-party `fcd` package, **LGPL-3.0**, not MIT). ChEMBL splits **(measured)**: train 1,273,104 / valid 79,568 / test 238,706 / all 1,591,378 SMILES. Last code commit **2022-07-15**.

⚠️ **[FACT] Two real Windows gotchas, found by code inspection and reproduced live:**
1. `guacamol/utils/chemistry.py` line 10 is `from scipy import histogram`, **removed from modern SciPy** → `ImportError` on *any* guacamol import. Still present on master; the conda-forge feedstock carries **only** `rdkit-dep.patch`, no scipy patch. Workaround: set `scipy.histogram = numpy.histogram` before importing, or pin an old SciPy.
2. `pip install guacamol` on Python 3.14 silently installs **0.5.2**, not 0.5.5, because 0.5.5 requires `rdkit-pypi>=2021.9.2.1` which has no 3.14 wheels. conda-forge fixes this; PyPI does not. 0.5.2 also does not declare rdkit as a dependency, and guacamol pulls **FCD → tensorflow + keras**.

**PMO / `mol_opt`** — **MIT** (© 2022 Wenhao Gao); Gao, Fu, Sun, Coley, *NeurIPS 2022 Datasets & Benchmarks*, arXiv:2206.12411.

**[FACT] The 23 oracles**, verified against `make_run_prod.sh`'s `oracle_array` (the authoritative production driver): `albuterol_similarity, amlodipine_mpo, celecoxib_rediscovery, deco_hop, drd2, fexofenadine_mpo, gsk3b, isomers_c7h8n2o2, isomers_c9h10n2o2pf2cl, jnk3, median1, median2, mestranol_similarity, osimertinib_mpo, perindopril_mpo, qed, ranolazine_mpo, scaffold_hop, sitagliptin_mpo, thiothixene_rediscovery, troglitazone_rediscovery, valsartan_smarts, zaleplon_mpo`. Provenance: 19 GuacaMol objectives through TDC + `qed` + 3 ML oracles (`drd2`/`gsk3b`/`jnk3`, which download model files). *Caveat: `run.py`'s `__main__` loops over a stale 24-name list — that is not the benchmark definition.*

**[FACT] PMO's budget protocol is exactly what an RL reward loop needs**, and is worth copying wholesale: `main/optimizer.py` sets `self.max_oracle_calls = 10000`, canonicalises SMILES with RDKit in `score_smi()`, **returns 0 once the budget is exhausted**, returns 0 for invalid SMILES, and **caches every molecule in `self.mol_buffer` so repeat queries are free and do not consume budget**. Primary metric is **AUC top-K** (the paper headlines AUC top-10, min-max scaled). It also instantiates `tdc.Oracle('SA')`, `tdc.Evaluator('Diversity')` and `MolFilter(filters=['PAINS','SureChEMBL','Glaxo'])`, and loads its start library via `tdc.generation.MolGen(name='ZINC')`. **Adding your own objective = supplying any TDC oracle name or any `Callable[[str], float]`.**

**[FACT] PMO is not pip-installable and not on conda-forge** (`setup.py` declares `name='mol_opt'` but nothing is published). Git clone only. Documented env is `python=3.7` + **PyTDC 0.3.6** (current is 1.1.15 — a big gap). **Windows not documented**: `run.sh` uses `ulimit -n 4096` and `nohup`, and `make_run_prod*.sh` generate `.slurm` scripts. `python run.py <method>` itself is portable. Last commit 2024-05-23 — the most actively maintained of the three suites. The paper benchmarks **25 algorithms on 23 tasks**; the README now says 29 methods.

**PyTDC / Therapeutics Data Commons** — **MIT** (© 2020 TDC Team); *"For individual dataset usage, please refer to the dataset license on the website"*; the **Molecule.one** oracle is *"permitted only for non-commercial use"*. pip **`PyTDC`**; **conda-forge: YES** as `pytdc` (noarch, lags PyPI).

**[FACT] Oracle inventory** from `tdc/metadata.py` (names are fuzzy-matched, so `Oracle(name='GSK3B')` → `gsk3b`):
- `trivial_oracle_names = ["qed","logp","sa"]` — **QED, SA and penalized LogP ship RDKit-only with zero extra deps.**
- `download_oracle_names`: **`drd2, gsk3b, jnk3`**, `fpscores`, `cyp3a4_veith` (+ `_current` variants auto-selected when scikit-learn ≥ 0.24) — pickled predictors downloaded on first call.
- `guacamol_oracle`: **29 names**, including all seven MPOs, `deco_hop`, `scaffold_hop`, `valsartan_smarts`.
- `meta_oracle_name`: `isomer_meta, rediscovery_meta, similarity_meta, median_meta, docking_score, molecule_one_synthesis, pyscreener` — the `*_meta` ones take `target_smiles=` so **you can define your own objectives**.
- `distribution_oracles`: `novelty, diversity, uniqueness, validity, fcd_distance, kl_divergence`.
- `synthetic_oracle_name`: `askcos, ibm_rxn` (+ `molecule_one_synthesis`) — **all three are network/service-dependent** (self-hosted ASKCOS over HTTP; IBM RXN needs an API key; Molecule.one needs a token).
- **Docking: 30 receptor oracles** — 10 targets (`1iep, 2rgp, 3eml, 3ny8, 4rlu, 4unn, 5mo4, 7l11, drd3, 3pbl`) × 3 variants (`_docking`, `_docking_normalize`, `_docking_vina`), plus `docking_oracles = [rmsd, kabsch_rmsd, smina]`. `PyScreener_meta` accepts `software_class` ∈ `["vina","qvina","smina","psovina","dock","dock6","ucsfdock"]`. There is a published **DRD3 docking leaderboard at 100 / 500 / 1,000 / 5,000 oracle calls** (<https://tdcommons.ai/benchmark/docking_group/overview/>).
- `tdc.chem_utils.MolFilter`: filter sets `BMS, Dundee, Glaxo, Inpharmatica, LINT, MLSMR, PAINS, SureChEMBL` plus property windows (HBA 0–10, HBD 0–5, LogP −5–5, MW 0–500, Rot 0–10, TPSA 0–200). It wraps Pat Walters' MIT `rd_filters` and **auto-installs it from GitHub at runtime**.

⚠️ **[FACT] TDC gotchas:** **`pip install PyTDC` fails on Python 3.14 (measured here)** — it resolves `scikit-learn==1.2.2`, which has no 3.14 wheel, and the sdist build dies in Cython. **Use Python ≤ 3.12.** All three CI workflows are `ubuntu-latest`. **TDC's docking oracles are effectively POSIX-only** and TDC never says so: the `smina` oracle does `os.system(f"chmod +x ./{smina_model_path}")` then `os.popen(f"./oracle/smina.static …")`; the PyPI `vina` package publishes **only** manylinux/musllinux wheels with `MacOS X` / `POSIX :: Linux` classifiers and **no Windows**; and the docs tell you to edit `.bashrc`. → **WSL, Linux, or the pyscreener Docker image.**

**MOSES** — **MIT** (© 2018 Insilico Medicine); Polykovskiy et al., *Front. Pharmacol.* **11** (2020), DOI 10.3389/fphar.2020.565644. ⚠️ **pip name is `molsets`, not `moses`**; conda-forge has **`molsets`** (noarch) and **no `moses`**; the feedstock carries a hard **`rdkit >=2019.09.3,<2021`** pin — the practical pain point. **[FACT] MOSES ships distribution-learning metrics only, no goal-directed objectives**: `get_all_metrics` returns 21 numbers (`valid`, `unique@1000/10000`, `FCD/Test`, `FCD/TestSF`, `SNN`, `Frag`, `Scaf`, `IntDiv`, `IntDiv2`, `Filters`, Wasserstein-1 distances for `logP`/`SA`/`QED`/`weight`, `Novelty`); README recommends sampling ≥30,000 molecules. Windows not documented; the documented paths are `nvidia-docker`, `apt-get`, `git lfs`. Last real code change 2021-09-01.

**[INFER] What to reuse instead of rebuilding Tier-1:** take **GuacaMol v2's 20 goal-directed tasks** as your Tier-1 task pool and **PMO's 10,000-call budget + AUC-top-10 protocol** as your evaluation harness. That gives you published leaderboards to compare against, a scaffold-constrained objective (Deco Hop / Scaffold Hop) mirroring the paper's scaffold constraint, and a `mol_buffer` caching pattern you would otherwise have to invent. Build custom tasks only where you need the paper's specific "sample a ZINC molecule, derive 2–4 constraints" generator.

## 4. SQM2.20 and the semiempirical tier

### What SQM2.20 is

Primary source: Pecina, Fanfrlík, Lepšík, Řezáč, *Nat. Commun.* **15**, 1127 (2024), <https://doi.org/10.1038/s41467-024-45431-8>, open access at <https://pmc.ncbi.nlm.nih.gov/articles/PMC10847445/>.

**[FACT]** SQM2.20 is a *scoring function*, not a program you install. Its stack:
- Gas-phase interaction energy ΔE_int at **PM6-D3H4X**.
- Solvation ΔΔG_solv with the **COSMO2** model at the PM6 level.
- Ligand conformational free energy, proton-transfer energy and an entropy term, using PM6-D3H4X/COSMO2 or the LM5 model.
- PM6 calculations run in **MOPAC2016** with the **MOZYME** linear-scaling solver; **Cuby4** adds the D3H4X corrections and drives the MOPAC/COSMO2 interface; **AMBER 20 / AmberTools** does system preparation.

**[FACT] Cost: "an average calculation time of ~20 minutes per P-L complex."** The paper gives no core count or hardware in the main text (that is in Supplementary Note 6, which I did not retrieve) — so **cores/hardware: not documented** here. Cost comparisons in the paper: docking and ML scoring are *"much faster (taking mere seconds to complete)"*; SQM2.20 *"can be computed in minutes as opposed to DFT, which takes hours or days"* and was *"four orders of magnitude faster"* than the DFT scoring it was benchmarked against. Validation set: **PL-REX**, 10 targets, average R² = 0.69.

**[FACT] Is SQM2.20 free?** Partially, and *there is no standalone tool*. The Code-availability statement names MOPAC, AmberTools and Cuby4, *"all of which are open source software"*, and says a standalone SQM2.20 tool is planned: *"these developments will be announced separately in the future."* No licence is stated for the SQM2.20 code itself. The competing-interests statement notes **IOCB Prague "is licensing the know-how on the SQM-based scoring function within a collaborative project funded by a U.S.-based pharmaceutical company."** PL-REX data/structures/scores: <https://github.com/Honza-R/PL-REX>, archived at <https://doi.org/10.5281/zenodo.8182922>.

**[INFER]** So reproducing SQM2.20 exactly means re-assembling PM6-D3H4X + COSMO2 yourself from MOPAC + Cuby4. That is a research project, not a setup step. Do not attempt it as a beginner.

### Open components and alternatives

| Tool | Licence | Platform | conda-forge | Relevant capability | Documented speed |
|---|---|---|---|---|---|
| **MOPAC** (open-source continuation of MOPAC2016) <https://github.com/openmopac/mopac> | **Apache-2.0** (as labelled on the repo; full LICENSE text not read) | *"Pre-built versions of MOPAC on Linux, Mac, and Windows are available with every GitHub Release"* → **native Windows** | `mopac` (`conda install -c conda-forge mopac`) | <https://openmopac.net/> lists AM1, PM6, PM7, a **MOZYME solver** and a **COSMO** implicit-solvation model. **PM6-D3H4X and PM6-ORG: not mentioned on that page → not documented.** COSMO2 specifically: not documented. | Repo says semiempirical is "roughly 1000x faster than ab initio"; **no protein timings documented** |
| **xtb** (GFN1/GFN2-xTB, GFN-FF) <https://github.com/grimme-lab/xtb> | **LGPL-3.0** (README: "GNU Lesser General Public License … either version 3"; `COPYING` + `COPYING.LESSER`) | conda packages for Linux (x86_64/aarch64/ppc64le) and macOS; **statically linked release binaries include Windows** ("Windows (Intel 2022, GNU-15) is provided"). Docs note the 6.7.1 Windows build is a pre-release (`6.7.1pre`) due to MSVC C++ deprecation: <https://xtb-docs.readthedocs.io/en/latest/> | `xtb` | GFN2-xTB single points, geometry optimisation, frequencies/thermochemistry, GBSA implicit solvation, MD/metadynamics | **Speed: not documented in the repo or the official docs.** GFN2-xTB (JCTC 2019, DOI 10.1021/acs.jctc.8b01176) targets systems of ~1000 atoms; GFN-FF (Spicher & Grimme, *Angew. Chem.* 2020) targets beyond ~1000 atoms, and the AMS implementation notes it is single-core. A third-party supporting table reports GFN2-xTB single-point **~1 s per complex on 1 CPU core** vs ~1000–1500 s for ωB97X-D/def2-QZVP on 8 cores — **secondary, not a Grimme-group benchmark; treat as indicative only.** |
| **Psi4** <https://github.com/psi4/psi4> | **LGPL-3.0** (README: text in `COPYING.LESSER`) | README: binaries *"available for Linux, Mac, Mac Silicon, Windows, and WSL Windows"*; CI on Linux and Windows → **native Windows** | `psi4` | "an open-source suite of **ab initio** quantum chemistry programs" — semiempirical support **not documented** | not documented |
| **ORCA** <https://www.faccts.de/orca/> | **Not open source.** Page: ORCA *"is and will remain free for academic and personal use"*; commercial licences via FACCTs, **price not published** | Free download is described as "the latest **Linux** version"; other versions via <https://orcaforum.kofo.mpg.de> | no | DFT/ab initio, some semiempirical | not documented |

**[FACT caveat] Cuby4:** <http://cuby4.molecular.cz/> **was unreachable at the time of writing** (connection refused, 147.231.128.93:443). Řezáč's own publication describes Cuby as an open-source integrative framework (*J. Comput. Chem.* **37**, 1230–1237, 2016), and the SQM2.20 paper calls it open source, but **I could not read its LICENSE file or confirm a current download location → licence unverified.**

### Is dropping the expensive tier sane?

**[FACT]** The paper does **not** train on SQM2.20. It uses it *only* as the held-out, never-trained-on evaluation target, with a budget of at most five calls per rollout, on 40 PLINDER test systems. The core claim is explicitly about *transfer*: curriculum training on cheap synthetic tasks (Tier-1 → Tier-2) generalises to an expensive oracle that was never in the reward.

**[INFER] Therefore dropping the expensive tier changes *what you can claim*, not *what you can train*.**
- Training is unaffected: you never needed SQM2.20 to run the curriculum.
- What you lose is the headline result. Without an expensive held-out oracle you cannot demonstrate "cheap-to-expensive transfer" at all — you can only show "Tier-1 → Tier-2 transfer", i.e. that curriculum training on property tasks improves docking-reward tasks. That is a weaker but still meaningful and testable version of the claim.
- **Recommended compromise [INFER]:** keep *a* held-out expensive-ish tier but make it cheap enough to afford — e.g. GFN2-xTB rescoring of the docked pose (minutes, free), or simply a *different and harder docking setup* (different scoring function + exhaustiveness, e.g. Vinardo via smina, or gnina's CNN score) held out from training. The scientific structure (train cheap, evaluate on an oracle never used as reward) survives; only the fidelity of the top tier drops. Say so plainly in any write-up.

---

## 5. Datasets: licence, access, size

Sizes marked **(measured)** were read from the server's own directory index or an HTTP `Content-Length` header on 2026-10-09 — none of these projects publish size tables, so this is the most authoritative figure available, and it will drift with releases.

| Dataset | Licence | Registration | Download size | Windows |
|---|---|---|---|---|
| **ZINC 250k** subset (`250k_rndm_zinc_drugs_clean_3.csv`, in `aspuru-guzik-group/chemical_vae`) | Repo **Apache-2.0**; ZINC redistribution clause applies upstream (repo silent → **not documented**) | no | **21.6 MiB (measured)** | trivial |
| **GuacaMol** standard splits | Code **MIT**; each figshare article is **CC BY 4.0 (measured** via figshare API, articles 7322228/43/46/52**)**; README itself states no data licence | no | train 59.0 MiB, valid 3.7 MiB, test 11.1 MiB, all 73.7 MiB → **~74 MiB total (measured)**; MD5s published | **perfect** — four plain HTTPS files |
| **MOSES** | Code **MIT**; **data licence not documented** (derived from ZINC Clean Leads) | no | `dataset_v1.csv` = **80.6 MiB (measured)**; 1,936,962 molecules (~1.6 M train / ~176 k test / ~176 k scaffold test) | good — but it's a **Git LFS** file, so a plain `git clone` without git-lfs gives a pointer stub. Fetch the `media.githubusercontent.com/media/...` URL |
| **ChEMBL 37** (prepared 01/05/2026) | **CC BY-SA 3.0 Unported**, stated in the dump's own `README` + full text in `LICENSE` + a `REQUIRED.ATTRIBUTION` file, at <https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/> | no | 2,921,148 compounds, 24,527,044 activities. `chembl_37_chemreps.txt.gz` (SMILES/InChI) = **279 M**; `chembl_37.sdf.gz` = **888 M**; `chembl_37_sqlite.tar.gz` = **5.4 G** (uncompressed `.db` size **not documented**; plan 20 GB+) | **excellent** — SQLite needs no server, stdlib `sqlite3` reads it; `tar` ships with Win 10+ |
| **PLINDER** <https://github.com/plinder-org/plinder> | **Apache-2.0 for the data *and* the code**, with carve-outs quoted in the README: BindingDB-curated data is **CC BY 4.0**, ChEMBL-imported data is **CC BY-SA 4.0**. Code licence **changed from GPL-2.0 to Apache-2.0** once PLIP was removed | **none** — README: *"No Google Cloud credentials or SDK are needed"* | **Default `plinder_download` = the ~1.5 GiB `index/` group** and it *asks* before pulling the rest. **Full 2026-09 release = 64.00 GiB (measured)**, of which `exports/` similarity tables are 57.65 GiB (three files: 31G + 12G + 10G). 400k PLI systems, >11k SCOP domains, >50k unique ligands. Split config: `num_test: 1000`, `num_val: 1000`. Per-split bytes **not documented** | **good now** — `pip install plinder` + plain HTTPS from `cameo3d.org`. Old 0.2.x releases were `gsutil -m cp -r gs://plinder/...` and awkward |
| **PDBbind / PDBbind+** <https://www.pdbbind-plus.org.cn/> | Operated by **Fudan University / TopScience**. Platform FAQ, verbatim: *"the PDBbind database was free-accessible up to version 2020, and it became **commercialized since version 2021**"*; *"For versions 2021 and later: You need to **purchase the subscription**… For version 2020: You can directly download the dataset from the download page without needing a subscription."* Free tier is governed by a "LICENSE AGREEMENT FOR DEMO USERS". Price: *"varies depending on the version and subscription type (academic, commercial)"* → **not published** | **yes, an account is required even for free v2020** (`/api/download/list` returns `{"code":10011,"msg":"Please log in first"}`) | v2020: **23,496 complexes**, of which **19,443 protein–ligand** (the "general set"); "refined set" = healthy subset; "core set" ships only inside CASF. **CASF-2016 = 285 complexes, 1.46 GB; CASF-2013 = 636 MB; CASF-2007 = 92 MB (measured** from archived pages**)**. v2020 general/refined tarball byte sizes: **not documented** (login-gated in every archived capture) | easy — browser download after registering |
| **LP-PDBBind** <https://github.com/THGLab/LP-PDBBind> (free alternative) | UC Regents permissive research licence: *"Permission to use, copy, modify, and distribute… for educational, research, and not-for-profit purposes, **without fee and without a signed licensing agreement**"*; commercial use requires UC Berkeley OTL. GitHub classifies as `NOASSERTION` | no | `LP_PDBBind.csv` 10.9 MB; `BDB2020+.tgz` 35.0 MB; `mpro.tgz` 11.7 MB; `EGFR.tgz` 2.2 MB **(measured)** | trivial — **but** README: *"Only the meta-information… are present in the csv file. Users need to download the prepared structure files… from the PDBBind website."* **It is a re-split, not a mirror — it does not route around the paywall.** |
| **CrossDocked2020** <http://bits.csb.pitt.edu/files/crossdock2020/> | **Data licence not documented.** `gnina/models` is Apache-2.0 as a repo; the data README makes no claim over the tarballs. Paper DOI 10.1021/acs.jcim.0c00411 | none, anonymous HTTP | **(all measured)** full `CrossDocked2020_v1.3.tgz` = **50.3 GiB**; `..._types.tgz` 3.48 GiB; `lig.molcache2` 17.8 GiB; `rec.molcache2` 2.06 GiB; **downsampled** tarball 7.35 GiB, its types 21 MiB, its molcaches 1.92 + 0.90 GiB → **~2.8 GiB molcache route**. README: *"WARNING -- `CrossDocked2020_v1.3.tgz` contains **52,126,979 files**!!"*, needs *"about 22Gb of data… loaded into memory"* vs *"about 5Gb"* downsampled | **full tarball effectively impractical on Windows** — `tar` exists on Win 10+ but extracting **52 M small files onto NTFS** will take days. Use the molcache2 + types route (no mass extraction) |
| `crossdocked_pocket10` (the ML-community subset) | **not documented** | no (Google Drive) | **not documented.** Comes from the AR / Pocket2Mol / TargetDiff line: `crossdocked_pocket10.tar.gz` + `split_by_name.pt` from <https://github.com/luost26/3D-Generative-SBDD>; TargetDiff (<https://github.com/guanjq/targetdiff>) documents regenerating it from v1.1 (`clean_crossdocked.py` keeps RMSD < 1 Å; `extract_pockets.py` clips to a 10 Å shell) | Google Drive |
| **ZINC20** 2D tranches <https://files.docking.org/2D/> | **No OSI/CC licence.** The only licence text is the server banner: *"Whereas you are free to share the results of a ZINC search or a screen of molecules from ZINC, **you may not redistribute major portions of ZINC without the express written permission of John Irwin**"*. Papers say only "freely available" | none for ZINC20 | 1.4 B compounds (1.3 B purchasable). **(measured)** all 121 first-level tranches = 4,275 `.smi` files = **106.9 GiB**, plus 202.6 GiB of property `.txt` → **309.4 GiB**. A single tranche (`JH`) is 1.02 GiB; one leaf (`AA/AAAE.smi`) is 8.3 MB → **a usable subset is selectable at the 10 MB–1 GB scale** | easy tooling, huge data. The ZINC-22 paper lists **curl, wget, PowerShell and rsync**. Note `zinc20.docking.org` 302s to a CAPTCHA for non-browser clients **(measured)** — script against `files.docking.org` |
| **ZINC22** | same redistribution clause | **partial basic auth** — `/zinc22/2d/` returns **401 (measured)**; <https://files.docking.org/zinc22/> publishes the hint in plain text (GPCR acronym / crystal abbreviation, both four lowercase letters). Enamine REAL Space 13.5 B is by email request | >37 B 2D, >4.5 B in 3D. Paper's own sizes: **~1 TB per billion** in mol2/sdf/pdbqt; **~200 TB per billion** in db2; 4.5 B in db2 *"consume nearly a petabyte"* and would take *"nearly three months to download at 1 Gbps"* | **no** |
| **PubChem** bulk | NCBI policy says no restrictions on most data **but explicitly names PubChem** among resources where depositors may retain copyright → **effectively open, not a clean single licence** | none | full `Compound/CURRENT-Full/SDF/` = **359 shards, 108.7 GiB compressed (measured)**. Practical alternative `CID-SMILES.gz` = **1.38 GiB (measured)** | easy; take `CID-SMILES.gz` |
| **DUD-E** <https://dude.docking.org/> | **not documented on the site** — no licence or terms page. The `files.docking.org` banner lists "DUDE" among its products, so the ZINC clause attaches only by association | none | 22,886 actives across **102 targets** (~224 ligands/target), **50 decoys per active**. `all.tar.gz` = **2.59 GiB (measured)**; per-target packages much smaller. Successor DUDE-Z at <https://dudez.docking.org> | easy |
| **LIT-PCBA** | **not documented** — only a citation request (Tran-Nguyen & Rognan, *JCIM* 2020, 60(9):4263–4273) | none | 15 targets, 7,761 actives, 407,839 inactives. **Size unknown — all three official download URLs return HTTP 404 (measured 2026-10-09)**, including `LIT-PCBA_full.tar.gz` and `LIT-PCBA_AVE_unbiased.tar.gz`. You would have to email the Strasbourg group | blocked |

### Dataset recommendation for this project **[INFER]**

- **Molecule corpus / generative benchmark:** GuacaMol splits (74 MB, CC BY 4.0) or MOSES (80 MB, MIT). Both are single HTTPS downloads with a clear licence and no registration.
- **Build-your-own corpus:** `chembl_37_chemreps.txt.gz`, 279 MB, CC BY-SA 3.0 — every ChEMBL SMILES without touching a database.
- **Reproduce VAE-era papers:** ZINC-250k, 22 MB.
- **3D pockets for the Tier-2 docking reward:** **PLINDER's default ~1.5 GiB download** is the right choice — it is what the paper itself uses, it is Apache-2.0, and it needs no registration. This is the single most important finding of this section: **the paper's own structural dataset is free and small.**
- **Only if you need more pockets:** CrossDocked2020 **downsampled molcaches** (~2.8 GiB). Never the 50 GiB / 52-million-file tarball on NTFS.
- **Avoid:** PDBbind (registration-gated, frozen at v2020 unless someone pays), full ZINC tranches, ZINC22 3D, PubChem full SDF, LIT-PCBA (broken links).

**Gaps the agent could not close:** PDBbind v2020 refined-set entry count and package byte sizes (login wall in every archived capture); size and licence of the community `crossdocked_pocket10` subset. The ZINC20 309 GiB total is a sum over a 121-directory crawl, **not a published figure**.

## 6. Windows reality

### 6.1 WSL2 + CUDA is officially supported

**[FACT]** Microsoft documents that *"Windows 11 and later updates of Windows 10 support running existing ML tools, libraries, and popular frameworks that use NVIDIA CUDA for GPU hardware acceleration inside a Windows Subsystem for Linux (WSL) instance"*, including PyTorch, TensorFlow, Docker and the NVIDIA Container Toolkit — <https://learn.microsoft.com/windows/ai/directml/gpu-cuda-in-wsl>. Setup: install the NVIDIA CUDA-enabled driver **for Windows** (no separate Linux display driver), then `wsl --install` a glibc distro; kernel ≥ 5.10.43.3. See also <https://learn.microsoft.com/windows/wsl/tutorials/gpu-compute>.

**[INFER] Consequence:** "Linux-only" is *not* a blocker for any GPU docking tool on this machine. WSL2 with GPU passthrough is the default execution environment to assume; only choose native-Windows builds where convenience matters (RDKit, Open Babel, MOPAC, Psi4 all have them). The Windows-edition restrictions that appear in Microsoft's GPU-PV tables apply to Azure IoT Edge / AKS Edge Essentials, **not** to WSL2 CUDA, so Windows 11 Home is fine.

### 6.2 Per-tool verdicts

Verdicts are from each project's own README/docs/CI/packaging as cited in the sections above. "**Yes (verified)**" means a helper agent actually installed and ran it on this machine.

| Tool | Native Windows? | conda-forge | Notes |
|---|---|---|---|
| **RDKit** | **Yes (verified)** | **yes** (`rdkit`, win-32/win-64) | pip wheels for CPython 3.10–3.15; the whole Tier-1 substitute in one dependency |
| **SA score** (`sascorer`) | **Yes (verified)** | via `rdkit` | ships inside the `win_amd64` wheel at `rdkit/Contrib/SA_Score/` |
| **Dimorphite-DL** | **[INFER] yes** (pure Python) | no (PyPI `dimorphite-dl`) | not documented upstream |
| **PoseBusters** | not documented | no (PyPI `posebusters`) | MIT; the paper's own pose filter |
| **Open Babel** | **Yes** — *"available as a binary installer for Windows, both 64-bit (preferred) or 32-bit"* | not mentioned in install docs | CLI + GUI; PDBQT support not confirmed on the pages read |
| **Meeko** | not documented (pure Python → **[INFER] fine**) | **yes** (`meeko`) | PDBQT prep for ligands *and* receptors |
| **smina** | **Yes** — conda-forge publishes real `win-64` artefacts | **yes** (`smina`) | the only maintained native-Windows docking engine |
| **AutoDock Vina 1.2.7** | **Yes, CLI only** (`vina_1.2.7_win.exe`, undocumented) | **no win-64** (`skip: true # [win]`) | Python bindings are *"Linux and Mac only"* |
| **AutoDock-GPU 1.6** | **Yes** (`AutoDock-GPU.exe`) | no | GPL-2.0 |
| **Vina-GPU 2.x / QuickVina2-GPU** | **Yes, first-class** (VS 2019 + `.exe` + GUI) | **no — source build only** | dormant since Oct 2024 |
| **gnina** | **No** — *"The pre-built binary can be used in WSL"*; WSL2 build steps provided | no | CUDA >= 12.0 |
| **Uni-Dock** | **No** — *"on Linux platform"* | **yes, `linux-64` only** | WSL2 works but is undocumented |
| **DiffDock / DiffDock-L** | **No** — `+cu117` wheels + `openfold`; Windows never mentioned | no | Docker `rbgcsail/diffdock` |
| **Chemprop** | **Yes** — CI matrix includes `windows-2022` | **yes** (noarch) | |
| **ADMET-AI** | *"any operating system"* + `OS Independent`; no Windows CI. `[web]` extra's gunicorn is POSIX-only | **no** | pip `admet-ai` |
| **GuacaMol** | **Works (verified)** but needs the `scipy.histogram` patch | **yes** (noarch) | all 20 v2 objectives are RDKit-only |
| **PyTDC** | not documented; **pip fails on Python 3.14** — use <= 3.12. Its **docking** oracles need WSL/Linux/Docker | **yes** (`pytdc`, noarch) | |
| **MOSES** | not documented; documented paths are apt/nvidia-docker/git-lfs | **yes as `molsets`** (noarch, `rdkit<2021` pin) | distribution metrics only |
| **PMO / `mol_opt`** | not documented; drivers are bash/`ulimit`/slurm | **no** (git clone) | `python run.py <method>` itself is portable |
| **SYBA** | documented all-platform; recipe ships `bld.bat` | no (`-c lich`) | **GPL-3.0** |
| **SCScore** | not documented | no | `np.bool` breaks on numpy >= 1.24 |
| **RAscore** | not documented; Windows wheels exist for all pins | no | blocker is **Python 3.7**, not the OS |
| **AiZynthFinder** | **documented** — *"tested on Windows 10"* | no | avoid `[all]` (`timeout-decorator` needs SIGALRM) |
| **MOPAC** (open) | **Yes** — *"Pre-built versions… on Linux, Mac, and Windows… with every GitHub Release"* | **yes** (`mopac`) | PM6/PM7, MOZYME, COSMO |
| **xtb** | **Yes**, statically linked release binaries incl. Windows; docs note 6.7.1 Windows is a `pre` build | **yes** (`xtb`) | LGPL-3.0 |
| **Psi4** | **Yes** — *"binaries… for Linux, Mac, Mac Silicon, Windows, and WSL Windows"* | **yes** (`psi4`) | ab initio; semiempirical not documented |
| **OpenMM** | not stated on the repo page (AppVeyor + Azure configs suggest it is tested) | **yes** (`openmm`) | MIT/LGPL mix |
| **ORCA** | free download is *"the latest **Linux** version"* | no | not open source |
| **Cuby4** | unknown — **official site unreachable (connection refused) on 2026-10-09** | no | licence unverified |

**[INFER] The single most important Windows fact** is 6a: WSL2 + CUDA is officially supported on Windows 11, so "Linux-only" costs you `wsl --install` and nothing else. Do not contort the stack to stay native.

---

## 7. Recommended minimal free stack

| Paper's oracle | Free substitute | Licence | Where it runs |
|---|---|---|---|
| Tier-1: 116 properties (101 RDKit + 15 OpenEye) | **RDKit** `Descriptors.CalcMolDescriptors` (217 descriptors) + `MurckoScaffold` + `BRICS` + `sascorer`; Dimorphite-DL for the pH-charge property | BSD-3 / Apache-2.0 | **native Windows** |
| Tier-1 task generator + scaffold constraint | **GuacaMol v2's 20 goal-directed tasks** (7 MPOs + Deco/Scaffold Hop), run under **PMO's 10,000-call / AUC-top-10 protocol** | MIT | native Windows (patch `scipy.histogram`) |
| Tier-2: POSIT template docking | **RDKit `AllChem.ConstrainedEmbed`** against the crystallographic ligand (or its MCS) | BSD-3 | native Windows |
| Tier-2: Chemgauss4 scoring | **smina `--minimize --autobox_ligand <crystal_lig>`** with the **Vinardo** scoring function; scale to **Uni-Dock `--search_mode fast`** in WSL2 if throughput binds | Apache-2.0 / GPLv2 (disputed) / Apache-2.0 | native Windows / WSL2 |
| Tier-2 pose sanity | **PoseBusters** (the paper's own filter) | MIT | pip |
| Held-out expensive oracle (SQM2.20) | **Option A (recommended): drop it** and hold out a *harder docking configuration* instead (gnina `--cnn=fast`, or Vinardo at high exhaustiveness, never used as reward). **Option B: GFN2-xTB rescoring** of the minimised pose via `xtb`. **Option C: do not attempt SQM2.20** — it has no standalone implementation | Apache-2.0 / LGPL-3.0 | WSL2 / native |
| Structures | **PLINDER** default download (~1.5 GiB) — exactly what the paper uses | Apache-2.0 | native Windows, plain HTTPS |
| Molecule corpus | **GuacaMol splits** (74 MB) or **ChEMBL 37 `chemreps`** (279 MB) | CC BY 4.0 / CC BY-SA 3.0 | native Windows |
| Prep | **Meeko** + **Open Babel** | LGPL-2.1 / GPL-2.0 | native Windows |

**Total download: well under 3 GB. Total licence cost: zero. Nothing in the critical path requires a non-commercial-only licence.**

### Rough per-evaluation time budget

Documented or measured figures first, then the derived budget. **All derived numbers are [INFER].**

| Oracle | Cost | Provenance |
|---|---|---|
| SMILES parse | 0.107 ms | measured here |
| One cheap descriptor | 0.0001–0.05 ms | measured here |
| `QED` | 0.879 ms | measured here |
| `BertzCT` | 0.245 ms | measured here |
| SA score | 0.068 ms | measured here |
| Murcko scaffold | 0.076 ms | measured here |
| **12-property panel** | **0.65 ms** | measured here |
| **All 217 RDKit descriptors** | **5.21 ms** | measured here |
| **One GuacaMol v2 objective** | **0.40 ms** | measured here |
| **All 20 GuacaMol v2 objectives** | **8.0 ms** | measured here |
| ADMET-AI, 41 endpoints | ~11 ms/mol (1 M in 3.1 h on 32 cores + 1 GPU) | **documented** (abstract) + my arithmetic |
| `ConstrainedEmbed` template pose | **not documented** — [INFER] ~10–100 ms | — |
| smina `--minimize` / `--score_only` | **not documented**; README claims 10–20x faster than Vina minimisation | documented (relative only) |
| Full-exhaustiveness CPU docking (Vina/smina) | **126 s/complex on 16 CPUs** | documented (DiffDock Table 1) |
| gnina `--cnn=fast` | **~16 s/complex on 4 CPU cores** | documented (GNINA 1.3 paper) |
| gnina 1.3 default ensemble | **~23 s/complex on 4 CPU cores** | documented |
| Vina-GPU on an RTX 3090 | **~3.7 s/ligand** (9,125 cpds in ~9.44 h) | my arithmetic from documented totals |
| Uni-Dock on a V100 | **~0.11 s/ligand** (38.2 M in 12 h on 100 V100s, **hierarchical**) | my arithmetic; not a uniform rate |
| DiffDock, 10 samples | **10 s on an A100 40GB**, preprocessing excluded | documented |
| AiZynthFinder retrosynthesis | **~38.7 s/molecule average search** | documented |
| GFN2-xTB single point | **~1 s/complex on 1 core** for a PDBbind complex | **third-party supporting table, not a Grimme benchmark — indicative only** |
| **SQM2.20 (the paper's own)** | **~20 min per protein-ligand complex**; the paper itself says "tens of minutes" | documented |

**[INFER] Resulting budget per RL rollout step**

- **Tier-1 only:** ~1–10 ms per molecule. A 10,000-call PMO-style budget costs **under 2 minutes of oracle time**. Tier-1 is free; your wall clock is entirely LLM generation.
- **Tier-2 the cheap way** (ConstrainedEmbed + smina `--score_only`/`--minimize`): **[INFER] ~0.1–2 s per molecule** on CPU. 1,000 scores ~ 2–30 min. **This is the regime the paper describes ("order of seconds") and it is reachable on one Windows box.**
- **Tier-2 the naive way** (full-exhaustiveness Vina/smina at 126 s): 1,000 scores ~ **35 h on 16 CPUs**. Do not do this.
- **Tier-2 at scale** (Uni-Dock `fast` in WSL2 on a consumer GPU): **[INFER] likely 0.1–1 s/ligand, but unmeasured on consumer hardware** — Uni-Dock's absolute numbers exist only as unreadable PNGs. **Measure before you budget.**
- **Expensive tier:** SQM2.20 at ~20 min x even 5 calls per rollout x 200 rollouts ~ **333 CPU-hours for one evaluation run** — and that assumes you had an implementation, which does not exist standalone. **Drop it.**

### What survives if you drop the expensive tier

**[FACT]** The paper never trains on SQM2.20; it is purely the held-out generalisation target (40 systems, <=5 calls per rollout). **[INFER]** So the *training* pipeline reproduces completely for free. What you lose is the headline "cheap-to-expensive transfer" claim. The honest reduced claim you can still test is: *curriculum training on cheap RDKit property tasks improves performance on structure-based docking tasks that were never in the training reward* — Tier-1 to Tier-2 transfer, with Tier-2 held out. That is a real, falsifiable, small-scale version of the paper's thesis. Keep the *structure* (train on cheap, evaluate on an oracle never used as reward) and be explicit in any write-up that the top tier's fidelity is lower.

---

## 8. Open questions / things I could not verify

- **OpenEye**: the academic application form's required fields, approval turnaround, and the exact product list covered by each licence tier. All prices. Whether any route exists for an unaffiliated individual (the page's wording says no).
- **SQM2.20**: the Supplementary-Note-6 hardware and core count behind the "~20 minutes"; whether COSMO2 and PM6-D3H4X are reachable in *open* MOPAC (the openmopac pages list PM6/PM7, MOZYME and COSMO, but not the D3H4X correction or COSMO2); Cuby4's licence and current download location (**official site returned connection refused**).
- **xtb / GFN2-xTB per-structure timings**: **not documented** in the repo, the official docs, or the GFN2-xTB/GFN-FF abstracts. The ~1 s/complex figure above is third-party.
- **Uni-Dock absolute s/ligand per GPU** — only in `unidock/assets/1.1_docking_box.png` and `1.1_vs_bar.png`.
- **DiffDock-L seconds per complex** — no figure in the paper; do **not** assume parity with DiffDock's 10 s.
- **Minimum VRAM** for Vina-GPU, AutoDock-GPU, Uni-Dock and DiffDock inference — **none of the four documents a figure**. DiffDock's authors used 40–48 GB cards; whether 24 GB suffices at default settings is unverified.
- **smina's definitive licence** — SourceForge and bioconda say GPLv2; conda-forge and the GitHub fork say Apache-2.0; the tree ships both files.
- **PDBbind v2020** refined-set entry count and package byte sizes (login-gated in every archived capture).
- **`crossdocked_pocket10`** community subset: size and licence both undocumented.
- **ZINC20's 309 GiB total** is a sum over a 121-directory index crawl, **not a published figure**.
- **LIT-PCBA**: all official download URLs returned HTTP 404 on 2026-10-09.
- **RDKit descriptor throughput** is nowhere documented by the project; every millisecond figure in sections 3 and 7 was measured on this machine and will differ on yours.

---

*Written 2026-10-09. Primary sources are linked inline throughout. Sizes and package versions drift with releases; re-check before relying on any number here.*

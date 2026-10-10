# The Tier-1 seed-molecule pool: where to get it, and how σ must be computed

**Question (ticket 02).** What exactly should the Tier-1 seed-molecule pool be for the shrunk
reproduction of arXiv:2609.04735, and how do we obtain it? Covering: which ZINC distribution
gives 2D/SMILES-only data at a sane size, how many seeds are actually needed, whether to
substitute ChEMBL / GuacaMol / MOSES, **how σ (the property standard deviation that sets the
whole Tier-1 reward scale) is computed and over what subset**, and the practical mechanics on
Windows.

**Audience.** A beginner with no computational-chemistry background, one Windows 11 machine with
WSL2, a home internet connection, strictly free/open software.

**Conventions**
- **[FACT]** — stated in a primary source, URL given.
- **[MEASURED]** — measured by me during this research, on this machine, against the live
  servers on 2026-10-09. Method stated so it can be re-run.
- **[INFER]** — my inference, not in any source.
- **"not documented"** — I looked and the primary source is silent.

Research date: 2026-10-09. Every URL below was verified to return HTTP 200 on that date unless
noted otherwise.

---

## 0. The answer, up front

**Recommended seed pool: the ZINC20 2D "in-stock" set from `files.docking.org/2D/`, restricted to
MW 300–450, sampled down to one 1,000,000-molecule pool that serves as both the σ-estimation
pool and the seed pool.**

| | |
|---|---|
| Source | `https://files.docking.org/2D/<TT>/<TT><R><P>.smi`, purchasability `P ∈ {A,B}` |
| Download | **619 MB** (1,432 plain-text `.smi` files), or **493 MB** if you take reactivity class A only **[MEASURED]** |
| Pool after MW 300–450 filter | **~6.0 M molecules [MEASURED]**, of which you keep 1 M |
| Why not ZINC22 | the **2D/SMILES-only** ZINC22 collection is **1.31 TB gzipped [MEASURED]** — not just the 3D one |
| σ computed over | the *same* 1 M pool, with **RDKit's own** descriptor values, cached to one JSON file |
| Property table | one Parquet file, 1 M rows × ~101 float32 columns (~150–250 MB) |
| Native Windows? | **yes**, entirely — no WSL2 needed for seed prep |

Measured σ for the two properties ZINC publishes, so you can sanity-check your own pipeline
**[MEASURED]** (see §5.4 for method and §5.5 for why the MW window is there):

| Pool | mean MW | σ_MW | σ (ZINC's logp column) |
|---|---|---|---|
| ZINC20 in-stock, all 121 tranches | 354.9 | **88.4** | **1.58** |
| ZINC20 in-stock, MW 300–450 ← **recommended** | 362.2 | **38.1** | **1.35** |
| ZINC20 in-stock, MW 325–425 | 365.1 | 26.7 | 1.32 |
| ZINC22 (whole 2D collection, byte-weighted) **[INFER]** | ~360 | **~30–45** | **~1.42** |
| MOSES-like window (MW 250–350) | 311.3 | 27.6 | 1.22 |

The MW 300–450 restriction exists for one reason: **it is the only cheap way to make σ match the
pool the paper actually used.** ZINC22 is overwhelmingly concentrated in a narrow size band, so
its σ for size-like properties is ~2–3× *smaller* than the unfiltered ZINC20 in-stock set's.
Using the unfiltered set would silently make every Tier-1 objective reward ~3× flatter. §5 is
the load-bearing section of this document.

---

## 1. What the paper requires, and why the pool defines the reward

**[FACT]** from the paper (arXiv:2609.04735; `docs/reference/paper-2609.04735-fulltext.txt`
lines 242–246, 1801–1803, 1934, 1940, and digest Table A1):

- Tier-1 seeds are *"a molecule randomly sampled from ZINC, a large database of commercially
  available compounds (Tingle et al., 2023)"* — i.e. **ZINC-22**.
- *"the starting molecules are taken from the ZINC dataset and we precompute all 116 RDKit and
  OpenEye properties for each molecule"* (101 RDKit + 15 OpenEye, Table A4).
- **200,000** Tier-1 tasks were generated in total.
- Objective reward (Eq A2): `r_obj = sgn(Δy)·(1 − exp[−k(Δy/τ)²])`, `k = 10`, and for Tier-1
  **`τ = σ_y`**, which Table A1's caption defines as *"the standard deviation of the Tier-1
  target property computed over all molecules in ZINC."*
- Soft constraint (Eq A6): `c_i = exp[−½(d_i/(s·σ_i))²]`, `s = 0.1`, where (line 1934)
  *"σ_i is the estimated standard deviation of the property associated with constraint i,
  computed over all training molecules from ZINC, and d_i is the distance to the closest range
  boundary."*
- Batch = **1024 rollouts/step, 64 unique tasks/batch**, group size **16**, **500 steps** per run.

So σ appears in the reward in **two** places, and it is the *only* thing that converts a raw
property difference (in Daltons, in logP units, in ring counts) into a number between −1 and 1.
Change the pool, and you change every Tier-1 reward on the project.

**Two things the paper does not document [not documented]:**
- Which ZINC-22 subset/tranches the seeds were drawn from, or how many distinct seeds were used.
- Whether σ was computed over the 200,000 seeds, over a larger ZINC sample, or over all of
  ZINC-22. The wording *"over all molecules in ZINC"* / *"over all training molecules from
  ZINC"* is ambiguous between "the whole database" and "all the ZINC molecules we used".

---

## 2. ZINC-22: documented, and not downloadable

### 2.1 What ZINC-22 is

**[FACT]** Tingle et al., *J. Chem. Inf. Model.* 63:1166–1176 (2023), DOI
`10.1021/acs.jcim.2c01253`, free full text at
<https://pmc.ncbi.nlm.nih.gov/articles/PMC9976280/> (the ACS page at
<https://pubs.acs.org/doi/10.1021/acs.jcim.2c01253> returns **403** to non-browser clients):

- *"over 37 billion enumerated, searchable, commercially available compounds in 2D"*, *"over
  4.5 billion of which have been built"* in 3D.
- Source catalogs: Enamine REAL Database (5 B), Enamine REAL Space (29 B), WuXi (2.5 B),
  Mcule (128 M), **ZINC20 in-stock (4 M)**.
- *"about 2.5 billion molecules are up to HAC25 before stereochemical expansion, plus about
  21 billion between HAC26 and HAC30"* — **this single sentence is the most important fact in
  the whole document; see §5.5.**
- Tranches are slices of property space defined by **heavy atom count (HAC)** and **calculated
  logP**; the 2D tranche browser uses HAC horizontally and lipophilicity vertically. *"the
  database favors molecules with logP below four, but no logP limit is enforced."*
- 3D storage: *"nearly a petabyte"* for the db2 flexibase form — this is the ~1 PB the map
  rightly forbids.
- Data is *"freely available from our website at files.docking.org/zinc22/"*, plus AWS, OCI,
  Globus, CartBlanche.
- Some data is **password-protected** deliberately, *"to preserve patentability of chemical
  matter."*

### 2.2 The live ZINC-22 2D download tree — measured

**[MEASURED]** `https://files.docking.org/zinc22/` (HTTP 200) contains `2d/`, `2d-all/`,
`special/`, `subsets/`, `vendors_zincid_map/` and `zinc-22a/` … `zinc-22z/` (the lettered
"layers").

`2d/` and `2d-all/` return **HTTP 401**. The credentials are published on the parent index page
itself: *"the user id is the acronym for G protein coupled receptors, all small case, four
letters. The password is a widely used four letter abbreviation of crystal, all small case, four
letters."* → **`gpcr` / `xtal`**. This is the documented public access route, not a bypass; it
exists only to keep search engines from indexing the SMILES. **[MEASURED]** the `2d/` and
`2d-all/` listings for a given HAC are byte-for-byte identical; the difference between the two
trees is **not documented**.

**Structure [MEASURED]:** `2d/H{04..49}/H{hac}{P|M}{nnn}.smi.gz`, 46 HAC directories,
**2,607 files** total. The logP code is `P` + logP×100 in **0.1-wide bins from P000 to P490**,
then 1.0-wide bins `P500, P600, P700, P800, P900`; negatives are `M000`…`M500` in 1.0-wide bins.
This matches the wiki's *"calculated logP within 0.1 units"*
(<https://wiki.docking.org/index.php/Selecting_tranches_in_ZINC22>).

**File format [MEASURED]** (downloaded `H14/H14P300.smi.gz`, 1,300,402 bytes):
tab-separated `SMILES<TAB>ZINC_ID`, **no header**, 128,484 molecules ⇒ **~10.1 bytes per
molecule gzipped**. Approximately grouped by SMILES prefix (first lines all begin `Br…`, then
`C#`, `C(`, `C1`, `C=`, `CC`, …), which matters in §2.4.

### 2.3 Sizes — the decisive measurement

**[MEASURED]** total of every `.smi.gz` in `files.docking.org/zinc22/2d/`, by heavy-atom count:

| HAC | gz size | HAC | gz size | HAC | gz size |
|---|---|---|---|---|---|
| H04–H09 | <1 MB | H20 | 7.1 GB | H28 | **304 GB** |
| H10 | 1 MB | H21 | 11.3 GB | H29 | **376 GB** |
| H13 | 36 MB | H22 | 20.8 GB | H30–H33 | 2.3 / 2.1 / 1.9 / 1.7 GB |
| H14 | 97 MB | H23 | 36.1 GB | H34–H49 | 24–53 MB each |
| H16 | 515 MB | H24 | 61.0 GB | | |
| H17 | 1.25 GB | H25 | 108 GB | | |
| H18 | 2.28 GB | H26 | 168 GB | | |
| H19 | 3.93 GB | H27 | 234 GB | | |

**Total ZINC22 2D = 1,375,150 MB ≈ 1.31 TB gzipped.** Even a *single* logP bucket at a drug-like
size is impractical: `H22P160.smi.gz` is 654 MB, `H28M000.smi.gz` is 8.9 GB.

**Verdict: ZINC-22 is not practically downloadable on a home connection — and that conclusion is
*not* limited to the 3D collection the map already excluded. The SMILES-only 2D collection is
1.31 TB.** At a sustained 50 Mbit/s that is ~61 days of continuous download.

### 2.4 Why you cannot cheaply sample ZINC-22 either

Three routes were considered and all fail for this purpose:

1. **Download only low-HAC tranches.** H04–H17 totals ~2.2 GB **[MEASURED]**, which *is*
   feasible. But HAC ≤ 17 means roughly MW ≤ 240 — fragments, not leads. The resulting σ would be
   wrong in the opposite direction, and the seeds would not resemble the paper's.
2. **HTTP range requests on the big `.smi.gz` files.** gzip decodes from the start, so
   `curl -r 0-2000000` on a tranche *does* give you a usable prefix. **[MEASURED]** but the files
   are approximately sorted by SMILES prefix, so a prefix is a sample of molecules whose SMILES
   begin with `B`/`Br` — i.e. heavily enriched in bromine. **Prefix sampling of a ZINC22 tranche
   is biased and must not be used for σ.**
3. **CartBlanche.** <https://cartblanche22.docking.org/> returns 200 but serves a JavaScript
   application; its stated per-download cap (commonly quoted as 100,000 molecules) is **not
   documented** on any primary page I could reach, and the tranche browser needs a real browser.
   `wiki.docking.org` has no CartBlanche download-limit page.

Also checked and **not useful**: `files.docking.org/zinc22/zinc-22g/` (layer `g` = *"in-stock
informer set carried over from ZINC20"*,
<https://wiki.docking.org/index.php/ZINC22:Layers>) contains only **ZINC-ID lists with no
SMILES** **[MEASURED]** — `zinc-22g/H18/H18.txt` is 217,555 bare IDs.
`files.docking.org/zinc22/subsets/Ho2025/zinc22_fragments_canonical_map_with_zinc_ids.tar.gz`
is 815 MB and is a fragment canonical map, not a lead-like seed pool.

### 2.5 Dead or gated official links (recorded so nobody re-walks them)

| URL | Status [MEASURED] |
|---|---|
| `https://files22.docking.org/` | **does not resolve** — but the ZINC22 *Getting started* wiki page still names it |
| `https://wiki.docking.org/index.php/ZINC22:Overview` | **404** |
| `https://zinc.docking.org/`, `https://zinc20.docking.org/`, `.../tranches/home` | **302 → `/captcha`** for non-browser clients. The web UI needs a browser; `files.docking.org` does not |
| `https://pubs.acs.org/doi/10.1021/acs.jcim.2c01253` | **403** to curl; use the PMC copy |
| `https://ndownloader.figshare.com/files/<id>` | **403 to HEAD, 206 to ranged GET** — use `curl -L` with a GET, not `curl -I` |
| `https://files.docking.org/zinc22/` | intermittent — returned 000 once, 200 on retry. Retry, don't conclude it's gone |

Working and stable: `https://files.docking.org/`, `https://files.docking.org/2D/`,
`https://files2.docking.org/` (identical mirror of `files.docking.org` **[MEASURED]**,
same 2,486-byte index), `https://wiki.docking.org/index.php/ZINC22:Downloading`,
`https://wiki.docking.org/index.php/Selecting_tranches_in_ZINC22`,
`https://wiki.docking.org/index.php/ZINC22:Layers`.

---

## 3. ZINC20 2D: what to actually download

### 3.1 The tranche scheme, from the horse's mouth

**[FACT]** the header of <https://files.docking.org/2D/> states it in full:

> *"Physico-chemical property space is organized in 2D into 121 first-level tranches and two
> further dimensions for a four dimensional space: size, polarity, reactivity and purchasability.
> […] First letter is the molecular weight bin […] Second letter is the logP bin […] The third
> letter is reactivity, which is progressively inclusive as follows: A=anodyne. B=bother - often
> chromophores that could interfere with some assays. C=clean (but pains ok), E=mild reactivity
> ok, G=reactive ok, I = hot chemistry ok. The fourth letter is purchasability, which is
> progressively inclusive as follows: A and B = in stock, C = in stock via agent, D = make on
> demand, E = boutique (expensive), F=annotated (not for sale). […] It is refreshed every 60
> days."*

**[FACT]** the ZINC20 paper (Irwin et al., *JCIM* 60:6065–6073 (2020),
<https://pmc.ncbi.nlm.nih.gov/articles/PMC8284596/>) names the six purchasability levels as
**Premier, In-stock, Agent, On-demand, Boutique, Annotated** — mapping to letters A…F
**[INFER]**. It gives *"1.4 billion compounds, 1.3 billion of which are purchasable"*, a
rule-of-4 in-stock collection of **6,060,000**, and estimates *"about 14 million in-stock
compounds worldwide."* The paper does **not** state tranche bin boundaries [not documented].

**Bin boundaries, derived empirically [MEASURED]** by reading the `mwt` and `logp` columns of the
`.txt` files across all 121 tranches (121 ranged GETs, 250 KB each, 196,720 molecules parsed).
The letters are 11 × 11 = 121 and the observed edges are:

| letter | MW bin | logP bin |
|---|---|---|
| A | ≤ 200 | ≤ −1 |
| B | 200–250 | −1 – 0 |
| C | 250–300 | 0 – 1 |
| D | 300–325 | 1 – 2 |
| E | 325–350 | 2 – 2.5 |
| F | 350–375 | 2.5 – 3 |
| G | 375–400 | 3 – 3.5 |
| H | 400–425 | 3.5 – 4 |
| I | 425–450 | 4 – 4.5 |
| J | 450–500 | 4.5 – 5 |
| K | > 500 | > 5 |

(A handful of molecules sit slightly outside their nominal bin — e.g. one logP-bin-B molecule at
logp 3.65. Treat the binning as approximate and re-derive MW/logP with RDKit; see §5.2.)

### 3.2 Sizes — measured across all 121 tranches

**[MEASURED]** by listing all 121 tranche directories and summing the Apache-reported sizes
(8,550 entries, deduplicated; every directory covered):

| purchasability | `.smi` total | `.txt` total |
|---|---|---|
| A — Premier | 160.7 MB | 315.1 MB |
| **B — In-stock** | **458.6 MB** | 881.5 MB |
| C — Agent | 8.0 MB | 15.9 MB |
| D — On-demand | 51.5 GB | 94 GB |
| E — Boutique | 55.4 GB | 107 GB |
| F — Annotated | 544.1 MB | 920.3 MB |
| **A + B ("in stock")** | **619.2 MB, 1,432 files** | **1,196.6 MB** |
| everything | **107 GB** | ~200 GB |

Within A+B, by reactivity class **[MEASURED]**: A (anodyne) **492.9 MB**, B 21.7 MB, C 13.8 MB,
E 63.4 MB, G 24.7 MB, I 2.8 MB.

**Molecule count [INFER, from measurement]: ~11.2 M in the A+B set.** Derived by measuring
bytes-per-line per MW bin on 35 downloaded files (32.4 B/line at MW bin A rising to 102.9 at bin
K) and dividing the listed file sizes. This sits sensibly between the ZINC20 paper's 6.06 M
(rule-of-4 in-stock only) and its *"about 14 million in-stock compounds worldwide"* estimate, and
is consistent with the ZINC-22 paper counting *"ZINC20 in-stock (4 M)"* as one of its inputs
(ZINC-22 presumably took a built/deduplicated subset).

### 3.3 File formats — measured

```
# https://files.docking.org/2D/HC/HCAA.smi   (space-separated, HAS a header line)
smiles zinc_id
Cc1cn2cc(CNC(=O)[C@@H]3CCC(=O)N(CCN4CCOCC4)C3)nc2s1 19224302

# https://files.docking.org/2D/HC/HCAA.txt   (tab-separated, HAS a header line)
smiles  zinc_id  inchikey  mwt  logp  reactive  purchasable  tranche_name  features
Cc1cn2cc(...)nc2s1  19224302  UICHGWONXAOGBM-OAHLLOKOSA-N  405.524  0.891  0  50  HCAA
```

**[MEASURED]** `.smi` files are ordered by ascending `zinc_id`. **[MEASURED]** the A/B
purchasability files are **disjoint** — `ACAA.smi` (44,003 molecules) and `ACAB.smi` (43,607)
share zero ZINC IDs, so "progressively inclusive" in the site header does **not** mean the files
nest; each molecule appears in exactly one `(reactivity, purchasability)` file per tranche.

### 3.4 Download mechanics

There is no API and no job system — it is a plain Apache directory tree, so plain `curl`/`wget`
works. Mechanics **[MEASURED]**:

```bash
# 1. the 121 first-level tranches
curl -s https://files.docking.org/2D/ | grep -o 'href="[A-K][A-K]/"' | sed 's/href="//;s|/"||'

# 2. per tranche, the in-stock files (purchasability A or B, any reactivity)
curl -s https://files.docking.org/2D/HC/ | grep -oE 'HC[ABCEGI][AB]\.smi'

# 3. fetch (619 MB total). Keep concurrency modest — 10-12 parallel connections
#    produced intermittent truncated listings for me; 6 with --retry 3 was reliable.
curl -s --retry 3 -m 300 -O https://files.docking.org/2D/HC/HCAA.smi
```

Expect ~1,432 files. Not every `(reactivity, purchasability)` combination exists in every
tranche, so drive the download from the directory listings rather than from a generated
cartesian product. Listings are HTML; parse `href=` attributes.

**Refresh cadence [FACT]:** *"refreshed every 60 days (each file is timestamped)"*. Files I saw
were stamped 2025-01-28 to 2025-02-17. **Record the timestamps you downloaded**, because σ is a
function of the snapshot.

### 3.5 Licence and terms — and the consequence for the public repo

**[FACT]** verbatim from <https://files.docking.org/> and repeated on
<https://files.docking.org/2D/>:

> *"License: Whereas you are free to share the results of a ZINC search or a screen of molecules
> from ZINC, you may not redistribute major portions of ZINC without the express written
> permission of John Irwin: chemistry4biology at gmail dot com."*
>
> *"Caveat Emptor: We do not guarantee the quality of any molecule for any purpose and take no
> responsibility for errors arising from the use of this database."*

There is **no SPDX-style licence, no CC licence, and no formal terms-of-use document**
[not documented]. The ZINC20 and ZINC-22 papers both say only that ZINC is *"freely available to
everyone"* and state no licence.

**[INFER] Consequence for the map's open item "whether to publish the generated Tier-1 task
set":** a public repo containing 1 M ZINC SMILES is plausibly "a major portion" of the in-stock
subset and should not be published without asking Irwin. A public repo containing the
**generation script + the ZINC IDs + the σ cache + a small worked example (a few hundred tasks)**
is clearly "the results of a screen" and is safe. Recommend that split, and note it in the
deviation ledger. If full redistribution of the task set turns out to be a portfolio requirement,
rebuild the pool from **ChEMBL** instead (CC BY-SA 3.0, §6.1) and accept the σ consequences
documented there.

---

## 4. How many seeds does the shrunk run actually need?

**[FACT]** the paper: 200,000 Tier-1 tasks; 64 unique tasks per batch; 500 steps per run.
⇒ **32,000 unique tasks consumed per 500-step run**, so the 200,000-task pool is a **6.25×
surplus** for a single arm. Across a full curriculum sweep whose Tier-1 step counts are
500 + 400 + 250 + 100 + 0 = 1,250 Tier-1 steps, consumption is 1,250 × 64 = **80,000 tasks**, a
**2.5× surplus**.

**[INFER] For the shrunk reproduction.** Task consumption is `steps × (batch / group)`; it does
*not* depend on the model, so it is computable before ticket 01 reports. With the paper's 500
steps preserved (map constraint 6) and a plausible shrunk batch of 64 rollouts at group 8:

| | paper | shrunk (illustrative) |
|---|---|---|
| unique tasks / step | 64 | **8** |
| unique tasks / 500-step arm | 32,000 | **4,000** |
| across 1,250 Tier-1 steps of a sweep | 80,000 | **10,000** |
| × the paper's 2.5× surplus | 200,000 | **25,000** |

**So task diversity stops being the binding constraint at roughly 25,000–50,000 Tier-1 tasks.**
Each task consumes one seed; the paper does not say whether seeds are reused across tasks
[not documented], so assume one distinct seed per task.

**Recommendation: build one 1,000,000-molecule pool anyway.** The surplus is nearly free and buys
three things the 25,000 figure does not:
1. σ estimated to **<0.2 % relative error** even for heavy-tailed descriptors (§5.3) — this is
   the real reason for a big pool.
2. Headroom if ticket 01 lands on a bigger batch, or if arms get re-run.
3. Seeds can be drawn *without replacement* across every arm of every sweep, so no arm ever sees
   a seed another arm saw — which keeps "curriculum A beat curriculum B" from being confounded
   by task overlap.

Cost of 1 M **[INFER from the measured 5.21 ms/molecule for all 217 RDKit descriptors in
`docs/research/open-chem-oracle-stack.md` §3A]**: ~87 min single-core, ~15 min on 8 cores,
one time. A 101-descriptor subset is cheaper (~1–3 ms/molecule ⇒ 17–50 min single-core).

---

## 5. σ — the part that silently miscalibrates everything

### 5.1 What σ does to the reward, quantitatively

`r_obj = sgn(Δy)·(1 − exp[−10·(Δy/τ)²])` with `τ = f·σ_true`, where `f` is the factor by which
your pool's σ differs from the right one. Writing `x = Δy/σ_true`:

| x = Δy/σ_true | f = 0.33 | f = 0.5 | **f = 1** | f = 2 | f = 3 |
|---|---|---|---|---|---|
| 0.05 | 0.202 | 0.095 | **0.025** | 0.006 | 0.003 |
| 0.10 | 0.594 | 0.330 | **0.095** | 0.025 | 0.011 |
| 0.20 | 0.973 | 0.798 | **0.330** | 0.095 | 0.043 |
| 0.26 | 0.998 | 0.937 | **0.499** | 0.159 | 0.074 |
| 0.50 | 1.000 | 1.000 | **0.918** | 0.465 | 0.243 |
| 1.00 | 1.000 | 1.000 | **1.000** | 0.918 | 0.671 |

At the correct σ, the objective is half-saturated at `Δy = 0.263 σ` and 95 %-saturated at
`Δy = 0.547 σ`. The whole informative range of the reward is therefore **a window about half a
standard deviation wide**, and the window's position scales linearly with `f`:

| f | r_obj = 0.5 at | r_obj = 0.95 at | soft-constraint partial-credit window (c ≥ 0.1) |
|---|---|---|---|
| 0.33 | 0.088 σ | 0.182 σ | \|d\| ≤ 0.071 σ |
| 0.5 | 0.132 σ | 0.274 σ | \|d\| ≤ 0.107 σ |
| **1** | **0.263 σ** | **0.547 σ** | **\|d\| ≤ 0.215 σ** |
| 2 | 0.527 σ | 1.095 σ | \|d\| ≤ 0.429 σ |
| 3 | 0.790 σ | 1.642 σ | \|d\| ≤ 0.644 σ |

The soft constraint `c_i = exp[−½(d_i/(0.1 σ_i))²]` is even more sensitive, because `s = 0.1`
makes its scale a *tenth* of a standard deviation:

| d_i/σ_true | f = 0.33 | f = 0.5 | **f = 1** | f = 2 | f = 3 |
|---|---|---|---|---|---|
| 0.02 | 0.835 | 0.923 | **0.980** | 0.995 | 0.998 |
| 0.05 | 0.324 | 0.607 | **0.883** | 0.969 | 0.986 |
| 0.10 | 0.011 | 0.135 | **0.607** | 0.883 | 0.946 |
| 0.20 | 0.000 | 0.000 | **0.135** | 0.607 | 0.801 |
| 0.30 | 0.000 | 0.000 | **0.011** | 0.325 | 0.607 |
| 0.50 | 0.000 | 0.000 | **0.000** | 0.044 | 0.249 |

**Two concrete failure modes [INFER, from the tables]:**

- **σ too small (f < 1):** `r_obj` saturates at ~0.2 σ of improvement, so almost every successful
  rollout in a group scores ≈ 1.0. Combined with the known trap that **Dr. GRPO discards
  zero-advantage groups** (map, "Known traps"), this converts usable groups into wasted ones
  exactly when the policy starts succeeding. Meanwhile the soft constraint collapses into a hard
  one (partial credit vanishes beyond 0.07 σ), destroying the *"denser signal"* the paper
  explicitly introduced it for.
- **σ too large (f > 1):** a typical 0.2 σ improvement earns 0.095 instead of 0.330 — a **3.5×
  weaker** objective reward, so the weak 4 B policy sees a near-flat landscape and the format /
  tool-call penalties (−0.5 and −0.001) dominate. And violations up to ~0.6 σ still earn partial
  credit, so constraints become ignorable — reward hacking by another name.

Both directions are bad, and neither produces an error message. This is exactly the kind of
silent miscalibration the ticket flags.

### 5.2 How to compute σ — the recipe

1. **Build the pool first, then compute σ from it.** σ and the seeds must come from the same
   distribution, because that is what the paper does (*"over all training molecules from ZINC"*).
   Do not take σ from one source and seeds from another.
2. **Compute σ from RDKit's own descriptor values, not from ZINC's columns.** ZINC's `logp`
   column is not RDKit `MolLogP`, and its `mwt` is not necessarily RDKit `MolWt`. Since the
   *reward* is computed with RDKit, σ must be too, or `f ≠ 1` by construction. Use ZINC's `mwt`
   column only for the cheap MW pre-filter (§5.5) and for sanity-checking.
3. **One pass, one table.** Run `Descriptors.CalcMolDescriptors` (or your 101-property subset)
   over all 1 M pool molecules, write the Parquet table, then compute σ from the table columns.
   Never recompute σ on the fly.
4. **Use the population std (`ddof = 0`)** for consistency; at n = 10⁶ the difference from
   `ddof = 1` is 5·10⁻⁵ %. The paper says *"the estimated standard deviation"* and does not
   specify [not documented].
5. **Compute σ before the perturbation step.** Tier-1 step 4 perturbs constraints so the seed
   violates one; σ describes the *unperturbed* property distribution of real molecules.
6. **Guard against degenerate and non-finite descriptors.** Required, not optional:
   - Drop any property with **σ = 0** or σ below a threshold (e.g. σ < 10⁻⁸, or
     σ/|mean| < 10⁻⁶). `NumRadicalElectrons` is 0 for essentially every ZINC molecule, so
     `τ = σ_y = 0` ⇒ division by zero in Eq A2 and in Eq A6.
   - Drop any property that is non-finite anywhere. **[FACT]** `CalcMolDescriptors` takes
     `missingVal` for descriptors that cannot be computed
     (<https://rdkit.org/docs/source/rdkit.Chem.Descriptors.html>). `Ipc` and `Kappa3` are known
     to return extreme values on some molecules — a 2025 methods paper
     (<https://arxiv.org/pdf/2510.23428>) reports dropping exactly those two and discarding any
     descriptor returning NaN or Inf. **[FACT]** the RDKit docs also warn that `BertzCT`
     *"fails on a molecule with a 2nd-or-later single-atom fragment"* and that its aromatic-bond
     handling changed between releases, so **σ is RDKit-version-dependent** — pin the version.
   - Record the dropped list. The paper's task-construction step 5 already filters *"non-scalar"*
     properties and saturated ones; this extends that filter with "σ-degenerate", which the paper
     does not mention [not documented].
7. **Compute σ over the whole pool, not over the tasks you happened to generate.** Property
   distributions conditioned on "a task was successfully generated for this seed" are not the
   same as the pool's.

### 5.3 How large must the σ sample be? (And why 1 M is plenty)

For a sample of size n, the relative standard error of an estimated σ is
`SE(σ̂)/σ ≈ sqrt((κ−1)/(4n))`, where κ is the kurtosis (3 = normal, 10 = heavy-tailed, 50 = very
heavy-tailed, which some topological descriptors are) **[MEASURED by computation]**:

| n | κ = 3 | κ = 10 | κ = 50 |
|---|---|---|---|
| 1,000 | 2.24 % | 4.74 % | 11.07 % |
| 10,000 | 0.71 % | 1.50 % | 3.50 % |
| 100,000 | 0.22 % | 0.47 % | 1.11 % |
| 1,000,000 | 0.07 % | 0.15 % | 0.35 % |

**The headline: at n ≥ 10⁵, sampling error in σ is well under 1 % even for nasty descriptors —
i.e. `f ∈ [0.99, 1.01]`, which is invisible in the §5.1 tables.** Pool *size* is a solved
problem. Pool *choice* produces `f ≈ 2–3`, which is catastrophic. **Spend your effort on which
molecules, not on how many.**

Corollary: σ does **not** need all 11.2 M in-stock molecules, and certainly not all 37 billion
ZINC-22 molecules. The paper's phrase *"computed over all molecules in ZINC"* is, statistically,
indistinguishable from "computed over a million of them".

### 5.4 Measured σ, and how I got it

**[MEASURED]** Method: listed all 121 ZINC20 tranche directories; computed each tranche's in-stock
(purchasability A+B, all reactivity) molecule count from the listed `.smi` sizes divided by a
per-MW-bin bytes-per-line calibration measured on 35 downloaded files; then ranged-GET the first
250 KB of each `<TT>AA.txt` (121 requests, ~22 MB total) and parsed the `mwt` and `logp` columns —
**196,720 molecules across 98 of 121 tranches**. Pooled moments were weighted by each tranche's
population, which is essential: **the ZINC tranche grid *is* the MW × logP partition, so summing
tranches with equal weight, or sampling only some tranches, systematically distorts σ_MW and
σ_logP.** Within one tranche, MW and logP are nearly constant by construction, so within-file
prefix bias is harmless for these two columns (it would **not** be harmless for, say,
halogen counts — see §2.4).

| pool | population | mean MW | σ_MW | mean logp | σ_logp |
|---|---|---|---|---|---|
| ZINC20 in-stock, all tranches | ~9.1 M covered (of 11.2 M) | 354.86 | **88.39** | 2.88 | **1.58** |
| ZINC20 in-stock, MW 300–450 | ~6.04 M | 362.17 | **38.08** | 2.92 | **1.35** |
| ZINC20 in-stock, MW 325–425 | ~4.46 M | 365.12 | 26.70 | 2.88 | 1.32 |
| ZINC20 in-stock, MW 250–500 | ~8.03 M | 357.11 | 57.53 | 2.90 | 1.43 |
| ZINC20 in-stock, MW 250–350 | ~4.02 M | 311.25 | 27.58 | 2.47 | 1.22 |

Caveat: these are **ZINC's own `mwt`/`logp` columns**, not RDKit's `MolWt`/`MolLogP`. Treat them
as calibration targets accurate to ~10 %, not as the σ to put in your config. Your pipeline's
RDKit-computed σ_MW over the MW 300–450 pool should land near 38; if it lands near 88 you forgot
the filter, and if it lands near 27 your window is too tight.

### 5.5 The ZINC22 ↔ ZINC20 mismatch, and why the MW window fixes it

This is the single most consequential finding in this document.

**[FACT]** the ZINC-22 paper: *"about 2.5 billion molecules are up to HAC25 before stereochemical
expansion, plus about 21 billion between HAC26 and HAC30."* So **~89 % of ZINC-22 molecules sit
inside a five-heavy-atom window.**

**[INFER]** a distribution with 89 % of its mass in a 5-wide window has σ_HAC ≈ 2–3. Two
independent estimates:
- From the paper's two stated numbers with a crude two-component model: σ_HAC ≈ 3.1.
- **[MEASURED]** from my per-HAC byte totals (§2.3), assuming gzipped bytes per molecule grow
  linearly with HAC (calibrated at 10.1 B/molecule for H14): σ_HAC ≈ 2.2. The same model
  back-predicts ~74 billion molecules against the paper's stated 37 billion, so it overestimates
  high-HAC counts by roughly 2× — which biases σ_HAC *upward*, making 2.2 an upper bound under
  that model.

At roughly 13.3 Da per heavy atom for drug-like organics, **σ_HAC ≈ 2.2–3.1 ⇒ σ_MW ≈ 30–45 Da
for ZINC-22**, versus **σ_MW = 88.4 Da for the unfiltered ZINC20 in-stock set [MEASURED]**.

For logP the two pools agree. **[MEASURED]** weighting ZINC22's per-logP-bin byte sizes within a
fixed HAC (so bytes-per-molecule is ~constant and cancels): σ_logP = 1.38 (H20), 1.43 (H22),
1.44 (H25), 1.42 (H28), 1.44 pooled across all HAC — against ZINC20 in-stock's 1.58, and 1.35 in
the MW 300–450 window.

**Conclusion [INFER]:**

| property family | ZINC20 in-stock vs ZINC-22 | consequence |
|---|---|---|
| logP-like (polarity, TPSA-ish) | σ within ~10 % | substitution is safe, `f ≈ 1` |
| **size-like (MW, HAC, atom/ring/bond counts — the majority of the 101 RDKit descriptors)** | **σ ~2–3× larger** | `f ≈ 2–3`: objective reward ~3.5× flatter, constraints ~3× too loose |

Because size-like descriptors dominate the RDKit descriptor list, using the *unfiltered* ZINC20
in-stock pool would push most Tier-1 tasks into the `f = 2–3` column of §5.1 — the worst possible
direction for a small model that is already short of gradient signal.

**The fix, measured: restrict the pool to MW 300–450.** That gives σ_MW = 38.1 (inside the
ZINC-22 band of 30–45) and σ_logp = 1.35 (within 6 % of ZINC-22's 1.42), while still leaving
**~6.0 M molecules** — six times more than the 1 M you need. It costs one `if` statement, it is
checkable against the table in §5.4, and it also sits comfortably inside the paper's own Tier-2
constraint of MW < 600.

**A more faithful but more complex alternative [INFER]:** ZINC-22's HAC × logP tranche
*populations* are recoverable for free from the `files.docking.org/zinc22/2d/` directory listings
(2,607 file sizes, no molecules downloaded). You can therefore importance-reweight or resample the
ZINC20 in-stock pool to match ZINC-22's HAC × logP marginal exactly, using ZINC-22 as the target
distribution and ZINC20 as the sample source. This is strictly better statistically, but it needs
HAC per molecule (one RDKit call), a reweighted σ estimator, and weighted seed sampling. **Do the
MW window first; keep this in reserve** in case ticket 07 reports a suspiciously flat Tier-1
reward distribution.

**What must go in the deviation ledger regardless:** the paper's σ comes from ZINC-22; ours comes
from a MW-windowed ZINC20 in-stock snapshot; the two agree on logP to within ~6 % and on MW to
within the inferred band, but **we cannot verify the match for the other 99 descriptors**
[not documented — ZINC publishes only `mwt` and `logp`].

### 5.6 Caching σ

σ is a **build artifact with provenance**, not a runtime computation. Write one small JSON next to
the Parquet table and commit it to the repo (it is ~101 rows, and it contains no ZINC SMILES, so
§3.5 does not bite). The values in the skeleton below are **illustrative** — only the `MolWt` and
`MolLogP` σ figures are anchored to the measurements in §5.4, and the percentiles are invented:

```json
{
  "schema_version": 1,
  "pool": {
    "source": "files.docking.org/2D",
    "selection": "purchasability A+B, all reactivity, MW 300-450 (ZINC mwt column)",
    "tranche_files": 1432,
    "snapshot_timestamps": "2025-01-28 .. 2025-02-17",
    "downloaded_utc": "2026-10-09T00:00:00Z",
    "n_pool": 1000000,
    "sample_seed": 20261009,
    "smiles_sha256": "<hash of the sorted SMILES list>"
  },
  "rdkit_version": "2026.09.1",
  "ddof": 0,
  "properties": {
    "MolWt":   {"sigma": 38.1, "mean": 362.2, "n_finite": 1000000, "p1": 305.1, "p99": 446.3, "status": "ok"},
    "MolLogP": {"sigma": 1.35, "mean": 2.92,  "n_finite": 1000000, "p1": -0.4,  "p99": 6.1,   "status": "ok"},
    "NumRadicalElectrons": {"sigma": 0.0, "status": "dropped:degenerate"},
    "Ipc":     {"status": "dropped:nonfinite"}
  }
}
```

Rules:
- **The reward function reads σ only from this file.** No fallbacks, no recomputation, no
  defaults. If a property is missing from the file, the task generator must refuse to sample it.
- **`smiles_sha256` + `rdkit_version` + `sample_seed` make σ reproducible.** If any of the three
  changes, σ changes, and every reward number before and after is on a different scale — so a
  changed hash must invalidate every result, not silently coexist with it.
- **Store mean and the 1st/99th percentiles too.** They cost nothing and let you sanity-check
  constraint ranges and spot a descriptor whose σ is driven entirely by a handful of outliers
  (σ ≫ (p99 − p1)/4.6 is the warning sign).
- **Never regenerate σ between curriculum arms.** The map's known trap that *"relative BA
  improvement is normalised against the T1-only arm"* means arms must be numerically comparable;
  a mid-sweep σ change breaks that silently.

---

## 6. Should you substitute ChEMBL, GuacaMol, or MOSES instead?

### 6.1 ChEMBL `chemreps` — the licence-clean option

**[FACT]** <https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/>:
`chembl_37_chemreps.txt.gz` = **279 MB** (confirms the ticket's figure).
Release notes: **2,921,148 compounds**. Licence, from the dump's own `README`: *"The data content
in ChEMBL is licensed under a highly permissive Creative Commons license - specifically the 'CC
Attribution-ShareAlike 3.0 Unported license'"*, with a required attribution naming the URL and
release version. Format **[MEASURED]**: tab-separated, header
`chembl_id / canonical_smiles / standard_inchi / standard_inchi_key`.

**Drug-likeness profile and skew [MEASURED + INFER]:** the *second data row* of the file is a
40-residue peptide. ChEMBL is an assay-centric database: it contains biotherapeutics, peptides,
natural products, agrochemicals, dyes, and tool compounds alongside drug-like small molecules.
**[INFER]** its MW distribution is far broader and much heavier-tailed than any purchasable-space
pool, so σ_MW over raw ChEMBL would be *larger* than ZINC20 in-stock's 88 — i.e. the wrong
direction, *worse* than the unfiltered ZINC20 set, pushing `f` further above 1. Usable only with
aggressive filtering (MW window, element whitelist, remove peptides/salts/mixtures) — at which
point you have reimplemented most of GuacaMol's pipeline.

**When ChEMBL wins:** if §3.5's redistribution restriction becomes binding — i.e. the portfolio
repo must ship the actual seed molecules. CC BY-SA 3.0 permits that with attribution (and
obliges share-alike on the derived dataset).

### 6.2 GuacaMol — ChEMBL, cleaned

**[FACT]** <https://github.com/BenevolentAI/guacamol> (**MIT** code licence;
`guacamol/data/get_data.py`): built from **ChEMBL 24.1** `chemreps`. Filters: keep SMILES
5–200 characters; `split_charged_mol`; drop SMILES containing any of a long forbidden-element
substring list (Ag, Al, Fe, K, Ru, Xe, si, te, …); canonicalise + neutralise; remove anything with
ECFP4 Tanimoto > 0.323 to the 10-molecule holdout set; dedupe; shuffle with seed 1337. Split
**5 % valid / 15 % test / 80 % train**.

**Sizes [MEASURED]** via the figshare API and ranged GETs (<https://figshare.com/projects/GuacaMol/56639>):

| file | URL | bytes |
|---|---|---|
| `guacamol_v1_all.smiles` | `https://ndownloader.figshare.com/files/13612745` | 77,290,469 (**73.7 MB** — the ticket's "74 MB") |
| `guacamol_v1_train.smiles` | `.../13612760` | 61,841,218 (59.0 MB) |
| `guacamol_v1_test.smiles` | `.../13612757` | 11,590,126 (11.1 MB) |
| `guacamol_v1_valid.smiles` | `.../13612766` | 3,859,125 (3.7 MB) |

Counts, already measured in `docs/research/open-chem-oracle-stack.md` §3: **train 1,273,104 /
valid 79,568 / test 238,706 / all 1,591,378**.

**Skew [INFER]:** GuacaMol applies **no MW or logP filter**, so it keeps most of ChEMBL's breadth
(SMILES up to 200 chars ≈ MW up to ~1,000+). σ_MW will be substantially larger than ZINC20
in-stock's 88, so `f ≫ 1` — the wrong direction, and worse than the recommendation. Note also
**[FACT, from the map's "Known traps"]** that GuacaMol still imports `scipy.histogram`, removed
from modern SciPy — though you would only hit that if you imported the package rather than
downloading the SMILES files.

### 6.3 MOSES — the trap

**[FACT]** <https://github.com/molecularsets/moses> (**MIT**, © 2018 Insilico Medicine). Derived
from **ZINC Clean Leads** (4,591,276 molecules) with filters: **MW 250–350**, **≤ 7 rotatable
bonds**, **XlogP ≤ 3.5**, no charged atoms, elements restricted to C/N/S/O/F/Cl/Br/H, no rings
longer than 8 atoms, plus MCF and PAINS filters. Final: **1,936,962 molecules**; train ~1.6 M,
test ~176 k, scaffold-test ~176 k. `dataset_v1.csv` = **84,482,588 bytes (80.6 MB) [MEASURED]**
at `https://media.githubusercontent.com/media/molecularsets/moses/master/data/dataset_v1.csv`.

**MOSES is the worst choice of the five for this project, and the reason is exactly σ.** Its
construction *is* a property-range truncation: MW confined to a 100 Da window and logP capped.
**[MEASURED]** the equivalent MW 250–350 window of ZINC20 in-stock has σ_MW = 27.6 and
σ_logp = 1.22. So using MOSES σ gives `f ≈ 27.6/38 ≈ 0.7` for MW against the ZINC-22 target — and
far worse for properties MOSES truncates directly: rotatable bonds (≤ 7 vs ZINC22's unbounded),
charge (zero variance ⇒ σ = 0 ⇒ division by zero), and element composition. Several of the 101
RDKit descriptors would be degenerate or near-degenerate in MOSES, and the task generator would
then be unable to sample them at all — shrinking the effective property space the curriculum
explores, which is the paper's actual contribution.

**[INFER]** MOSES also redistributes ZINC-derived SMILES on GitHub, which sits awkwardly with
§3.5's "no major portions" clause; 1.9 M of 1.3 B is plausibly not a "major portion", but the
repo states no permission.

### 6.4 Verdict

| option | download | licence | σ fidelity to ZINC-22 | verdict |
|---|---|---|---|---|
| **ZINC20 2D in-stock, MW 300–450** | 619 MB | ZINC terms, no redistribution | **best measured match** (σ_MW 38 vs 30–45; σ_logP 1.35 vs 1.42) | **recommended** |
| ZINC20 2D in-stock, unfiltered | 619 MB | same | σ_MW 88 ⇒ `f ≈ 2–3` for size properties | avoid |
| ZINC-22 2D | **1.31 TB** | same | perfect by definition | **impossible on a home connection** |
| ChEMBL `chemreps` | 279 MB | **CC BY-SA 3.0** | poor (broader + heavier-tailed) unless heavily filtered | fallback only if the repo must ship the seeds |
| GuacaMol `all` | 74 MB | MIT code, data from ChEMBL 24.1 | poor (no MW/logP filter) | no |
| MOSES `dataset_v1.csv` | 81 MB | MIT | **bad** — truncation by construction, some σ = 0 | no |

---

## 7. Practical mechanics

### 7.1 Native Windows or WSL2?

**Native Windows, all of it. [MEASURED/FACT]**
- ZINC20 2D files are **plain uncompressed text** — no gzip step needed. `curl.exe` ships with
  Windows 10+; PowerShell `Invoke-WebRequest` also works.
- 1,432 files in one directory is fine on NTFS (contrast the map's CrossDocked 52-million-file
  warning).
- RDKit has official `win_amd64` wheels (`pip install rdkit`), per
  `docs/research/open-chem-oracle-stack.md` §3A.
- `pandas` + `pyarrow` are already installed on this machine **[MEASURED]**: pandas 3.0.3,
  pyarrow 25.0.1. **RDKit is not yet installed [MEASURED]** — `import rdkit` fails.

WSL2 remains needed only for the vLLM/GRPO training itself (map constraint 9), not for seed prep.
Build the pool on the Windows side and let WSL2 read it through `/mnt/d/…`, or keep the Parquet in
the WSL2 filesystem if the trainer reads it hot.

### 7.2 Storing the precomputed property table

**Recommendation: one Parquet file, `float32`, snappy or zstd compression.**

| | Parquet | SQLite |
|---|---|---|
| 1 M × 101 columns, raw float32 | 404 MB | 404 MB + index overhead |
| on disk, compressed | **~150–250 MB [INFER]** | ~400–600 MB (no column compression by default) |
| load whole table to RAM | one `pd.read_parquet` | row-by-row or a full `SELECT` |
| read a single column (σ pass) | **reads only that column** | reads every row |
| concurrency from the trainer | read-only, safe | needs care |

The access pattern is "load once into RAM, then sample random rows 25,000 times", not "look up
one molecule by key a billion times" — which is what SQLite would be for. At 1 M rows the whole
table fits in RAM comfortably, so Parquet's columnar reads plus a single in-memory NumPy array is
both simpler and faster. Keep SQLite in reserve only if the pool ever grows past ~20 M rows.

Suggested layout:

```
data/seeds/
  pool_zinc20_instock_mw300-450_1M.parquet   # zinc_id, smiles, <101 descriptor columns>
  pool_manifest.json                         # provenance: tranche files + timestamps + hashes
  sigma_cache.json                           # §5.6 — the only σ the reward may read
  dropped_properties.json                    # degenerate / non-finite, with reasons
  tasks_tier1_25k.jsonl                      # generated tasks (seed id + target + constraints)
```

Store `zinc_id` as a string (ZINC20 IDs are integers, ZINC-22's are strings like
`ZINCeA0000022lrf` **[MEASURED]** — don't let a schema guess make them unjoinable later). Commit
`sigma_cache.json`, `pool_manifest.json` and `dropped_properties.json`; do **not** commit the
Parquet (size, and §3.5).

### 7.3 Build order

1. Download the 1,432 in-stock `.smi` files (619 MB). Record timestamps.
2. Concatenate, **skip the `smiles zinc_id` header in every file**, dedupe on `zinc_id`.
3. Join the matching `.txt` files, or recompute MW with RDKit, and filter to **MW 300–450**
   (~6.0 M molecules).
4. Sample 1,000,000 with a fixed seed. Hash the sorted SMILES list.
5. Compute the 101 RDKit descriptors → Parquet (~15 min on 8 cores).
6. Compute σ, mean, p1, p99 per column from the Parquet; drop degenerate/non-finite; write
   `sigma_cache.json`.
7. Sanity-check: `σ(MolWt) ≈ 38`, `σ(MolLogP) ≈ 1.3–1.5`. If not, stop and find out why.
8. Generate 25,000–50,000 Tier-1 tasks from distinct seeds, using σ from the cache for the
   constraint ranges and later for the reward.

---

## 8. Open questions and things I could not verify

- **Which ZINC-22 subset the paper sampled**, and whether σ was computed over the whole 37-billion
  2D collection or over the 200,000 seeds — **not documented**. The whole of §5.5 is an attempt to
  bound the consequence rather than eliminate it.
- **Whether the paper's seeds are distinct** (200,000 tasks from 200,000 molecules, or fewer
  reused) — **not documented**.
- **`ddof` for σ**, and whether σ was computed before or after the constraint perturbation —
  **not documented** (immaterial at n = 10⁶ for the former; §5.2 item 5 takes the defensible
  reading of the latter).
- **The difference between ZINC-22's `2d/` and `2d-all/` trees** — **not documented**; the
  listings I compared are identical.
- **CartBlanche's download cap** — widely quoted as 100,000 molecules, but **not documented** on
  any primary page that resolves.
- **σ for the other 99 descriptors** in either pool. ZINC publishes only `mwt` and `logp`, so the
  MW/logP agreement in §5.5 is the only direct evidence the pools match. A cheap future check:
  compute the 101 descriptors on ~100 k molecules from a mid-size ZINC-22 tranche prefix and
  compare σ ratios against the ZINC20 pool — accepting the prefix bias of §2.4 as a known
  confound, it would still catch an order-of-magnitude mismatch.
- **Whether John Irwin would grant redistribution permission** for a 1 M-molecule public task set
  (§3.5). One email to `chemistry4biology@gmail.com` would settle the map's open item.

---

## 9. Primary sources

**ZINC**
- ZINC file archive, licence and caveat text — <https://files.docking.org/> (and the identical
  mirror <https://files2.docking.org/>)
- ZINC20 2D tranche archive + the full four-dimension tranche scheme —
  <https://files.docking.org/2D/>
- ZINC-22 file tree and the published `gpcr`/`xtal` note — <https://files.docking.org/zinc22/>
- ZINC-22 2D SMILES tranches — `https://files.docking.org/zinc22/2d/H{04..49}/`
- ZINC22 downloading (rsync/Globus/AWS) — <https://wiki.docking.org/index.php/ZINC22:Downloading>
- ZINC22 tranche/set selection — <https://wiki.docking.org/index.php/Selecting_tranches_in_ZINC22>
- ZINC22 layers a–z — <https://wiki.docking.org/index.php/ZINC22:Layers>
- ZINC22 getting started (names the now-dead `files22.docking.org`) —
  <https://wiki.docking.org/index.php/ZINC22:Getting_started>
- Tingle et al., *ZINC-22 — A Free Multi-Billion-Scale Database of Tangible Compounds for Ligand
  Discovery*, JCIM 63:1166 (2023), DOI 10.1021/acs.jcim.2c01253 —
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC9976280/>
- Irwin et al., *ZINC20 — A Free Ultralarge-Scale Chemical Database for Ligand Discovery*,
  JCIM 60:6065 (2020), DOI 10.1021/acs.jcim.0c00675 —
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC8284596/>
- CartBlanche — <https://cartblanche22.docking.org/>

**ChEMBL**
- Release directory, README (CC BY-SA 3.0), release notes, `chembl_37_chemreps.txt.gz` —
  <https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/>

**GuacaMol / MOSES**
- <https://github.com/BenevolentAI/guacamol> — `README.md`, `LICENSE` (MIT),
  `guacamol/data/get_data.py`
- <https://figshare.com/projects/GuacaMol/56639> and the figshare API
  (`https://api.figshare.com/v2/articles/<id>/files`)
- <https://github.com/molecularsets/moses> — `README.md`, `LICENSE` (MIT),
  `data/dataset_v1.csv`

**RDKit**
- <https://rdkit.org/docs/source/rdkit.Chem.Descriptors.html> — `CalcMolDescriptors`,
  `missingVal`, `silent`
- <https://rdkit.org/docs/source/rdkit.Chem.GraphDescriptors.html> — `Ipc`, `AvgIpc`, `BertzCT`
  and its documented failure mode
- <https://arxiv.org/pdf/2510.23428> — third-party report of dropping `Ipc` and `Kappa3` for
  extreme values (secondary, but the only published account of the failure I found)

**The paper**
- arXiv:2609.04735 — <https://arxiv.org/html/2609.04735v1>; locally
  `docs/reference/paper-2609.04735-fulltext.txt` (Eq A2/A4/A6, Table A1, Table A2, §A.1) and
  `docs/reference/paper-2609.04735-digest.md`

**Sibling research in this repo**
- `docs/research/open-chem-oracle-stack.md` — RDKit descriptor count (217 in 2026.09.1),
  measured per-molecule descriptor timings (`CalcMolDescriptors` = 5.21 ms), ChEMBL/GuacaMol
  licence and split sizes, Windows-native status of the whole Tier-1 stack

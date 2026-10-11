# The Tier-1 seed pool and its σ / correlation / quantile caches

**What this is.** The build record for the 1,000,000-molecule ZINC20 seed pool that defines the
Tier-1 environment's reward scale, and for the three statistics cached from it. Resolves
[#15](https://github.com/zhipengzhu1-dotcom/10-09-2026-Small-Molecule-Design-with-Synthetic-Task-Scaling/issues/15).
Everything here is **[MEASURED]** on this machine unless marked otherwise.

The pool matters more than its size suggests: the Tier-1 reward divides by property standard
deviations (τ = σ_y in Eq A2, σ_i in Eq A6), so **the seed pool sets the entire reward scale**.
A pool whose σ is 2–3× the paper's flattens the objective reward ~3.5× and makes constraints
ignorable, with no error message anywhere. See
[`zinc-seed-source.md`](zinc-seed-source.md) §5.1 for the quantitative failure modes.

**Scripts:** [`scripts/pool/`](../../scripts/pool/) — `properties.py` (the Table A4 → RDKit
mapping), `enumerate_zinc20.py`, `download_zinc20.py`, `build_pool.py`, `compute_caches.py`.
**Caches (committed):** [`caches/tier1-pool/`](../../caches/tier1-pool/).
**The pool itself is not committed** — ZINC's terms forbid redistributing major portions, so the
repo carries the script, the ZINC IDs and the caches, never the SMILES.

---

## 1. Provenance — the key everything hangs off

σ is a function of the snapshot, the RDKit version and the sample seed. Change any one and every
reward number before and after is on a different scale, so all three are recorded together and
the reward must read them **only** from the cache.

| | |
|---|---|
| Source | `https://files.docking.org/2D/`, purchasability **A + B** (premier + in-stock), all reactivity classes |
| Files | **1,432** `.txt` files over **121** tranches, **1,198.2 MB** |
| Snapshot timestamps | **2024-11-11 10:00 .. 2025-04-29 06:59** (the site refreshes every 60 days) |
| Downloaded | 2026-10-11 |
| In-stock molecules scanned | **11,327,276** |
| MW window | **300–450 Da**, on ZINC's own `mwt` column |
| Survivors in window | **7,397,090** (65.3%) |
| Pool size | **1,000,000**, drawn by seeded permutation |
| Sample seed | **20261011** |
| RDKit | **2026.09.1** (pinned; σ is version-dependent) |
| `ddof` | **0** (population std) |
| SMILES SHA-256 | `92c62a4eec4d04e902632f50ac0470ac143946d0ea13acba851970ca2c610a35` |

Two corrections to the estimates in [`zinc-seed-source.md`](zinc-seed-source.md):

- The in-stock total is **11,327,276**, confirming the ~11.2 M estimate derived there from
  byte-size calibration.
- Survivors in the MW window are **7,397,090**, not the estimated ~6.0 M — **23% more**. The
  estimate came from ranged-GET prefixes of 98 of 121 tranches; the direct count supersedes it.
  Either way the window leaves a 7.4× surplus over the 1 M pool.

### Download mechanics, and the 619 MB / 1,198 MB choice

The `.smi` files (619.2 MB) carry only `smiles` and `zinc_id`; the `.txt` files (1,198.2 MB)
add `mwt` and `logp`. **The `.txt` set was taken** so the MW window could be applied as a text
filter, avoiding an RDKit parse of all 11.3 M molecules — that pre-filter costs nothing in
fidelity (§2).

Concurrency: **6 parallel connections failed 39 of 1,432 files** (8 MB worth) even with 4 retries
and backoff; all 39 succeeded immediately at **2 connections**, which ran *faster* overall
(7.1 MB/s vs 2.3 MB/s). The research record's advice to keep concurrency modest holds, and **2 is
the better setting than 6** — a failure here is silent data loss, since a missing tranche file
removes a whole region of property space from σ.

### Tranche yield — the full download is nearly all useful

The tranche grid's **first letter is the size bin**, so the MW window cannot touch every tranche:

| | |
|---|---|
| Tranches contributing survivors | **81 / 121** |
| Tranches contributing none | **40** (all of `A*`, most of `B*`/`C*`, all of `J*`/`K*`) |
| Bytes in zero-yield tranches | **164 MB of 1,197 MB (13.7%)** |

So pre-selecting tranches to cut the download saves only 13.7% — the dead tranches are the small
ones. **Download everything; filter per molecule.** And filtering *by tranche* would be wrong
regardless: the grid is binned on **heavy-atom count**, not MW, so MW spills across bins — `B*`,
`C*` and `J*` each yield a trickle of in-window molecules (16, 90 and 60 respectively) that a
tranche-level cut would discard.

---

## 2. ZINC's `mwt` / `logp` columns *are* RDKit's — the pre-filter is free

[`zinc-seed-source.md`](zinc-seed-source.md) §5.2 warns that *"ZINC's `logp` column is not RDKit
`MolLogP`, and its `mwt` is not necessarily RDKit `MolWt`"*, and treats the measured σ_MW = 38.1
as *"a calibration target accurate to ~10%, not the σ to put in your config."*

**Measured, and the caution can be retired.** Over **1,504 molecules sampled from 40 tranche
files**:

| comparison | mean Δ | max \|Δ\| | fraction \|Δ\| > 0.01 |
|---|---|---|---|
| `Descriptors.MolWt` − ZINC `mwt` | **+0.00000** | **0.0000** | **0.0000** |
| `Crippen.MolLogP` − ZINC `logp` | −0.00003 | 0.0005 | 0.0000 |

`mwt` is bit-exact RDKit `MolWt`; `logp` agrees with `MolLogP` to within the column's own
3-decimal rounding. Filtering on ZINC's column and filtering on RDKit's **select the same
molecules: 0 of 1,504 disagreements** at the window edges.

Consequence: the cheap text pre-filter is not an approximation, and the σ_MW = 38.1 figure is a
genuine RDKit-scale target rather than a ~10% one. Every property that reaches the reward is
still computed from RDKit, per the recipe.

---

## 3. The Table A4 → RDKit mapping

Table A4 names its 116 properties by the **identifier shown in the prompt** and never states
which RDKit call produces each one, so the mapping had to be built:
[`scripts/pool/properties.py`](../../scripts/pool/properties.py).

It reproduces Table A4's structure exactly, which is the main evidence that the inference is
right:

| | mapping | Table A4 |
|---|---|---|
| numeric properties | **100** | 100 (101 − `scaffold`) |
| `scaffold` (string) | 1 | 1 |
| integer (hard, Eq A5) | **75** | **75** |
| continuous (soft, Eq A6) | **25** | **25** |
| Size / physico. | 12 | 12 |
| H-bond / charge | 13 | 13 |
| Bond / stereo | 9 + `scaffold` | 10 |
| Atom counts | 11 | 11 |
| Ring counts | 13 | 13 |
| Topological | 12 | 12 |
| Functional grps. | 30 | 30 |

Three mappings are **[INFER]**, not mechanical, and are the places to look first if Tier-1
behaves oddly:

- **`num_leadopt_disallowed_atoms`** — the paper never defines the disallowed element set
  [not documented]. Taken as "any element outside the ten the Atom-counts group enumerates
  individually" (C, H, N, O, S, F, Cl, Br, P, I), the reading that makes the group
  self-consistent.
- **`atom_count_H`** — implicit + explicit, per Table A4's own parenthetical.
- **`num_tautomers`** — `rdMolStandardize.TautomerEnumerator` with the enumerator capped at
  **1,000** tautomers. The cap censors the value, so its saturation rate is reported in §5.
- **`scaffold`** — largest BRICS fragment with dummy atoms stripped, per
  [#7](https://github.com/zhipengzhu1-dotcom/10-09-2026-Small-Molecule-Design-with-Synthetic-Task-Scaling/issues/7).
  Verified to return `Cc1cn2ccnc2s1` for the research record's sample molecule. Not part of the
  numeric table, so it carries no σ.

One of #3's predicted drops does not apply: **`Ipc` is not among the 101**. It appears in RDKit's
full `CalcMolDescriptors` set (217 descriptors), which is where the prediction came from, but
Table A4 does not list it. `Kappa3` *is* listed, and its behaviour is measured in §5.

---

## 4. Pool construction

Two resumable stages, `build_pool.py filter` then `build_pool.py sample`:

1. **filter** — stream all 1,432 `.txt` files, keep rows with `300 ≤ mwt ≤ 450`, consolidate to
   one 568 MB TSV. 11,327,276 scanned → 7,397,090 kept in **6 s**. Zero unparseable lines.
2. **sample** — draw a seeded permutation of the 7,397,090 survivors, walk it in order,
   RDKit-canonicalise, keep the first 1,000,000 that parse. **12.8 s.**

Walking a permutation rather than drawing a fixed 1 M is deliberate: a parse failure consumes a
draw and the walk continues, so the pool is **always exactly 1 M** instead of silently shrinking.
In the event the top-up never fired:

| | |
|---|---|
| Draws consumed for 1,000,000 molecules | **1,000,000** |
| RDKit parse failures | **0** |
| Duplicate ZINC IDs | **0** |
| Duplicate canonical SMILES | **25** |

**The 25 duplicates are a real finding.** ZINC holds distinct IDs that collapse to the same
canonical SMILES once RDKit normalises them. At 25 per million it changes nothing numerically,
but #7's generator assumes one distinct seed per task, so the task generator should deduplicate
on canonical SMILES rather than on `zinc_id` — the ID is not a unique key for a structure.

---

## 5. The pass, and what it cost

| | |
|---|---|
| Molecules | 1,000,000 |
| Numeric properties | 100 |
| Wall clock | **420 s (7 min)** on **22 worker processes** |
| Effective rate | ~2,380 molecules/s |
| Single-core cost | **~9.2 ms/molecule** for all 100 |
| RDKit failures | **0** |
| Parquet output | **86.9 MB** (float32, zstd) |

The Parquet file came in at **86.9 MB against the ticket's predicted 150–250 MB**, because zstd
compresses 75 small-range integer columns extremely well.

**`num_tautomers` is the pathologically slow property**, at **2.90 ms/molecule single-core —
roughly a third of the entire pass** and 4× the next worst. The next three are `qed_alerts`
(0.72), `qed` (0.70) and `num_brics_bonds` (0.24); every other property is under 0.18 ms. If this
pass ever needs to be cheaper, `num_tautomers` is the only thing worth touching.

Nothing failed outright, so there is no property RDKit cannot compute on ZINC in-stock molecules.
Two came close — see the drops below.

---

## 6. The drops: 3 of 100, and not the ones predicted

**97 of 100 properties are usable.** The drops:

| property | status | why |
|---|---|---|
| `max_partial_charge` | `dropped:nonfinite` | **162** of 1,000,000 molecules (0.016%) return non-finite Gasteiger charges |
| `min_partial_charge` | `dropped:nonfinite` | the same 162 molecules |
| `num_fragments` | `dropped:degenerate` | **exactly 1.0 for all million** — σ = 0, so τ = 0 divides by zero |

Three predictions from #3 and #7 did **not** hold:

- **`Ipc` is not among the 101.** It belongs to RDKit's full 217-descriptor set, which is where
  the prediction originated; Table A4 does not list it. Nothing to drop.
- **`Kappa3` is finite on all 1,000,000 molecules** (σ = 1.10, max 29.8). It was predicted to be
  dropped as non-finite. It is fine here.
- **`num_radical_electrons` is not σ-degenerate.** It was the named example of the degenerate
  drop, but ZINC in-stock does contain radicals (max 5), giving **σ = 0.0157** — non-zero, so the
  automatic rule keeps it. That is arguably worse than dropping it: a σ of 0.016 as the divisor
  in Eq A2 means a single radical electron scores a fully saturated reward. **The degenerate rule
  should be a floor on σ, not a test for exactly zero.** `num_fragments` was caught only because
  it is *perfectly* constant.

The non-finite rule as written ("drop any property non-finite anywhere") is harsh — 162 molecules
in a million cost two properties. Both are recorded with counts rather than silently removed, so
#7 could instead drop the 162 molecules and keep the properties. **Recommendation: keep the
rule.** These two have σ of 0.068 and 0.071, small relative to a single-atom edit, so they were
weak objectives regardless.

---

## 7. σ_MW and σ_logp reproduce

The calibration targets from [`zinc-seed-source.md`](zinc-seed-source.md) §5.4 — measured there
on ZINC's own columns over a 196,720-molecule prefix sample — against this pool's RDKit values
over all 1,000,000:

| | predicted | **measured** | Δ |
|---|---|---|---|
| σ_MW | 38.1 | **39.41** | +3.4% |
| mean MW | 362.2 | **363.55** | +0.4% |
| σ_logp | 1.35 | **1.29** | −4.2% |
| mean logp | 2.92 | **2.93** | +0.2% |

**Both reproduce.** σ_MW = 39.4 sits inside the inferred ZINC-22 band of 30–45 Da, so `f ≈ 1` and
the reward scale is calibrated. #7's perturbation calibration (δ ∼ U[0.05σ, 0.2σ], the 0.26σ
margin) rests on σ figures that have now held to within 4%, and needs no rechecking.

---

## 8. The number #7 is waiting on — and why the gate is not the real problem

#7 gated the **objective** pool at **σ_y ≥ 2.5 for integer properties**, because `r_obj`
saturates to 1.0000 on a single edit when σ is small, and left 2.5 provisional pending this
measurement.

**Raw survivor counts among the 75 integer properties:**

| gate | survivors |
|---|---|
| σ ≥ 1.8 | **8** |
| **σ ≥ 2.5** | **7** |
| σ ≥ 3.2 | **5** |

The seven at σ ≥ 2.5 are `num_stereoisomers`, `num_valence_electrons`, `num_tautomers`,
`atom_count_H`, `num_bonds`, `atom_count_C`, `heavy_atom_count`.

**But the raw count overstates the pool, for two reasons the cache exposes.**

**(a) Two of the seven have σ driven entirely by outliers.** Comparing σ against the robust
spread `(p99 − p1)/4.6` (the two are equal for a normal distribution) flags **8 of the 75 integer
properties**, including two gate survivors:

| property | σ | robust spread | mean | p99 | max |
|---|---|---|---|---|---|
| `num_stereoisomers` | **1048.58** | 0.65 | 2.15 | 4 | **1,048,576** |
| `num_tautomers` | **11.90** | 9.13 | 5.41 | 43 | 1,000 (the cap) |

`num_stereoisomers` is the extreme case: σ is 1,600× its robust spread because one molecule has
2²⁰ stereoisomers. A reward scaled by σ = 1048 is flat everywhere — the opposite of the
saturation the gate exists to prevent, and it *passes* the gate. `num_tautomers` is censored by
the enumerator cap (1 molecule at 1,000), so its σ is partly an artifact of a tuning constant.

**(b) The remainder are collinear with each other.** Spearman among the gate survivors:
`heavy_atom_count` ↔ `num_bonds` = **0.977** and `heavy_atom_count` ↔ `num_valence_electrons` =
**0.958**, both above #7's own 0.95 threshold. They are three names for molecular size.

Applying the outlier filter, then collapsing clusters above 0.95:

| gate | raw | after outlier filter | **after collinearity collapse** |
|---|---|---|---|
| σ ≥ 1.8 | 8 | 7 | **6** |
| **σ ≥ 2.5** | 7 | 6 | **5** |
| σ ≥ 3.2 | 5 | 4 | **4** |

**So the gate's exact value barely matters: 1.8, 2.5 and 3.2 leave 6, 5 and 4 effectively
independent integer objectives.** Moving it buys at most two, and every survivor is a size-like
count (`num_valence_electrons`, `atom_count_H`, `num_bonds`, `atom_count_C`, plus `num_tautomers`
if the cap is accepted). **Recommendation: keep the gate at 2.5** — it is not the binding
constraint, and lowering it to 1.8 admits only `num_rotatable_bonds`.

**The real finding is that the integer objective pool is tiny and one-dimensional, while the
continuous pool is healthy.** 23 of 25 continuous properties survive, spanning genuinely
different chemistry:

`bertz_ct` 202, `molecular_weight` 39.4, `tpsa` 22.8, `labute_asa` 17.2, `molar_refractivity`
12.5, `kappa1` 2.18, `chi0` 2.13, `max_estate_index` 1.80, `logp` 1.29, `kappa3` 1.10,
`hall_kier_alpha` 0.76, `balaban_j` 0.32, `fraction_csp3` 0.19, `qed` 0.16, and nine more.

**Consequence for #7: the objective pool is really ~23 continuous properties plus ~5 size-like
integers, not a balanced draw over 75 + 25.** A generator that samples objectives uniformly over
the gated integer pool will produce tasks that are nearly all "change the molecule's size", and
the curriculum would then measure size-editing rather than property optimisation. This is a new
question the measurement opened, not one #7 settled.

### The `fr_*` estimate, checked

#7 *estimated* that rare functional-group counts sit at σ ≈ 0.1–0.5, and used that to exclude
them from the objective pool. Measured over all 30:

| | σ |
|---|---|
| minimum (`fr_aldehyde`) | **0.039** |
| median | **0.316** |
| maximum (`fr_NH0`) | **1.513** |
| below 0.5 | **18 of 30** |

**The estimate is right about the median and too low at the top.** The exclusion still holds —
every `fr_*` is far below 2.5, so none would pass the gate anyway — but `fr_NH0` (1.51),
`fr_Ar_N` (1.47), `fr_halogen` (0.97) and `fr_amide` (0.87) are an order of magnitude above the
estimated floor and carry real partial-credit structure as *constraints*.

### Collinearity, for the constraint pool

**18 pairs exceed 0.95** among the 97 usable properties, which is what #7's constraint sampler
must reject against. The full matrix is cached
([`spearman_cache.npz`](../../caches/tier1-pool/spearman_cache.npz), 97×97 float32) with the
offending pairs enumerated in
[`spearman_cache.json`](../../caches/tier1-pool/spearman_cache.json).

---

## 9. The caches

All artifacts carry the same provenance triple (SMILES SHA-256 + RDKit version + sample seed).
**The reward reads σ only from these files** — no fallbacks, no recomputation. If any of the three
changes, σ changes and every reward number before and after is on a different scale, so a changed
hash must invalidate every result rather than silently coexist with it.

| file | contents |
|---|---|
| `sigma_cache.json` | per-property σ (ddof=0), mean, min, max, p1/p5/p95/p99, n_finite, n_nonfinite, status |
| `quantile_cache.json` | the 1st/5th/95th/99th percentiles alone, for #7's saturation test |
| `spearman_cache.npz` | the 97×97 Spearman matrix (float32) + property names |
| `spearman_cache.json` | the 18 pairs above 0.95 |
| `objective_pool_gates.json` | survivor lists at σ ≥ 1.8 / 2.5 / 3.2 |
| `pool_zinc_ids.txt.gz` | the 1,000,000 ZINC IDs (4.5 MB) — shippable; the SMILES are not |
| `property_timing_ms.json` | per-property single-core cost |

**Never regenerate these between curriculum arms.** Relative BA improvement is normalised against
the T1-only arm, so arms must stay numerically comparable; a mid-sweep σ change breaks that
silently. #7's decision to freeze σ and `y_ref` into each task record makes this structurally
impossible rather than merely forbidden, which is the stronger guarantee.

---

## 10. What this hands the next ticket

- **#7's provisional gate is settled: keep σ_y ≥ 2.5.** The evidence at 1.8 and 3.2 says the
  threshold is not load-bearing.
- **A new question for the Tier-1 prompt/surface work:** how objectives are sampled, given that
  the gated integer pool is ~5 mutually-related size counts against 23 varied continuous ones.
- **Two mechanical fixes to the recipe:** make the degenerate-σ rule a floor rather than an
  equality test (`num_radical_electrons` at σ = 0.0157 slips through), and add the robust-spread
  outlier test to the objective gate (`num_stereoisomers` at σ = 1048 passes the gate today).
- **Deduplicate seeds on canonical SMILES, not `zinc_id`** — 25 pairs of distinct IDs collapse.
- **Download with 2 connections, not 6.** 39 of 1,432 files failed at 6 even with retries.

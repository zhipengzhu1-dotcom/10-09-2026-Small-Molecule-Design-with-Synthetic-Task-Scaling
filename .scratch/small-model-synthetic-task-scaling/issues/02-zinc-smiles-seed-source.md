# 02 — Where to get ZINC seed molecules at a manageable size

Type: research
Status: resolved
Blocked by: —
Map: [Synthetic Task Scaling at <8B](../map.md)

## Question

What exactly should the Tier-1 seed-molecule pool be, and how do we obtain it?

The paper samples Tier-1 seeds from **ZINC-22** (Tingle et al. 2023) and precomputes all 116
properties per molecule. Tier-1 needs **SMILES only** — no 3D conformers — so the ~1 PB ZINC22
3D collection is irrelevant and must not be downloaded.

Resolve, against primary sources:

- Which ZINC distribution gives **2D/SMILES-only** tranches at a sane size, with real download
  URLs, the tranche-selection scheme (logP × MW buckets), licence, and terms of use. Cover
  ZINC20 and ZINC22; say plainly which is practically downloadable on a home connection.
- How many seed molecules the shrunk reproduction actually needs. The paper generated 200,000
  tasks; under this map's ~1% scaling principle, how large must the pool be to keep task
  diversity from being the binding constraint rather than compute?
- Whether to sample ZINC at all, or substitute **ChEMBL `chemreps`** (279 MB) or the
  **GuacaMol / MOSES** standard splits (74 / 80 MB). For each: licence, drug-likeness profile,
  and how the substitution would skew the property distributions the reward depends on.
- **Critical for the reward function:** the paper's Tier-1 objective normalisation is
  `τ = σ_y`, the standard deviation of the target property **computed over all ZINC molecules**,
  and the soft-constraint scale uses `σ_i` from the same pool. So the chosen pool *defines the
  reward scale*. Document how σ will be computed and over what subset, and how sensitive the
  reward is to getting this pool wrong.
- Practical: download size, whether it works on native Windows, and how to store the
  precomputed property table (parquet? sqlite?) for 101 RDKit properties over the pool.

Write findings to `.scratch/research/zinc-seed-source.md`. Separate documented facts from
inference; say "not documented" rather than guessing.

## Answer

<!-- append on resolution -->

## Answer

Resolved 2026-10-09. Full findings: [`zinc-seed-source.md`](../../research/zinc-seed-source.md)
(856 lines).

**Seed pool: ZINC20 2D "in-stock" from `files.docking.org/2D/` (purchasability letters A+B),
filtered to MW 300–450, sampled to a single 1,000,000-molecule pool that serves as both the σ
pool and the seed pool.**

### ZINC-22 is not downloadable at all, in any form

The map's "avoid ZINC22 3D (~1 PB)" note was correct but incomplete. The **2D/SMILES-only**
collection was measured at **1.31 TB gzipped** across 2,607 files (H28 alone is 304 GB) — about
61 days at 50 Mbit/s. So the paper's stated seed source is out of reach regardless of dimension,
and substituting ZINC20 is a mandatory deviation, not a convenience.
(The `2d/` tree returns HTTP 401; the credentials are published on its own parent index page.)

**ZINC20 2D in-stock is 619 MB** — 1,432 plain-text `.smi` files over 121 tranches, ~11.2 M
molecules; ~6.0 M survive the MW filter, of which 1 M is kept. Tranche scheme verified:
ZINC20 = MW letter × logP letter (11×11) × reactivity × purchasability, with empirically derived
bin edges (MW 200/250/300/325/350/375/400/425/450/500; logP −1/0/1/2/2.5/3/3.5/4/4.5/5).

### σ: pool size is a non-problem, pool *choice* is the problem

σ appears twice in the reward — τ = σ_y in Eq A2 and σ_i in Eq A6 with s = 0.1 — so the pool
sets the entire Tier-1 reward scale.

- At n ≥ 10⁵ the relative standard error of σ̂ is **< 1.1%** even at kurtosis 50. Pool size is
  therefore irrelevant to reward calibration.
- **Pool mismatch, by contrast, is catastrophic.** ZINC-22's size distribution is far narrower
  than ZINC20 in-stock's: the ZINC-22 paper puts ~21 of ~23.5 billion molecules in HAC 26–30,
  implying **σ_MW ≈ 30–45 Da**, against a measured **σ_MW = 88.4** for unfiltered ZINC20
  in-stock — a factor of 2–3 on every size-like descriptor. At f = 2, a 0.2σ improvement earns
  **0.095 instead of 0.330** (a 3.5× flatter objective), and the soft-constraint partial-credit
  window widens from 0.215σ to 0.429σ, i.e. **constraints become effectively ignorable**.
- **The fix is one filter.** Restricting to MW 300–450 yields **σ_MW = 38.1** and
  **σ_logp = 1.35**, both inside the ZINC-22 band, while retaining 6.0 M molecules.

**σ recipe:** compute from RDKit's own values (not ZINC's `mwt`/`logp` columns), one pass over
the same 1 M pool, `ddof=0`, **before** constraint perturbation. Drop σ ≈ 0 descriptors
(`NumRadicalElectrons`) and non-finite ones (`Ipc`, `Kappa3`). Cache to one `sigma_cache.json`
keyed by SMILES-hash + RDKit version + sample seed; the reward reads it exclusively and it must
**never be regenerated mid-sweep** — doing so silently rescales every reward.

### Remaining answers

- **Task count:** tasks = steps × (batch / group). Paper: 500 × 64 = 32,000 per arm drawn from
  200,000 (6.25× surplus). Shrunk at batch 64 / group 8: ~10,000 across a full sweep, so
  **25,000–50,000 tasks** is where diversity stops binding. Build the 1 M pool regardless — it
  is what buys the σ precision.
- **Substitutes rejected.** MOSES is the worst option (MW 250–350, logP ≤ 3.5 by construction →
  truncated σ, some descriptors degenerate). GuacaMol/ChEMBL skew σ *upward* (peptides, no MW
  filter). **ChEMBL (CC BY-SA 3.0, 279 MB) is the fallback only if the repo must ship actual
  seed structures.**
- **Licence — affects the public repo.** ZINC carries no SPDX/CC licence, only *"you may not
  redistribute major portions of ZINC without the express written permission of John Irwin."*
  So the repo ships **the script, the ZINC IDs, and the σ cache — not the SMILES.**
- **Storage:** native Windows throughout (plain text, RDKit has win_amd64 wheels). One
  **Parquet** file, float32, ~150–250 MB. Not SQLite — the access pattern is load-once-sample-rows.
- **Dead or gated links recorded** in the findings file: `files22.docking.org` does not resolve;
  the `ZINC22:Overview` wiki page 404s; `zinc.docking.org` and `zinc20.docking.org` 302 to a
  captcha for non-browser clients; the ACS DOI page 403s.

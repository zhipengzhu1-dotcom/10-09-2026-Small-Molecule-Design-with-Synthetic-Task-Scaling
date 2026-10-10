# Digest: arXiv:2609.04735v1 — Training LLMs for Small-Molecule Design with Synthetic Task Scaling

Hu, Chennakesavalu, Wang, Suriana, Vani, Shmilovich, Chuang, Grambow.
**Prescient Design, Genentech.** 4 Sep 2026. CC BY 4.0. cs.LG.
Correspondence: grambow.colin@gene.com

Full text saved locally: [`paper-2609.04735-fulltext.txt`](./paper-2609.04735-fulltext.txt) (3,179 lines).
Raw HTML: [`paper-2609.04735.html`](./paper-2609.04735.html).

**No code or data release.** The author-contributions note says the framework was "internal
prime-rl-based" and SQM was "deployed on internal hardware". Expect no artifacts.

---

## The claim

Chemistry oracles that matter (FEP, SQM) cost hours-to-days per evaluation, so they cannot sit
inside an online RL loop. The paper asks whether a model can learn molecular-design strategy
from **cheap synthetic tasks** and transfer it to an **expensive held-out oracle it never
trained on**. Answer: yes, and a curriculum (cheap first, then medium) beats both cheap-only
and medium-only training, and beats much larger frontier models.

## Three-tier oracle hierarchy

| Tier | Role | Oracle | Cost/eval | Count |
|---|---|---|---|---|
| Tier-1 | cheap training | RDKit + OpenEye descriptors | ms | 200,000 tasks |
| Tier-2 | medium training | POSIT docking → Chemgauss4 | "order of seconds" | 999 tasks |
| Eval | held-out, never trained on | POSIT docking → SQM2.20 | "tens of minutes" | 40 systems |

All three share one abstraction: **lead optimization** — improve a target property of a seed
molecule subject to constraints, iteratively, with tool access.

## Model and training

- Base: **Qwen3.6-35B-A3B** ("Qwen 3.6 (base)") — MoE, ~35B total / **~3B active per token**.
  Note: compute-wise already small; the barrier is weight memory, not FLOPs.
- **RLVR only.** No SFT, no distillation, no DPO (explicitly left to future work).
- Framework: **prime-rl**, asynchronous (separate inference and trainer workers).
- Advantage: **Dr. GRPO-style** — mean-centred within group, **no std normalisation** (Eq 6).
  **Groups with identical rewards are dropped** (zero advantage, no gradient signal).
- Loss: **IPO** = DPPO-Binary-TV + Kimi K2.5 regularisation (Eq 10). Token-level log importance
  ratio clipped to ±ρ_max, ρ_max = 10. Trust-region threshold ε_IPO. β = 1e-3.
- Hardware: **32 × B200, 4 nodes** (2 training + 2 inference).
- LoRA vs full fine-tune: **not stated** (almost certainly full FT at that scale).

### Table A2 — training hyperparameters (all runs)

| | |
|---|---|
| Loss | IPO (`ipo_loss_fn`) |
| Group size G | 16 |
| KL coefficient β | 1e-3 |
| Off-policy staleness | 2 steps (async) |
| Optimizer | AdamW, lr **1e-6**, betas (0.9, 0.999), wd 0.01 |
| Gradient clip max_norm | 0.1 |
| LR schedule | constant, no warmup, no decay |
| Batch | **1024 rollouts/step, 64 unique tasks/batch** |
| Max sequence | 16,384 tokens |
| Max completion | 14,000 tokens |
| Temperature | 1.0 |
| Steps | **500 for every run** |

Curriculum runs **hot-start from the relevant checkpoint, loading weights only; optimizer state
is reset.**

## Reward (fully specified — reimplementable)

```
R_total = w_obj·r_obj + w_constraint·r_constraint + n_tool·r_tool + r_format + r_invalid
```

- **Objective** (Eq A2): `r_obj = sgn(Δy)·(1 − exp[−k(Δy/τ)²])`, with signed improvement
  `Δy = ŷ − y_ref` (maximisation) or `y_ref − ŷ` (minimisation).
- **Constraint** (Eq A4): mean of per-constraint scores `c_i`.
  - Integer/boolean → **hard**: 1 or 0 (Eq A5).
  - Continuous (LogP, TPSA) → **soft** (Eq A6): 1 inside range, else
    `exp[−½(d_i / (s·σ_i))²]`, where `d_i` = distance to nearest range boundary and `σ_i` =
    property std over ZINC. Gives partial credit for marginal violations → denser signal.

### Table A1 — reward hyperparameters

| | Tier-1 | Tier-2 |
|---|---|---|
| Objective scale k | 10.0 | 10.0 |
| Objective normalisation τ | σ_y (property std over ZINC) | \|y_ref\| (seed score) |
| Soft-constraint scale s | 0.1 | 0.1 |
| w_obj | **0.5** | **0.75** |
| w_constraint | **0.5** | **0.25** |
| Tool-call penalty r_tool | −0.001 | −0.001 |
| Format penalty r_format | −0.5 | −0.5 |
| Invalid-molecule penalty r_invalid | −0.001 | −0.001 |

Reward-weight screen (App C.2): w_obj=0.75/w_c=0.25 was best for Tier-2; alternatives
(0.5/0.5, 0.25/0.75) gave worse downstream BA (none exceeded +2.5 kcal/mol).

### Tool-call penalty warmup — a scaling trap

Ramped linearly 0 → target over **1000 *group-scoring* steps**. Group-scoring steps per trainer
step = batch / group = 1024/16 = **64**, so 1000 group steps ≈ **16 trainer steps**. In mixed
curricula: 250 warmup steps for Tier-1, 750 for Tier-2, so full penalty bites at the same
trainer step for both. **"Without the warmup, the model would learn catastrophically
conservative tool call behavior."** Any rescaling of batch/group must rescale this.

## Task construction

### Tier-1 (6 steps, fully specified)
1. Sample min-or-max, and a target property from the **116** descriptors.
2. Sample a seed molecule from **ZINC** (ZINC-22, Tingle 2023). All 116 properties precomputed.
3. Build **2–4** constraints from the seed, **plus a BRICS scaffold constraint** (core substructure).
4. **Perturb a random subset of constraints so the seed violates at least one.**
5. Filter pathologies (property already saturated; non-scalar property).
6. One tool only: `calculate_multiple_properties(properties[], smiles[])`.
   Single wrapper tool deliberately, to avoid context bloat from many similar tools.

Total: **200,000** Tier-1 tasks.

### Tier-2 / eval — PLINDER filtering
- Seed ligand MW **200–600 Da**
- Exclude ions, cofactors, covalent binders, oligomers, crystallisation artifacts
- Crystal resolution **≤ 3 Å**
- Chemgauss4 **and** SQM computable for the seed
- Passes **all PoseBusters** checks (sanitisation, valences, kekulisation, bond lengths/angles,
  aromatic-ring planarity, no internal clashes)
- A valid **OpenEye design unit (.oedu)** can be generated ← *OpenEye-specific, drop when substituting*

**999 training tasks** (official PLINDER **train** split) / **40 evaluable** (official **test**
split). Split discipline matters — no leakage.

### Tier-2 fixed physicochemical constraints
MW < 600 · 12–50 heavy atoms · LogP < 4.0 · TPSA < 150 · 0–4 HBD · 0–4 aromatic rings ·
0–9 rotatable bonds · elements only C,H,N,O,P,S,F,Cl,Br,I · **retains the BRICS scaffold** of the seed.

### Tools by tier
| Tier | Tools |
|---|---|
| Tier-1 | `calculate_multiple_properties` |
| Tier-2 | `calculate_multiple_properties`, `score_chemgauss4` (POSIT dock → Chemgauss4) |
| Eval | `calculate_multiple_properties`, `score_sqm`, **`contains_scaffold`** |

`contains_scaffold` is **evaluation-only on purpose**: including it in training "hurts
performance because models traded objective improvement and the satisfaction of other
constraints for scaffold satisfaction, sometimes leading to mode collapse."

Scoring tools are **partial functions per target** — target-specific files pre-bound, model
passes only a SMILES.

## The 116 properties (Table A4): **101 RDKit + 15 OpenEye**

Groups: size/physicochemical (12) · H-bond & charge (13) · bond/stereo (10, incl. the BRICS
`scaffold` string) · atom counts (11) · ring counts (13) · topological (12) · functional groups
`fr_*` (30) · **OpenEye (15)**.

The 15 OpenEye ones: molecular complexity + components, aromatic atom/bond/ring counts,
ring-system count, `oe_is_macrocycle` (boolean), ring bond count, longest unbranched chain,
halide fraction, unspecified E/Z count, anionic carbon count, net charge at neutral pH.
**→ 87% of the property space is free; only these 15 are gated.**

## Prompts (given verbatim in the paper)

Shared **system prompt**: "helpful scientific assistant with expertise in molecular design,
computational biology, and chemistry"; requires a reasoning summary between
`<|reasoning_summary_start|>` / `<|reasoning_summary_end|>` and the final answer between
`<|answer_start|>` / `<|answer_end|>`, each appearing **exactly once**.

**Tier-1 user prompt**: 15-turn budget (a turn is a proposal OR a tool call); tool calls and
proposals must be in **separate messages**; answer tags contain only a molecule representation;
last message must include answer tags; lists available properties; then seed molecule, target
property, constraints, and a 6-step suggested workflow.

**Tier-2 user prompt**: 20-turn budget; **at most one tool call per message**; expensive scorer
capped at **5 calls, one molecule per call** (further calls refused); seed SMILES **plus an
atom-map-labelled copy** so the binding context can reference atom numbers; then the
**BINDING CONTEXT** block and the fixed constraints.

### Binding-context "textification" format (verbatim shape)
```
Key interactions the seed makes with the target:
- strong H-bond: GLN48 (ligand atom 22)
- H-bond (non-ideal) (water-mediated): HOH1 (ligand atom 22)
Steric clashes in the seed pose (liabilities to relieve, not preserve): LEU38
Unfilled polar sites near the ligand (room to add a complementary group):
- acceptor GLN48 (sidechain), ~3.4A from ligand atom 22
- acceptor ASN42 (sidechain), ~3.6A from ligand atom 12
Pocket residues lining the site (most ligand contact first): MET82, ASN42, LEU41, ...
```
Reimplementable from structures with free interaction-profiling tools — needs no OpenEye.

## Curricula (Table 1) — all runs total 500 steps

`T1(a)–T2(b)`: a steps Tier-1, then b steps **Tier-2 only**.
`T1(a)–Mix(b)`: a steps Tier-1, then b steps on a **25% : 75% Tier-1:Tier-2** batch mixture.
Arms: T1(500), T2(500), and a ∈ {250,300,350,400,450} for both T2 and Mix second stages.

## Results (Table 2, n=200 = 40 systems × 5 rollouts)

| Model | Reward (bal.) | Rel. BA impr. (kcal/mol) | Sys. impr. /40 | Turns | Constr. % |
|---|---|---|---|---|---|
| **T1(400)–T2(100)** | 0.623 | **+3.18 ± 1.35** | 37 | 7.7 | 93.3% |
| T1(300)–T2(200) | 0.622 | **+3.88 ± 1.98** | 34 | 7.3 | 93.7% |
| T1(250)–Mix(250) | 0.611 | +3.65 | 37 | 7.2 | 91.9% |
| T1(500) *(reference)* | 0.570 | 0.00 (ref) | 35 | 11.2 | 94.0% |
| GPT-5.6 Sol | 0.542 | +1.44 | 37 | 13.3 | 89.9% |
| Claude Opus 5 | 0.505 | −0.16 | 35 | 14.7 | 83.2% |
| GLM-5.2 | 0.317 | −0.58 | 34 | 17.7 | 63.2% |
| **Qwen 3.6 (base)** | 0.122 | **−2.89** | 24 | 14.6 | **36.2%** |

**Rel. BA improvement is normalised by subtracting the T1(500) model's average** — so
reproducing the comparison *requires* running a Tier-1-only arm as the reference.
Paired SE over the 40 shared systems. Invalid rollouts score 0.

### Findings that matter for a reproduction
1. **Tier-1-only already transfers**, closing most of the base→frontier gap. The cheap tier
   alone does a lot of work.
2. **Every curriculum arm beats T1(500)**; many beat frontier models.
3. **T2(500) mode-collapses** (App C.1, Fig A1): from the base model, Tier-2-only training
   produces **degenerate single-turn policies** — `r_obj` stays ≈ 0 while `r_constraint`
   saturates, i.e. a **constraint-only policy** that never iterates or calls tools. "The Tier-2
   tasks are too difficult for the Qwen 3.6 (base) model to learn directly using RL."
   *This is the load-bearing claim and it has a cheap, unmistakable signature.*
4. **No scaling law** — more expensive recipes do not monotonically improve BA.
5. **Mixing Tier-1 back in during stage 2 is generally not beneficial** → minimal catastrophic
   forgetting. Exception: T1(250)–Mix(250) ≫ T1(250)–T2(250).
6. Trained models are **more efficient**: 7.7 turns vs 13–18 for frontier; fewer tokens; they
   call the expensive scorer **earlier**.
7. **Reliability** (Table A3): trained models ~198–200/200 successful. **Qwen 3.6 base: only
   74/200 successful, 123/200 invalid formatting.** A base model barely functions in this
   harness — strong evidence that a small *base* model is a dead start.
8. Trained models **shrink molecules and avoid halogenation**; frontier models grow and
   halogenate. Removing an anionic group improved relative BA by **26.1 kcal/mol** on average,
   and curriculum-trained models overwhelmingly learned to do it.
9. Generative diversity of trained models ≈ frontier models; T1(500) highest.

## Reproduction-relevant inventory

**Fully specified → reimplementable:** reward functions and all hyperparameters (Tables A1, A2),
Tier-1 generation algorithm, Tier-2 constraint set, PLINDER filter criteria, both prompt
templates, textification format, curriculum definitions, evaluation metrics.

**Gated / unavailable:**
- OpenEye **POSIT** + **Chemgauss4** → all of Tier-2 scoring (commercial; academic licence
  requires institutional employment)
- 15 of 116 Tier-1 properties (OpenEye)
- OpenEye `.oedu` design-unit filter criterion
- **SQM2.20** → no standalone implementation exists; PM6-D3H4X + COSMO2 assembled from
  MOPAC2016 + Cuby4 + AmberTools, ~20 min/complex, know-how licensed commercially
- prime-rl **IPO loss** (`ipo_loss_fn`) — upstream TRL/Unsloth offer GRPO/Dr.GRPO/DAPO/BNPO, not IPO
- 32 × B200

**Free and open:** ZINC, PLINDER (Apache-2.0, data *and* code), RDKit (101/116 properties),
PoseBusters, BRICS scaffolds.

# LLM Fine Tuning — Synthetic Task Scaling at <8B

The shared vocabulary for reproducing arXiv:2609.04735 on one RTX 5090. Terms are drawn from the
paper and sharpened where the paper's own wording is ambiguous or collides with itself. The map is
[issue #1](https://github.com/zhipengzhu1-dotcom/10-09-2026-Small-Molecule-Design-with-Synthetic-Task-Scaling/issues/1).

## Language

### Molecular design

**Lead optimization**:
Improving a chosen property of an existing molecule by editing it, rather than designing a molecule
from nothing. The single abstraction all three oracle tiers share.

**Seed molecule**:
The existing molecule a task starts from, and the reference point every reward is measured against.
_Avoid_: starting molecule, lead, parent

**Oracle**:
A function that scores a molecule. Oracles are ranked by cost per evaluation, which is what makes
the paper's tiers a hierarchy rather than a menu.

**Scaffold**:
The core substructure a proposed molecule must retain, obtained by BRICS decomposition of the seed.
_Avoid_: core, framework, Murcko scaffold (a different, rejected notion — see
[#7](https://github.com/zhipengzhu1-dotcom/10-09-2026-Small-Molecule-Design-with-Synthetic-Task-Scaling/issues/7))

**Target**:
The **protein** a molecule is being optimised to bind, in Tier-2 and evaluation only. Never the
property being optimised — see _objective property_.

### Task structure

**Task**:
One lead-optimization problem instance: a seed molecule, an objective property with a direction, a
set of constraints, and a scaffold constraint.

**Objective property**:
The single property a task asks the model to maximise or minimise. Named this way deliberately: the
paper's prompt calls it the "target property", which collides with _target_ meaning the protein.
_Avoid_: target property

**Property constraint**:
A requirement on some property other than the objective, which a proposed molecule must satisfy.
Every task carries 2–4 of them plus a scaffold constraint.

**Preservation constraint**:
A property constraint the seed already satisfies, because it was derived from the seed's own value.
Its role is "do not break this while optimising".

**Repair constraint**:
A property constraint deliberately perturbed so the seed violates it. Its role is "fix this". Every
task has exactly one, which is the only reason any task is unsatisfied at the start.

**Scaffold constraint**:
The requirement that a proposal *contain* the seed's scaffold. A containment test, not an identity
test — a molecule may grow freely as long as the core survives.

**Hard constraint**:
A constraint scored 1 or 0 with no partial credit. Integer and boolean properties are always hard.

**Soft constraint**:
A constraint scored 1 inside its range and decaying by a Gaussian outside it, so near-misses earn
partial credit. Continuous properties are always soft.

### Pools and scale

**Seed pool**:
The fixed set of molecules that tasks draw their seeds from, and the same set the reward's property
statistics are measured over. One pool serves both roles so that the two can never disagree.

**σ (sigma)**:
A property's standard deviation over the seed pool. Not a tuning constant but **the unit every
reward is expressed in**, which is why the pool's composition sets the entire reward scale and why
σ is frozen once and never recomputed.

### Tiers and curricula

**Tier-1**:
The cheap synthetic task tier, scored by RDKit descriptors in milliseconds. Tasks are generated in
bulk from seeds.

**Tier-2**:
The medium-cost task tier, scored by docking a proposal into a real protein pocket. Tasks come from
experimental structures, so they are scarce.

**Held-out oracle**:
The expensive oracle used only to evaluate, never to train. Its whole purpose is to be something the
model has never optimised against, which is what makes transfer a real claim.

**Curriculum arm**:
One training run with a particular schedule of tiers, e.g. Tier-1 for 400 steps then Tier-2 for 100.
The comparison *between* arms is the paper's contribution, so arms must stay comparable — which is
why the task set and σ are frozen across all of them.

**Deviation**:
A documented, deliberate departure from the paper, with its reason. Deviations are acceptable; the
undocumented kind is what the portfolio bar rules out.

# The 15 OpenEye Tier-1 properties: what an open reimplementation would actually be

Resolves [#18](https://github.com/zhipengzhu1-dotcom/10-09-2026-Small-Molecule-Design-with-Synthetic-Task-Scaling/issues/18).
Blocks [#16](https://github.com/zhipengzhu1-dotcom/10-09-2026-Small-Molecule-Design-with-Synthetic-Task-Scaling/issues/16)
decision point 4. Research date: **2026-10-11**.

**Question.** Table A4 of arXiv:2609.04735 lists 116 Tier-1 properties, 101 computed with RDKit
and **15 with OpenEye**. OpenEye is confirmed unobtainable for this project
([#5](https://github.com/zhipengzhu1-dotcom/10-09-2026-Small-Molecule-Design-with-Synthetic-Task-Scaling/issues/5)
closed as denied; the licence finding is §1 of
[`open-chem-oracle-stack.md`](open-chem-oracle-stack.md)). So: what would each of the 15 be if
reimplemented open, and how defensible is each definition without access to the original?

**Audience.** A beginner with no computational-chemistry background. Jargon is named on first use.

**Conventions** (same as [`open-chem-oracle-stack.md`](open-chem-oracle-stack.md))
- **[FACT]** — stated in a primary source, with the URL given.
- **[INFER]** — my reasoning, not in any source.
- **[not documented]** — I looked and the primary source is silent.

**The one framing rule this document obeys.** OpenEye cannot be run here, so **nothing below is an
equivalence claim.** Every proposal is *an open look-alike defined from published algorithm
descriptions, unvalidatable against the original.* Where a property is a standard graph count that
any correct implementation must agree on, that is said explicitly and is a much stronger claim than
where a vendor formula is being guessed at.

---

## The answer in five lines

1. **The complexity family is settled, and it is Bertz 1981.** Not a hypothesis any more —
   OpenEye's own docs cite `[Bertz-1981]` by name. RDKit's `BertzCT` is an independent
   implementation of the same published index, and **all three named components are separately
   recoverable** from RDKit's own internals by algebra, with no new algorithm needed.
2. **The provenance of all 15 is now traceable to four named OpenEye toolkits**, six of them by
   near-verbatim function-name match in a publicly readable API index. The paper never said this;
   the match is strong enough to treat as established.
3. **Two of the paper's own Table A4 descriptions contradict OpenEye's documented functions** —
   `oe_halide_fraction` and `oe_anionic_carbon_count`. This is a fork in the road the spec has to
   choose a side of, not a detail.
4. **13 of 15 are faithfully reimplementable**; 2 (`oe_symmetry_complexity`, and the exact
   identity of `oe_molecular_complexity` among four OpenEye entry points) rest on inference that
   cannot be closed without the software.
5. **For #16: this does not repair the integer pool.** Prediction, not measurement — of the 10
   integer/boolean properties among the 15, about **3** would clear the σ ≥ 2.5 gate, and they
   collapse to **1–2** after the |ρ| > 0.95 rule. Details and reasoning in §6.

---

## 1. Provenance: which OpenEye products the 15 actually come from

The paper attributes the 15 to "OpenEye" with no product named [not documented]. But OpenEye's
public API indexes are readable without a licence, and the function names line up almost verbatim
with the paper's identifiers.

**[FACT]** The **MolProp TK** Python API index
(<https://docs.eyesopen.com/toolkits/python/molproptk/api.html>) lists, among 85 entries, these
functions: `OEGetAnionicCarbonCount`, `OEGetAromaticRingCount`, `OEGetHalideFraction`,
`OEGetLongestUnbranchedCarbonsChain`, `OEGetLongestUnbranchedHeavyAtomsChain`,
`OEGetNumUnspecifiedAtomStereos`, `OEGetNumUnspecifiedBondStereos`, `OEGetFractionCsp3`,
`OEGet2dPSA`, `OEGetXLogP`, `OEGetRotatableBondCount`, `OEGetHBondDonorCount`,
`OEGetHBondAcceptorCount`, `OEGetLipinskiDonorCount`, `OEGetLipinskiAcceptorCount`.

Six of the paper's 15 identifiers are one-to-one renamings of that list. **[INFER]** The 15 are
therefore not a bespoke descriptor set — they are **the subset of OpenEye's standard MolProp /
OEMedChem / OEChem / QUACPAC descriptor surface that RDKit does not already cover**, which is
exactly what a team with an OpenEye licence would reach for. This matters: it means the
definitions are documented vendor functions, not unpublished models.

| Paper identifier | OpenEye origin | Toolkit |
|---|---|---|
| `oe_molecular_complexity` | `OEDetermineMolecularComplexity` (or `OETotalMolecularComplexity`) | OEMedChem TK |
| `oe_connective_complexity` | `OEDetermineConnectiveComplexity` | OEMedChem TK |
| `oe_symmetry_complexity` | `OEDetermineSymmetryComplexity` | OEMedChem TK |
| `oe_elemental_complexity` | `OEDetermineElementalComplexity` | OEMedChem TK |
| `oe_aromatic_ring_count` | `OEGetAromaticRingCount` | **MolProp TK** |
| `oe_halide_fraction` | `OEGetHalideFraction` | **MolProp TK** |
| `oe_anionic_carbon_count` | `OEGetAnionicCarbonCount` | **MolProp TK** |
| `oe_longest_unbranched_chain` | `OEGetLongestUnbranchedHeavyAtomsChain` | **MolProp TK** |
| `oe_unspecified_bond_stereo_count` | `OEGetNumUnspecifiedBondStereos` | **MolProp TK** |
| `oe_aromatic_atom_count` | `OEAtomBase.IsAromatic` count | OEChem TK |
| `oe_aromatic_bond_count` | `OEBondBase.IsAromatic` count | OEChem TK |
| `oe_ring_bond_count` | `OEBondBase.IsInRing` count | OEChem TK |
| `oe_ring_system_count` | `OEDetermineRingSystems` / FILTER `MIN_RING_SYS` | OEChem TK / MolProp TK |
| `oe_is_macrocycle` | `OEIsMacrocycle` | **Omega TK** (`OEConfGen`) |
| `oe_net_charge_neutral_ph` | `OESetNeutralpHModel` then sum formal charges | **QUACPAC TK** |

The last three columns are **[INFER]** where no exact identifier match exists (the OEChem flag
counts, which need no dedicated function); the five MolProp rows and the four OEMedChem rows are
**[FACT]** name matches.

---

## 2. HIGHEST PRIORITY: the complexity family is Bertz 1981

The project's prior note guessed `oe_molecular_complexity ≈ BertzCT` and marked it `[INFER]`
([`open-chem-oracle-stack.md`](open-chem-oracle-stack.md) §3A). **That guess was right, and it is
now [FACT].**

### 2.1 What OpenEye says, verbatim

**[FACT]** <https://docs.eyesopen.com/toolkits/python/medchemtk/OEMedChemFunctions/OEDetermineMolecularComplexity.html>
— the whole substantive body of the page:

> From **[Bertz-1981]**. Includes connectivity and elemental complexity. Though aromaticity is not
> addressed in the brief literature note, **aromatic bonds are not counted as double bonds for the
> entropy calculation in this implementation.** The three additional api points return the three
> individual terms that make up the Molecular Complexity as defined by Bertz.

**[FACT]** The same docs tree resolves `[Bertz-1981]`
(<https://docs.eyesopen.com/toolkits/python/medchemtk/bibliography.html>):

> **Bertz-1981** — Steven H. Bertz, *The first general index of molecular complexity*, Journal of
> the American Chemical Society, Vol. 103, pp. 3599–3601, 1981.
> DOI [10.1021/ja00402a071](https://pubs.acs.org/doi/abs/10.1021/ja00402a071)

**[FACT]** <https://docs.eyesopen.com/toolkits/python/medchemtk/OEMedChemFunctions/OETotalMolecularComplexity.html>
gives the composition algebra:

> This is the final function to use for assessing molecular complexity.
> `OETotalMolecularComplexity = OENormalMolecularComplexity + OENormalStereoComplexity`. In turn,
> `OENormalMolecularComplexity = OEDetermineConnectiveComplexity + OEDetermineElementalComplexity`.
> **Ring complexity is not included** because it did not contribute significantly to reproduction
> of chemists' notion of synthetic accessibility.

**[FACT]** `OENormalMolecularComplexity` "scales the value from `OEDetermineMolecularComplexity`
to [0-1] assuming the underlying complexity is [0-1000] which is the case from most small
molecules"
(<https://docs.eyesopen.com/toolkits/python/medchemtk/OEMedChemFunctions/OENormalMolecularComplexity.html>).

**[FACT]** The two sibling terms OpenEye deliberately keeps out of the main index:
`OEDetermineRingComplexity` is "a non-SSSR adaptation of the ring complexity algorithm of
[Gasteiger-1979]", and `OEDetermineStereoComplexity` reproduces the tetrahedral-stereo term added
by `[Boda-2007]` "with the addition of chiral bond stereo".

**[FACT]** The three component pages (`OEDetermineConnectiveComplexity`,
`OEDetermineSymmetryComplexity`, `OEDetermineElementalComplexity`) contain **only a signature and
a cross-reference back to `OEDetermineMolecularComplexity`** — no formulas. So the per-component
formulas are **[not documented]** by OpenEye; the only authority is Bertz 1981 itself (paywalled,
JACS).

### 2.2 The docs contradict themselves on "three terms", and Bertz explains why

Note the tension: `OEDetermineMolecularComplexity` says the molecular complexity is made of
**three** terms (connective, symmetry, elemental), while `OETotalMolecularComplexity` writes it as
a sum of **two** (connective + elemental).

**[INFER]** Both are right, because in Bertz's construction **symmetry is not an additive third
term — it is a correction applied inside the connective term.** Bertz's connectivity index has the
form

```
C(eta)  =  2 * eta * log2(eta)  -  SUM_i  eta_i * log2(eta_i)
```

where `eta` is the total number of "connections" (adjacent pairs of bonds, weighted by bond order)
and the `eta_i` are the counts of connections falling into each **symmetry-equivalence class** of
the molecular graph. If the molecule has no symmetry every `eta_i = 1`, the second sum vanishes,
and `C(eta) = 2 * eta * log2(eta)`. Symmetry *reduces* the complexity, and the amount it reduces
it by is `SUM_i eta_i * log2(eta_i)`. **That subtracted quantity is what a "symmetry complexity"
api point would naturally return**, which is why it is a nameable component of the index without
being a summand of it.

The elemental term (Bertz's heteroatom-diversity contribution) is a plain Shannon entropy over the
element counts, scaled by the number of atoms:

```
C(E)  =  n * log2(n)  -  SUM_j  n_j * log2(n_j)
```

with `n` the number of (heavy) atoms and `n_j` the count of each chemical element present.

**[FACT, partial]** Corroboration that `CT = C(eta) + C(E)` is the published decomposition of the
Bertz index, with an elemental term accounting for heteroatoms, appears in the secondary
literature reviewing the index. **[not documented] here:** I could **not** read Bertz 1981 itself
(JACS, paywalled) and therefore cannot quote its equations verbatim. The formulas above are
reconstructed in §2.3 from an open implementation that cites it, and verified algebraically.

### 2.3 RDKit's `BertzCT` is the same quantity, and the components fall out of it

This is the decisive part, because RDKit's implementation is itself a primary source — open,
readable, and citing Bertz 1981.

**[FACT]** <https://raw.githubusercontent.com/rdkit/rdkit/master/rdkit/Chem/GraphDescriptors.py>.
The docstring: *"A topological index meant to quantify 'complexity' of molecules. **Consists of a
sum of two terms, one representing the complexity of the bonding, the other representing the
complexity of the distribution of heteroatoms.** From S. H. Bertz, J. Am. Chem. Soc., vol 103,
3599-3601 (1981)."*

**[FACT]** The function returns `_CalculateEntropies(connectionDict, atomTypeDict, numAtoms)`,
which is exactly:

```python
connectionIE = totConnections * (InfoEntropy(connectionList) + log2(totConnections))
atomTypeIE   = numAtoms       *  InfoEntropy(atomTypeList)
return atomTypeIE + connectionIE
```

and **[FACT]** `InfoEntropy(counts) = -SUM p_i * log2(p_i)` with `p_i = counts_i / total`
(<https://raw.githubusercontent.com/rdkit/rdkit/master/rdkit/ML/InfoTheory/entropy.py>).

**[FACT, verified here]** Substituting the entropy definition and simplifying gives precisely the
two Bertz forms of §2.2:

- `connectionIE  ==  2*eta*log2(eta) - SUM_i eta_i*log2(eta_i)`  →  Bertz `C(eta)`
- `atomTypeIE    ==  n*log2(n) - SUM_j n_j*log2(n_j)`            →  Bertz `C(E)`

I checked the first identity numerically on 2,000 random connection multisets (including
fractional bond orders): maximum absolute discrepancy **5.7e-14**, i.e. floating-point exact. The
check was arithmetic only, in a scratch directory, and no code was added to the repo.

**So the answer to #18's load-bearing question is:**

| Paper property | Recoverable from RDKit as |
|---|---|
| `oe_molecular_complexity` | `Descriptors.BertzCT(mol)` **directly** |
| `oe_connective_complexity` | the `connectionIE` half of `BertzCT` |
| `oe_elemental_complexity` | the `atomTypeIE` half of `BertzCT` |
| `oe_symmetry_complexity` | `2*eta*log2(eta) - connectionIE`, i.e. `SUM_i eta_i*log2(eta_i)` |

**Yes, RDKit's `BertzCT` computes the same quantity** (same published index, independent
implementation), **and yes, the three components are separately recoverable** — all four numbers
come from one pass over the same two dictionaries RDKit already builds. No new algorithm is
needed; the work is splitting a return value that is currently summed. Cost is therefore the
measured `BertzCT` cost, **0.245 ms/molecule** single-core
([`open-chem-oracle-stack.md`](open-chem-oracle-stack.md) §3A), for all four properties together
rather than four times over.

**Two robustness notes for a 1 M-molecule pass.** **[FACT]** `BertzCT`'s own docstring warns *"this
barfs if the molecule contains a second (or nth) fragment that is one atom"* — a real hazard for
salts and counterions. For *this* pool it does not bite: the σ cache records `bertz_ct` with
**1,000,000 finite values and 0 non-finite**, and `num_fragments` σ = 0 with every molecule at 1.0,
so the pool is single-fragment by construction. It would bite on policy-generated molecules, where
`properties.py`'s existing `_safe` nan-wrapper is the right guard. **[FACT]** `BertzCT.version` is
`"2.0.0"` and its docstring states *"THIS MEANS THAT THIS IMPLEMENTATION IS NOT BACKWARDS
COMPATIBLE. Any molecule containing aromatic rings will yield different values with this
implementation"* — so published pre-2.0 Bertz values are not comparable either, which is a second
reason no external cross-check is available.

**There is no second open implementation to cross-check against.** **[FACT]** `mordred`'s `BertzCT`
docstring is *"Bertz CT descriptor (rdkit wrapper)"* and its body is
`return float(RDKit.BertzCT(self.mol, dMat=D))`; CDK does not implement Bertz at all (§5.2). So
RDKit's is the **only** open implementation of this index. The obvious validation route — compare
two independent open implementations and treat agreement as evidence — **does not exist.**

### 2.4 Three documented reasons the numbers will still not match OpenEye

Important, because it is tempting to read §2.3 as equivalence. It is not.

1. **Aromatic bonds are handled differently, and both sides document it.** **[FACT]** OpenEye:
   *"aromatic bonds are not counted as double bonds for the entropy calculation in this
   implementation."* **[FACT]** RDKit assigns aromatic bonds a bond order of **1.5** and then, in
   the `if bond_i_order > 1` branch, credits them `1.5*0.5/2 = 0.375` connections. So RDKit *does*
   give aromatic bonds partial multiple-bond character where OpenEye explicitly does not.
   **[INFER]** For drug-like molecules, which are mostly aromatic rings, this alone guarantees
   systematically different values.
2. **The symmetry-class partition is computed by different heuristics.** **[FACT]** RDKit's
   `_AssignSymmetryClasses` buckets atoms by the sorted rows of a bond-order-weighted ("Balaban")
   distance matrix, truncated at the `cutoff=100` nearest neighbours; its own docstring explains
   `cutoff` as *"consider vertices topologically identical if their distance vectors … are equal
   out to the cutoff-th nearest-neighbor."* That is an **approximation to graph-automorphism
   orbits, not a computation of them.** **[not documented]** what symmetry perception OpenEye
   uses. **[INFER]** Since `eta_i` are the symmetry-class bucket counts, a different partition
   changes both the connective and the symmetry term. (**[INFER]** `Chem.CanonicalRankAtoms(mol,
   breakTies=False)` gives true RDKit symmetry classes and would be a more principled orbit
   source — but using it is a *deviation from RDKit's own `BertzCT`*, so it would need logging as
   such, and it would break comparability with the project's already-computed `bertz_ct` column.)
3. **The normalisation and the stereo term are an open choice.** OpenEye has four entry points
   (`OEDetermine…`, `OENormal…`, `OETotal…`, plus the ring and stereo terms). **[not documented]**
   which one the paper's `oe_molecular_complexity` is. **[INFER]** It is
   `OEDetermineMolecularComplexity` — the raw, unnormalised Bertz value — because the paper lists
   exactly connective + symmetry + elemental as its "components", which is the decomposition that
   page describes, and because Table A4 types it as continuous with no [0,1] bound. If instead it
   were `OETotalMolecularComplexity`, the values would be in roughly [0,2] and would carry a
   Boda-2007 stereo term with no RDKit analogue.

### 2.5 The sting in the tail: 2 of the 4 are duplicates of a column the pool already has

**[INFER]**, and it matters for #16. If `oe_molecular_complexity` is implemented as `BertzCT`,
then it is **numerically identical to the pool's existing `bertz_ct` property** — Spearman ρ = 1.0
by construction, not merely high. And since `oe_molecular_complexity = oe_connective_complexity +
oe_elemental_complexity` with the connective term dominating for molecules of this size,
`oe_connective_complexity` will track `bertz_ct` at ρ well above 0.95 too.

So **#7's |ρ| > 0.95 collapse rule would delete two of the four complexity properties on sight.**
Only `oe_elemental_complexity` (element-diversity entropy, **[INFER]** likely correlated with
`heavy_atom_count` and `num_heteroatoms` but not identical to either) and
`oe_symmetry_complexity` (molecular symmetry, **[INFER]** a genuinely new axis the 101-property
pool contains nothing like) are candidates to add real variety.

---

## 3. The other 11, defined precisely

Each heading gives OpenEye's documented definition, then the proposed open implementation in
prose, then how defensible the match is. Chemistry terms are named on first use.

### 3.1 `oe_aromatic_ring_count` — the Ritchie definition

**Aromatic ring**: a flat ring of atoms sharing a cloud of electrons, which makes it unusually
stable; benzene is the archetype. "Heteroaromatic" means such a ring containing an atom other than
carbon (nitrogen, oxygen, sulfur).

**[FACT]** <https://docs.eyesopen.com/toolkits/python/molproptk/OEMolPropFunctions/OEGetAromaticRingCount.html>
— "Returns the number of aromatic rings in a molecule as defined in **[Ritchie-2009]**. The
article describes the method as the following":

> The terminology 'number of aromatic rings' (or aromatic ring count) is used generically and
> **encompasses both benzenoid aromatic rings and heteroaromatics** (including, e.g. pyridine and
> imidazole). … **Each ring in a fused system is counted individually**; thus, **indole and
> naphthalene are each defined as having two aromatic rings.**

**[FACT]** The citation, verified against PubMed: **Ritchie TJ, Macdonald SJF**, "The impact of
aromatic ring count on compound developability — are too many aromatic rings a liability in drug
design?", *Drug Discovery Today* **14**(21–22): 1011–1020 (2009), PMID
[19729075](https://pubmed.ncbi.nlm.nih.gov/19729075/), DOI
[10.1016/j.drudis.2009.07.014](https://doi.org/10.1016/j.drudis.2009.07.014). Follow-up: **Ritchie
TJ, Macdonald SJF, Young RJ, Pickett SD**, "…further insights by examining carbo- and hetero-
aromatic and -aliphatic ring types", *Drug Discovery Today* **16**(3–4): 164–171 (2011), PMID
[21129497](https://pubmed.ncbi.nlm.nih.gov/21129497/), DOI
[10.1016/j.drudis.2010.11.014](https://doi.org/10.1016/j.drudis.2010.11.014).

**[not documented]** The 2009 paper's own text could not be read (ScienceDirect returns HTTP 403,
no open copy). The definition above is quoted *as OpenEye attributes it to Ritchie*; whether it is
verbatim from the paper or OpenEye's paraphrase is unverified. OpenEye's page also names **no
aromaticity perception model** for this descriptor.

**Proposed open implementation.** `rdkit.Chem.Lipinski.NumAromaticRings` — **[FACT]** documented as
"calculates the number of **aromatic SSSR rings**"
(<https://www.rdkit.org/docs/cppapi/Lipinski_8h.html>). SSSR = "smallest set of smallest rings",
the conventional minimal ring basis.

**Defensibility: high on the count, with a named caveat.** **[INFER]** The *number* of rings in a
ring system is a graph invariant — the circuit rank, `bonds − atoms + 1` — even though *which*
rings an SSSR picks is ambiguous. Naphthalene: 11 ring bonds, 10 ring atoms → 2. Indole: 10 ring
bonds, 9 ring atoms → 2. Both match Ritchie exactly. So the two definitions agree by construction
for any fully-aromatic ring system, which is the drug-like majority case. The caveat is
**aromaticity perception**, not counting: see §5.3.

### 3.2 `oe_aromatic_atom_count` and `oe_aromatic_bond_count`

**[not documented]** No dedicated MolProp function exists for either; they are absent from the API
index of §1. **[FACT]** OEChem exposes per-atom and per-bond aromatic flags set by
`OEAssignAromaticFlags` and read via `OEAtomBase.IsAromatic` / `OEBondBase.IsAromatic`
(<https://docs.eyesopen.com/toolkits/python/oechemtk/aromaticity.html>). **[INFER]** The paper's
two counts are therefore just sums over those flags.

**Proposed open implementation.** Count atoms with `atom.GetIsAromatic()`; count bonds with
`bond.GetIsAromatic()`.

**Defensibility: the arithmetic is trivial; all the risk is in perception.** **[FACT]** OEChem's
aromatic flags are *not unique* — `OEAssignAromaticFlags` takes a model argument and OpenEye ships
five (OpenEye/default, Daylight, Tripos, MDL, MMFF), and the docs state the models "define
aromaticity rules differently" so even canonical SMILES differ between them (same URL).
**[not documented]** which model the paper used; the default (`OEAroModel_OpenEye`) is the obvious
guess **[INFER]**, since `OESmilesToMol` and `OEReadMolecule` apply it automatically. See §5.3 for
how far RDKit's default can be expected to agree.

### 3.3 `oe_ring_bond_count` — a pure graph invariant

**[FACT]** OEChem defines ring membership graph-theoretically, not by ring enumeration
(<https://docs.eyesopen.com/toolkits/python/oechemtk/ring.html>): *"In graph-theoretical terms, a
bond is considered cyclic if its removal from the structure would not lead to the structure being
broken into separate components."*

**Proposed open implementation.** Count bonds where `bond.IsInRing()` is true.

**Defensibility: the highest of all 15.** A bond is in a ring exactly when it is not a *bridge* (a
bond whose removal disconnects the graph). That is a textbook invariant with one correct answer,
independent of SSSR, aromaticity or any vendor convention. **[INFER]** Any correct implementation
must agree, so this is not a look-alike — it is the same number.

### 3.4 `oe_ring_system_count` — "contiguous", not "fused"

Table A4 calls these "distinct (**fused**) ring systems". **OpenEye's own wording is different and
looser.** **[FACT]** The FILTER criterion `MIN_RING_SYS`/`MAX_RING_SYS`
(<https://docs.eyesopen.com/toolkits/python/molproptk/theory/filter_files_stub.html>):

> **Ring Systems** — Number of ring systems (**contiguous systems of ring atoms and bonds**).

**[FACT]** The matching OEChem primitive is `OEDetermineRingSystems`, which "return[s] a mapping
from atom indices to a ring … system index", behaving "very similarly to `OEDetermineComponents`"
— i.e. it is a **connected-components** computation — and "all acyclic atoms are mapped to the
value zero" (<https://docs.eyesopen.com/toolkits/python/oechemtk/ring.html>).

**Proposed open implementation.** Build the subgraph of ring bonds (§3.3), find its connected
components, count them. Equivalently: union-find over `mol.GetRingInfo().AtomRings()`, merging any
two rings that **share at least one atom**.

**The distinction that matters.** "Contiguous" and "fused" are not the same thing:

- Two rings sharing a **bond** (*fused*, e.g. naphthalene) → 1 system under both readings.
- Two rings sharing exactly one **atom** (*spiro* — a single atom pivoting between two rings) → 1
  system under OpenEye's "contiguous", but arguably 2 under a strict reading of "fused".
- Two rings joined by a bond but sharing nothing (e.g. biphenyl) → 2 systems under both.

**[INFER]** Follow OpenEye ("contiguous", so spiro merges), because the value came from OpenEye;
log the divergence from Table A4's word "fused". The pool measures `num_spiro_atoms` mean 0.049, so
**[INFER]** the choice changes roughly 5% of molecules by at most 1 — small but not nil.

**Defensibility: high.** Connected components of the ring subgraph is as canonical as §3.3 once
the spiro convention is fixed. The project's earlier note equating this to
`RingCount`/`NumAromaticRings` was wrong, as #18 says; those count *rings*, this counts *clumps of
rings*.

### 3.5 `oe_is_macrocycle`

**Macrocycle**: a ring large enough to behave like a flexible loop rather than a rigid plate;
erythromycin and crown ethers are examples.

**[FACT]** <https://docs.eyesopen.com/toolkits/python/omegatk/OEConfGenFunctions/OEIsMacrocycle.html>
— signature `OEIsMacrocycle(mol, minSize: int = 10) -> bool`:

> By default, a molecule is defined as macrocycle when it contains a **10-membered or larger
> ring**, regardless of aromaticity and heteroatom content. For example, large cyclic alkanes,
> annulenes, crown ethers, and porphyrins are all macrocycles.

This confirms Table A4's "(≥ 10 atoms)" and resolves it as **ring size in atoms, inclusive of 10**.

**Proposed open implementation.** True if any SSSR ring has ≥ 10 atoms:
`max((len(r) for r in mol.GetRingInfo().AtomRings()), default=0) >= 10`. RDKit's
`RingInfo.IsAtomInRingOfSize` is the direct analogue of OpenEye's `OEAtomIsInRingSize`.

**Defensibility: high, with one documented structural caveat.** **[FACT]** OEChem deliberately
ships **no SSSR at all** — "We believe that it is a great service to our customers that we do not
include any SSSR functionality in OEChem TK. This is a conscious (and consensus) decision"
(ring.html), on the grounds that SSSR "is not a unique subset of all possible cycles". So
OpenEye's ring-size test cannot be SSSR-based; **[INFER]** it is built on per-atom smallest-ring
size (`OEAtomGetSmallestRingSize`). **[INFER]** For **bridged** polycyclics the two can disagree:
a large cycle that an SSSR decomposes into smaller rings is invisible to a max-SSSR-size test. For
the simple macrolide/crown cases OpenEye names, both agree. The pool measures
`num_bridgehead_atoms` mean 0.064, so **[INFER]** this is a rare-case divergence.

### 3.6 `oe_longest_unbranched_chain` — atoms, non-ring, degree ≤ 2

**[FACT]** <https://docs.eyesopen.com/toolkits/python/molproptk/OEMolPropFunctions/OEGetLongestUnbranchedHeavyAtomsChain.html>:

> Returns the **size** of the longest chain of heavy atoms in a molecule. This is defined to be the
> **maximum number of connected, unbranched, and non-ring heavy atoms**. An **unbranched atom is a
> chain atom with maximum two connections to other heavy chain atoms**. A set of unbranched atoms
> which are connected together form a chain. A molecule may contain multiple chains which are
> isolated from each other by non-chain atoms (e.g. ring or branched atoms).

**[FACT]** The FILTER page states it slightly differently: *"An unbranched atom is an atom with at
most two connections **to other heavy atoms** and is not in a ring"* — dropping the word "chain".
Default limits `MIN_UNBRANCHED 1`, `MAX_UNBRANCHED 13`.

This answers #18's three sub-questions:
- **Measured in atoms, not bonds** — "the maximum number of … heavy atoms".
- **Hydrogens excluded** ("heavy" = non-hydrogen).
- **A chain is broken by** (a) any ring atom, and (b) any atom with three or more heavy
  neighbours (a branch point).

**[FACT, unresolved]** The two wordings differ in a way that changes answers. Under *"two
connections to other heavy **chain** atoms"*, an atom could have a third neighbour provided that
neighbour is a ring atom and so not a chain atom — e.g. the central carbon of `Ph–CH(CH3)–CH2–CH3`
has three heavy neighbours, but only two are non-ring. Under *"two connections to other heavy
atoms"* it is a branch point and breaks the chain. OpenEye's two pages say both. **[not
documented]** which the implementation does; the function page's worked examples are images I
could not read.

**Proposed open implementation (stating the choice).** Take the subgraph of non-ring heavy atoms;
delete every atom whose degree **within that subgraph** is ≥ 3; return the number of atoms in the
largest remaining connected component. That is the "chain atoms only" reading, which matches the
function page (the more specific source) and is the self-consistent one — it makes "chain" a
property of the induced subgraph throughout. **Log the reading as a deviation**, because the FILTER
page supports the other.

**Defensibility: medium.** The algorithm is elementary graph work with no vendor magic, but the
branch-point rule is genuinely ambiguous between two OpenEye pages, and the choice shifts values on
branched aliphatic tails — common in this chemical space. Note also that `OEGetLongestUnbranched
CarbonsChain` exists as a separate carbons-only variant; Table A4's description says
"heavy-atom chain", which selects the heavy-atom function **[INFER]**.

### 3.7 `oe_halide_fraction` — the paper's description contradicts OpenEye

**Halogen**: fluorine, chlorine, bromine, iodine (and astatine). A "halide" in a drug molecule is a
halogen atom attached to the rest of the structure.

**Table A4 says:** "Fraction of heavy atoms that are halogens."

**[FACT] OpenEye says something else.**
<https://docs.eyesopen.com/toolkits/python/molproptk/OEMolPropFunctions/OEGetHalideFraction.html>:

> `OEGetHalideFraction(mol, isotopic: bool = False) -> float` — Returns the **percent of molecular
> weight from halides.**

**[FACT]** The FILTER page agrees and gives the defaults: *"Halide Fraction — Percent of molecular
weight from halides"*, `MIN_HALIDE_FRACTION 0.0`, `MAX_HALIDE_FRACTION 0.66`.

These are different quantities. One iodine on a 350 Da scaffold is ~1/25 of the heavy atoms but
~36% of the mass. **[INFER]** Table A4's description is the paper's own paraphrase and is wrong
about OpenEye's function.

**Proposed open implementation.** Follow **OpenEye**: sum the atomic masses of all F/Cl/Br/I atoms
and divide by the molecule's molecular weight (`Descriptors.MolWt`, which includes hydrogens).
Keep the mass-fraction definition and **log the divergence from Table A4's wording in the spec**,
because the prompt text the model sees comes from the description while the property semantics come
from the function.

**Defensibility: high on the formula, with an explicit decision to record.** Mass fraction of a
named element set is unambiguous arithmetic. The only judgement is which of the paper's two
mutually inconsistent sources to honour. **[not documented]** whether OpenEye's "percent" means a
0–1 fraction or a 0–100 percentage — the default bound of `0.66` says **fraction** **[INFER]**, and
Table A4 typing it continuous is consistent either way.

### 3.8 `oe_anionic_carbon_count` — the paper's description contradicts OpenEye again

**Table A4 says:** "Number of formally negatively-charged carbon atoms."

**[FACT] OpenEye is narrower.**
<https://docs.eyesopen.com/toolkits/python/molproptk/OEMolPropFunctions/OEGetAnionicCarbonCount.html>:

> Returns the number of anionic carbons in a molecule. Anionic carbon is defined as an **aromatic**
> carbon that has negative 'formal charge'.

The "See also" confirms the two tests: `OEAtomBase.IsAromatic` **and** `OEAtomBase.GetFormalCharge`.

**[INFER]** This is a much smaller set than Table A4 implies. Aromatic carbanions
(cyclopentadienide-like rings) are essentially absent from purchasable drug-like space, whereas
non-aromatic carbanions, though also rare, are a different population. Following Table A4 would
produce a different — and still near-zero — property.

**Proposed open implementation.** Follow **OpenEye**: count atoms where
`atom.GetSymbol() == "C" and atom.GetIsAromatic() and atom.GetFormalCharge() < 0`. Log the
divergence from Table A4.

**Defensibility: high on the formula, low on usefulness.** Two flag tests, no ambiguity. But
**[INFER]** this property will be identically 0 for very nearly every molecule in a ZINC drug-like
pool, which makes it degenerate as an objective regardless of whose definition is used (§6).

### 3.9 `oe_unspecified_bond_stereo_count`

**Double-bond stereochemistry (E/Z)**: when a double bond cannot rotate, the groups on its two ends
are locked into one of two arrangements. A SMILES string may leave that arrangement unstated.

**[FACT]** <https://docs.eyesopen.com/toolkits/python/molproptk/OEMolPropFunctions/OEGetNumUnspecifiedBondStereos.html>:

> Returns the number of unspecified stereo bonds in a molecule. The **`OEPerceiveChiral`** function
> will be called to perceive chiral bonds in the molecule.

So the definition is two-stage: **perceive** which bonds *could* carry E/Z stereochemistry, then
**count** those whose configuration is not stated. Confirmed by the "See also" pointing at
`OEBondBase.HasStereoSpecified`. **[FACT]** The FILTER defaults are
`MIN/MAX_UNSPECIFIED_BOND_STEREOS 0/2`, and the page notes these "are **not used for filtering in
the default filters**".

**Proposed open implementation.** `Chem.FindPotentialStereo(mol)` and count the returned
`StereoInfo` entries with `type == StereoType.Bond_Double` and
`specified == StereoSpecified.Unspecified`. **[FACT]** Those enum members exist with those exact
semantics: `Bond_Double` is commented *"single double bond and odd-numbered cumulenes"* and
`StereoSpecified` is `{Unspecified /* no information provided */, Specified, Unknown /* deliberately
marked as unknown */}`
(<https://raw.githubusercontent.com/rdkit/rdkit/master/Code/GraphMol/Chirality.h>).

**Defensibility: medium.** The *shape* of the computation matches OpenEye's two-stage definition
exactly, and `properties.py` already uses RDKit's atom-side analogue
(`CalcNumUnspecifiedAtomStereoCenters`) for the corresponding RDKit property, so this is consistent
with existing practice. Two real caveats: **[FACT]** RDKit's own header warns *"this function is
still somewhat experimental and the API and results may change in a future release"*; and
**[not documented]** what `OEPerceiveChiral` counts as a potentially-stereogenic bond, so the two
perceivers may disagree on the candidate set even when they agree on what "unspecified" means. A
decision is also needed on whether `Unknown` (explicitly marked as unknown, the SMILES/SDF "either"
flag) counts as unspecified — **[INFER]** it should not, since OpenEye's test is
`HasStereoSpecified`, and an explicit "unknown" marking *is* a specification.

### 3.10 `oe_net_charge_neutral_ph` — the pH model, and the type question settled

**pH 7.4** is blood pH. At that pH some chemical groups gain or lose a proton (a hydrogen with its
charge), so the molecule's net electrical charge is not what the drawn structure says: carboxylic
acids tend to be negative, basic amines positive.

**[FACT]** <https://docs.eyesopen.com/toolkits/python/quacpactk/OEProtonFunctions/OESetNeutralpHModel.html>:

> This function will attempt to set `mol` to the most energetically favorable ionization state for
> **pH=7.4** using a **rule-based** system. This function **does not enumerate multiple states** for
> any molecule. In cases where the ionization is near 7.4 and could be represented by a mixture of
> states, **the state that is likely to be most populated is chosen.**

**[FACT]** The same model is the `pKa Normalization` stage of FILTER
(<https://docs.eyesopen.com/toolkits/python/molproptk/theory/filter_process.html>): *"pKa
normalization uses a **rule-based** system to set the ionization state of input molecules. … the
molecule is set to its most energetically favorable ionization state for pH=7.4. The rule-based
nature of this calculation allows it to be very fast. Furthermore, despite being rule-based, this
approach takes into account many secondary charge interactions."* It adds the vendor's own caveat:
*"this may not be appropriate for hit-to-lead or lead optimization."*

**This settles Table A4's `integer?` flag: it is an integer.** A single state is assigned, not an
ensemble average, so the net formal charge is a whole number. The project's note that an ensemble
average would be fractional was the right question to ask, and the answer is no.

**[not documented]** The actual pKa rules — which groups, what thresholds, what the "secondary
charge interactions" are. No OpenEye page publishes them. This is the one place in the 15 where the
vendor's *content*, not just its formula, is withheld.

**Proposed open implementation.** **Dimorphite-DL** at pH 7.4 over a tight window, take the single
dominant protonation state it returns, and sum formal charges with `Chem.GetFormalCharge`.
Licence-vetted in [`open-chem-oracle-stack.md`](open-chem-oracle-stack.md) §2b and re-confirmed
here from the actual file: **Apache-2.0**
([LICENSE.md](https://raw.githubusercontent.com/durrantlab/dimorphite_dl/main/LICENSE.md)), Ropp et
al., *J. Cheminform.* **11**:14 (2019), DOI
[10.1186/s13321-019-0336-9](https://doi.org/10.1186/s13321-019-0336-9), repo
<https://github.com/durrantlab/dimorphite_dl>.

**[FACT] The API in the prior record is stale — Dimorphite-DL 2.x is a breaking change.** Latest is
**2.1.0 (2026-10-02)**, `requires-python >= 3.10`. The 1.x names the earlier note implies no longer
exist:

| | 1.2.5 | 2.1.0 |
|---|---|---|
| pH flags | `--min_ph` / `--max_ph` | **`--ph_min` / `--ph_max`** |
| precision | `--pka_precision` | **`--precision`** |
| input | `--smiles` / `--smiles_file` | **positional** (string *or* file path) |
| Python entry point | `dimorphite_dl.cli.run(...)`, `run_with_mol_list(mols)` | **`from dimorphite_dl import protonate_smiles`** |

**[FACT]** The 2.x signature is
`protonate_smiles(smiles_input, ph_min=6.4, ph_max=8.4, precision=1.0, label_identifiers=False,
label_states=False, max_variants=128, validate_output=True) -> list[str]`. **`run_with_mol_list` is
gone** — 2.x is SMILES-in / SMILES-out, so the pool pass must round-trip through SMILES rather than
pass RDKit `Mol` objects. Logging goes to stderr, so stdout carries only SMILES.

**[FACT] Two 2.1.0 behaviour changes that move the numbers**, from its CHANGELOG: *"Amides and
anilides are no longer deprotonated at physiological pH… This changes the output for existing
inputs, so pipelines that depend on the previous enumeration should be checked."* And the share of
inputs for which it returns **only the dominant species at pH 7.4 rose from 48% to 65%**, measured
against Baltruschat & Czodrowski (2020), *F1000Research* **9**:113. That 65% is the single most
useful number in this section: **for about a third of molecules the open tool still returns more
than one state at pH 7.4, where OpenEye returns exactly one** — so the reduction-to-one-state rule
is not a formality, it fires often.

**Why not `obabel -p 7.4`?** **[FACT]** Open Babel's pH model is a SMARTS-rule table plus
Henderson–Hasselbalch: `data/phmodel.txt` is 179 lines — **38 active TRANSFORM rules and 25
SEEDCHARGE lines**, roughly 20 distinct chemotypes with single fixed pKa values (carboxylic acid
4.0, amine 10.0, tetrazole 4.89, guanidine/amidine 12.5, …), applied per site with a hard
winner-takes-all threshold and no coupling between ionisable centres. Anything outside those SMARTS
is left untouched at any pH. Dimorphite-DL instead carries fitted pKa windows with measured means
and standard deviations and a `--precision` knob. Open Babel is also **GPL-2.0-only** against
Dimorphite-DL's Apache-2.0. **[not documented]** Open Babel publishes no accuracy claim for its pH
model. (Two traps if it is ever used anyway: `-h` silently disables `-p`, and `-p`'s argument is
parsed greedily, so the number must be attached — `-p7.4`, not `-p 7.4`.)

**Defensibility: low-to-medium — the weakest of the 11.** Both tools are rule-based pKa estimators
working from substructure rules, so they are the same *kind* of thing, but **[not documented]**
OpenEye's rules means there is nothing to align to. **[FACT]** Dimorphite-DL's own README notes it
deprotonates indoles/pyrroles around pH 14.5 but does not protonate them around pH −3.5 — a known
asymmetry, irrelevant at 7.4 but indicative that its rule set is its own. Two further judgement
calls are forced: it enumerates *multiple* states over a pH *range* where OpenEye picks *one*
(and per the 65% figure above, that is the common case), so the code must reduce the ensemble to a
single state deterministically; and OpenEye's pipeline applies **salt and metal stripping before**
pKa normalisation (filter_process.html), which the open version must mirror or a counterion's charge
leaks into the total. The pool is already single-fragment (`num_fragments` measured σ = 0, every
molecule 1.0), so for *this* pool the stripping step is moot — but it is not moot for molecules the
policy generates during RL.

---

## 4. The per-property table: all 15

Confidence is in **the implementation matching the definition** — never in matching OpenEye, which
cannot be tested. Read it as: *high* = standard graph count or unambiguous arithmetic, any correct
implementation must agree; *medium* = definition published but with a resolvable ambiguity or a
known perception dependence; *low* = vendor-internal content, the open version is a different rule
set with the same purpose.

| # | Identifier | Paper's description | Authoritative definition found | Proposed open implementation | Source / licence | Confidence |
|---|---|---|---|---|---|---|
| 1 | `oe_molecular_complexity` | OpenEye molecular complexity index | **Yes** — Bertz 1981 index, "connectivity + elemental"; but 4 OpenEye entry points exist and which one is **[not documented]** | `Descriptors.BertzCT(mol)` | RDKit, **BSD-3** | **medium** — index settled, entry point inferred |
| 2 | `oe_connective_complexity` | Connectivity component | **Partial** — named as a Bertz term; per-term formula **[not documented]** by OpenEye | the `connectionIE` half of `BertzCT` = `2·η·log₂η − Σηᵢlog₂ηᵢ` | RDKit internals, **BSD-3** | **medium** |
| 3 | `oe_symmetry_complexity` | Symmetry component | **No** — no formula anywhere; reconstructed from Bertz's symmetry correction **[INFER]** | `2·η·log₂η − connectionIE` = `Σηᵢlog₂ηᵢ` | RDKit internals, **BSD-3** | **low** — the only genuinely reconstructed formula |
| 4 | `oe_elemental_complexity` | Elemental-diversity component | **Partial** — named as a Bertz term | the `atomTypeIE` half of `BertzCT` = `n·log₂n − Σnⱼlog₂nⱼ` | RDKit internals, **BSD-3** | **medium** |
| 5 | `oe_aromatic_atom_count` | Number of aromatic atoms | **Yes** (implicitly) — sum of OEChem aromatic atom flags; model **[not documented]** | count `atom.GetIsAromatic()` | RDKit, **BSD-3** | **medium** — trivial sum, perception-dependent (§5.3) |
| 6 | `oe_aromatic_bond_count` | Number of aromatic bonds | **Yes** (implicitly) — sum of OEChem aromatic bond flags | count `bond.GetIsAromatic()` | RDKit, **BSD-3** | **medium** — as above |
| 7 | `oe_aromatic_ring_count` | Number of aromatic rings (Ritchie definition) | **Yes, verbatim** — Ritchie 2009: heteroaromatics included, each ring of a fused system counted separately, naphthalene = indole = 2 | `Lipinski.NumAromaticRings` (aromatic SSSR rings) | RDKit, **BSD-3** | **high** on counting (circuit rank is invariant), medium overall via perception |
| 8 | `oe_ring_system_count` | Number of distinct (fused) ring systems | **Yes** — "**contiguous** systems of ring atoms and bonds"; `OEDetermineRingSystems` is connected components. **Not** "fused": spiro merges | connected components of the ring-bond subgraph (union-find over `AtomRings()` sharing ≥ 1 atom) | RDKit, **BSD-3** | **high** once the spiro convention is logged |
| 9 | `oe_is_macrocycle` | Contains a macrocyclic ring (≥ 10 atoms) | **Yes** — `OEIsMacrocycle(minSize=10)`: "10-membered or larger ring, regardless of aromaticity and heteroatom content" | `max(len(r) for r in AtomRings()) >= 10` | RDKit, **BSD-3** | **high**; bridged-polycycle edge case flagged (OEChem has no SSSR) |
| 10 | `oe_ring_bond_count` | Number of bonds that are part of a ring | **Yes** — OEChem's graph definition: a bond is cyclic iff removing it does not disconnect the molecule | count `bond.IsInRing()` | RDKit, **BSD-3** | **high** — the same number, not a look-alike |
| 11 | `oe_longest_unbranched_chain` | Length of longest unbranched heavy-atom chain | **Yes, but self-inconsistent** — atoms (not bonds), non-ring, "max two connections to other heavy **chain** atoms" (function page) vs "to other heavy atoms" (FILTER page) | largest connected component of the non-ring heavy-atom subgraph after deleting in-subgraph degree ≥ 3 atoms | RDKit, **BSD-3** | **medium** — two OpenEye pages disagree; reading must be logged |
| 12 | `oe_halide_fraction` | **Fraction of heavy atoms that are halogens** | **Yes, and it contradicts the paper** — "**percent of molecular weight** from halides" | Σ(mass of F/Cl/Br/I) / `Descriptors.MolWt` | RDKit, **BSD-3** | **high** on formula; a spec decision to record |
| 13 | `oe_unspecified_bond_stereo_count` | Double bonds with unassigned E/Z | **Yes** — perceive potentially-stereogenic bonds (`OEPerceiveChiral`), count those lacking `HasStereoSpecified` | `FindPotentialStereo`, filter `Bond_Double` + `Unspecified` | RDKit, **BSD-3** | **medium** — RDKit calls the API "somewhat experimental"; candidate sets may differ |
| 14 | `oe_anionic_carbon_count` | **Formally negatively-charged carbon atoms** | **Yes, and it contradicts the paper** — "an **aromatic** carbon that has negative formal charge" | count `C` and `GetIsAromatic()` and `GetFormalCharge() < 0` | RDKit, **BSD-3** | **high** on formula; a spec decision to record |
| 15 | `oe_net_charge_neutral_ph` | Net formal charge after neutral-pH (7.4) protonation | **Partial** — rule-based, single state, pH 7.4, no enumeration (**so: integer**). The **rules themselves are [not documented]** | Dimorphite-DL at pH 7.4 → one dominant state → `Chem.GetFormalCharge` | **Dimorphite-DL, Apache-2.0** + RDKit BSD-3 | **low** — same kind of estimator, different rule set, nothing to align to |

**Count: 13 of 15 have an authoritative definition precise enough to implement unambiguously**
(rows 5–14, plus rows 1, 2 and 4 at the index level). The two that do not are **row 3**
(`oe_symmetry_complexity`, where no published formula exists and Bertz's symmetry correction is
reconstructed) and **row 15** (`oe_net_charge_neutral_ph`, where the pH rules are withheld). Row 1
has a settled *index* but an inferred *entry point*.

---

## 5. What already exists open

### 5.1 Verdict first

**No new library needs to be adopted beyond one already vetted.** RDKit (**BSD-3**, already a
dependency, already running over the 1 M pool) plus Dimorphite-DL (**Apache-2.0**) covers all 15.
Every other candidate #18 named was checked and rejected — and in two cases for a stronger reason
than "redundant": **CDK does not implement Bertz CT at all**, and **mordred's `BertzCT` is a
one-line RDKit passthrough**. Neither would have added a second opinion even if adopted.

**Compatibility with `scripts/pool/properties.py`.** Every proposal in §2–§4 is a plain
`mol -> float` getter over an RDKit `Mol`, which is exactly the shape that module's `_SPEC` table
and `_safe` nan-wrapper already take, so 14 of the 15 would drop into the existing spec as new rows
with no structural change. Three practical notes: the four complexity properties should share one
`BertzCT`-style pass rather than calling it four times (§2.3), since the pass cost is 0.245
ms/molecule and the pool is 1 M molecules; `oe_net_charge_neutral_ph` is the one exception, because
Dimorphite-DL is SMILES-in/SMILES-out (§3.10) and so needs a separate stage rather than a getter;
and the aromaticity-model choice (§5.3) must be set once, globally, not per property, or the five
aromaticity-dependent rows will disagree with each other.

### 5.2 The candidates, checked

Licences below were read from the **actual LICENSE/COPYING file** in each repository, not from a
badge. Note two filename traps: CDK's is `LICENSE.txt` (plain `LICENSE` 404s) and Dimorphite-DL's
is `LICENSE.md`.

| Candidate | Licence (from the actual LICENSE file) | Linux/WSL2 | Install | Latest / maintained? | Verdict here |
|---|---|---|---|---|---|
| **RDKit** | **BSD-3-Clause** — [license.txt](https://raw.githubusercontent.com/rdkit/rdkit/master/license.txt) | yes (and native Windows) | `pip install rdkit` / conda-forge | active | **Adopt.** Already the dependency; covers 14 of 15 |
| **Dimorphite-DL** | **Apache-2.0** — [LICENSE.md](https://raw.githubusercontent.com/durrantlab/dimorphite_dl/main/LICENSE.md) | yes, pure Python | `pip install dimorphite_dl` | **2.1.0, 2026-10-02** | **Adopt for row 15 only.** The one property RDKit cannot do |
| **CDK** (Chemistry Development Kit) | **LGPL-2.1-or-later** — [LICENSE.txt](https://raw.githubusercontent.com/cdk/cdk/main/LICENSE.txt) | yes, but **needs a JVM** | Maven `cdk-bundle:2.13` | 2.13, 2026-08-18; very active | **Reject.** **CDK has no Bertz CT at all** (see below), and its two complexity descriptors are reimplemented in pure Python by mordred |
| **CDK-pywrapper** | **MIT** | yes | `pip install CDK-pywrapper` | 1.0.0, 2026-07-16 | **Reject.** Downloads a JRE at first run and shells out to a subprocess per batch |
| **mordred** (upstream) | **BSD-3-Clause** — [LICENSE](https://raw.githubusercontent.com/mordred-descriptor/mordred/master/LICENSE) | yes, pure Python | `pip install mordred` | **dead: 1.2.0, 2019-06-05**, 55 open issues | **Reject** — and do not install it; it breaks on numpy ≥ 1.24 / 2.x |
| **mordredcommunity** (the live fork) | **BSD-3-Clause** | yes, pure Python | `pip install mordredcommunity` (import name is still `mordred`) | 2.0.7, 2026-01-22; Python 3.9–3.14 | **Reject for these 15** — its `BertzCT` is a one-line RDKit passthrough. Keep in mind only if `fragCpx`/`fMF` are ever wanted |
| **ODDT** (Open Drug Discovery Toolkit) | **BSD-3-Clause** — [LICENSE](https://raw.githubusercontent.com/oddt/oddt/master/LICENSE) | yes, pure Python | `pip install oddt` ships **2019 code**; git master is current | PyPI 0.7, 2019-12-23; commits 2026-10 | **Reject.** It exposes **no molecular descriptors at all** — only protein–ligand scoring descriptors |
| **Open Babel** | **GPL-2.0-only** — [COPYING](https://raw.githubusercontent.com/openbabel/openbabel/master/COPYING) | yes (and native Windows) | `pip install openbabel` (manylinux wheels since 3.2.0) | 3.2.1, 2026-07-11 | **Reject.** No complexity descriptor; its 25 documented descriptors contain none. Its `-p` pH model is far weaker than Dimorphite-DL's (§3.10) |

**[FACT] CDK does not implement Bertz CT.** This is worth stating plainly because #18 asked about
"CDK complexity descriptors" as a candidate. Verified three ways: the 54 classes under
`org.openscience.cdk.qsar.descriptors.molecular` contain no Bertz entry; the Javadoc URLs
`BertzCTDescriptor.html`, `BertzCT.html` and `ComplexityDescriptor.html` all return **404** while a
control (`FMFDescriptor.html`) returns 200; and CDK-pywrapper's full 288-descriptor manifest has no
`bertz` match. CDK's two actual complexity descriptors are different quantities:

- **`FragmentComplexityDescriptor`** (output `fragC`) — **[FACT]**, Javadoc verbatim: *"The
  complexity is defined as [Nilakantan, R. et. al., Journal of chemical information and modeling,
  2006, 46]: `C = abs(B^2 - A^2 + A) + H/100` where C = complexity, A = number of non-hydrogen
  atoms, B = number of bonds and H = number of heteroatoms."* An algebraic size/branching formula —
  **not** an information-theoretic index, and nothing to do with Bertz.
- **`FMFDescriptor`** (output `FMF`) — **[FACT]** *"the ratio of heavy atoms in the framework to the
  total number of heavy atoms in the molecule"* (Murcko framework fraction), citing Yang et al.,
  *J. Med. Chem.* 2010, DOI [10.1021/jm1008456](https://doi.org/10.1021/jm1008456).

Neither is a candidate for any of the 15, so **the JVM is avoidable entirely.**

**[FACT] mordred adds nothing over RDKit for Bertz.** `mordred.BertzCT`'s own docstring is *"Bertz
CT descriptor (rdkit wrapper)"* and its body is `return float(RDKit.BertzCT(self.mol, dMat=D))`. So
there is no second independent open implementation of the Bertz index to cross-check RDKit against —
**RDKit's is the only one**, which is itself a fact worth recording, since it removes the obvious
"compare two open implementations" validation route.

**[FACT]** RDKit's `rdkit.Chem.GraphDescriptors` exposes **22** topological descriptors
(`BertzCT`, `BalabanJ`, `Ipc`, `AvgIpc`, `HallKierAlpha`, `Kappa1-3`, `Chi0/1/0v/1v/2v/3v/4v`,
`Chi0n-Chi4n` and two helpers), and **`BertzCT` is the only one it frames as complexity**. The
others are already in `properties.py` as part of the 101.

**Licence disqualifications: none.** Every candidate examined is BSD-3, MIT, Apache-2.0, Unlicense,
LGPL-2.1 or GPL-2.0 — all free/open, all redistributable, and **no non-commercial-only,
academic-only or "research use only" clause appears in any of the five LICENSE files read.** That is
the failure mode the project's constraint guards against, and nothing tripped it.

Two licence notes to record anyway:
- **Open Babel is GPL-2.0-*only*, i.e. strong copyleft**, not LGPL. Linking it into distributed code
  would make the combined work GPL-2.0. For a public repo that is a compatibility decision rather
  than a blocker — but it is cleanly avoided here, since Open Babel contributes no complexity
  descriptor and Dimorphite-DL (Apache-2.0) is the better protonation tool anyway.
- **CDK's README contradicts its own LICENSE file** (README says "LGPL v2"; `LICENSE.txt` is
  2.1, and per-file headers add the "or later" grant). Trust the file. Moot here, since CDK is
  rejected.

By contrast, the thing being replaced — OpenEye — *is* the academic-only/commercial case, which is
precisely why this ticket exists.

### 5.3 The genuinely unmeasured risk: aromaticity perception

Five of the 15 (`oe_aromatic_atom_count`, `oe_aromatic_bond_count`, `oe_aromatic_ring_count`,
`oe_anionic_carbon_count`, and indirectly `oe_molecular_complexity` via its aromatic-bond rule)
depend on *which atoms a toolkit calls aromatic*. This is not a settled question between toolkits.

**[FACT]** The **RDKit Book**'s Aromaticity section (<https://www.rdkit.org/docs/RDKit_Book.html>)
states that since no single definition is agreed upon "it's necessary to pick something arbitrary
and stick to it"; that an aromatic bond must join aromatic atoms but a bond between aromatic atoms
need not be aromatic; and that in the default RDKIT model a *fused ring system* can be aromatic even
when its individual rings are not, with **azulene** as the worked example. Most pointedly, it states
that RDKit's **MDL** model "isn't well documented (at least not publicly)" and that RDKit's
implementation was built by **attempting to reproduce the behaviour described in the OEChem
documentation** — with **no claim of exact compatibility**. OEChem is the only other toolkit the
section names.

**[FACT]** OpenEye independently ships five models and says they "define aromaticity rules
differently" (§3.2).

**[not documented] / [NOT FOUND]** No published study reports how many molecules in a large set get
a *different aromatic-atom or aromatic-ring count* under RDKit vs OpenEye perception. Searched: the
RDKit docs and blog, Greg Landrum's and Pat Walters' blogs, iwatobipen, *J. Cheminformatics*.
The two nearest published artifacts:

- **[FACT]** **Sayle, "Cheminformatics toolkits: a personal perspective", 1st RDKit UGM, London,
  4 Oct 2012** (<https://www.rdkit.org/UGM/2012/Sayle_RDKitPerspective.pdf>) contains a
  cross-toolkit table of **π-electrons contributed per atom type** to the Hückel 4n+2 count, with
  rows for MDL, Tripos, Merck, Daylight, **OEChem**, **RDKit**, ChemAxon, OpenBabel, Indigo, CDK
  and Derwent. This is the best published *model-level* OpenEye-vs-RDKit aromaticity comparison
  that exists. (The author was at OpenEye 2001–2010.) **Caveat: the cell values do not survive text
  extraction cleanly — read the slide visually before quoting any individual entry.**
- **[FACT]** **O'Boyle, Mayfield, Sayle, "A de facto standard or a free-for-all? A benchmark for
  reading SMILES", 256th ACS National Meeting, Aug 2018**
  (<https://www.nextmovesoftware.com/talks/OBoyle_SmilesBenchmark_ACS_201808.pdf>, data at
  <https://github.com/nextmovesoftware/smilesreading>) tested 13 toolkits including **OEChem and
  RDKit** over **47,464 ring systems from ChEMBL23**, and both scored **0 kekulization failures and
  0 differing hydrogen counts** against CDK as reference. **But the methodology deliberately
  sidesteps aromaticity**, comparing per-atom hydrogen counts precisely because "the hydrogen count
  is independent of the specific Kekulé form". So it is strong evidence the two toolkits read the
  same structures, and **no** evidence they label the same atoms aromatic.

**[INFER] What this means for the five properties.** The underlying *structures* agree (the 2018
benchmark), so disagreements are confined to labelling, and for ordinary benzenoid and
five-/six-membered heteroaromatic rings — the overwhelming majority of a ZINC drug-like pool — all
models agree. Expect divergence in the known-hard cases: azulene-type fused systems aromatic only
as a whole, quinonoid and exocyclic-double-bond rings, tautomer-dependent rings, and rings mixing
aromatic and non-aromatic carbons. **The honest statement is that the divergence rate is unknown
and cannot be measured here**, since measuring it requires the toolkit that is unavailable. Choose
RDKit's default (`AROMATICITY_DEFAULT`/RDKIT) rather than its MDL model, on the grounds that the
MDL model is itself admittedly reverse-engineered second-hand **[INFER]**, and record the choice.

---

## 6. Has anyone published an OpenEye→RDKit descriptor correspondence?

**No. [NOT FOUND]** — searched for papers, preprints, blog posts by recognised practitioners,
GitHub repos and notebooks mapping OEChem / MolProp TK / QUACPAC descriptors onto RDKit
equivalents. The nearest things, none of which is a descriptor crosswalk:

- **[FACT]** The **Chemistry Toolkit Rosetta Wiki** (<https://ctr.fandom.com/wiki/Chemistry_Toolkit_Rosetta_Wiki>)
  is a cross-toolkit cookbook covering OEChem, RDKit and CDK — but at the level of *tasks* (read a
  file, find rings, compute a fingerprint), not descriptor-value correspondence.
- **[FACT]** `chemfp` provides a common molecule-I/O API across OEChem, RDKit and Open Babel, and
  its docs explicitly say it will *not* gain a common molecule API
  (<https://chemfp.readthedocs.io/en/latest/toolkit.html>).
- **[FACT]** `oefp` (<https://pypi.org/project/oefp/>) generates RDKit-compatible Morgan and
  Atom-Pair **fingerprints** from OpenEye molecules — fingerprints only.
- **[NOT FOUND]** No published reimplementation of OpenEye's specific complexity composite, and no
  published study comparing RDKit `BertzCT` values against OpenEye's on any dataset.

**So this document is the mapping.** It is original work, not a literature lookup, and should be
cited as such — including its uncertainty.

---

## 7. What this means for #16

[#16](https://github.com/zhipengzhu1-dotcom/10-09-2026-Small-Molecule-Design-with-Synthetic-Task-Scaling/issues/16)
found the Tier-1 **integer** objective pool starved: about 5 usable properties after the σ ≥ 2.5
gate and #7's |ρ| > 0.95 collapse, all of them size-like counts. The hope was that the `oe_*`
properties, being mostly *non-size* integers, might repair it.

**Everything in this section is a prediction, not a measurement.** Actually computing σ, ρ and
quantiles over the 1 M pool is the follow-on `wayfinder:task`, not this ticket. The predictions
below are anchored on **measured** σ values for RDKit near-analogues already in
`caches/tier1-pool/sigma_cache.json` (ZINC20, MW 300–450, n = 1,000,000, RDKit 2026.09.1).

### 7.1 The gate that matters

**[FACT]** `caches/tier1-pool/objective_pool_gates.json` records the rule as *"integer properties
with sigma_y >= gate"*. The σ gate applies **to integer properties only**; continuous ones are not
σ-gated. So the 15 split cleanly:

- **5 are continuous** — the 4 complexity properties and `oe_halide_fraction`. They join the
  continuous pool without facing the gate.
- **10 are integer or boolean** — and every one of them faces σ ≥ 2.5.

### 7.2 Why most of the 10 will fail, with the measured anchors

The σ ≥ 2.5 gate is **absolute, in each property's own natural units**. That is why the 7 survivors
at gate 2.5 are exactly the large-magnitude counts (`num_valence_electrons` σ = 15.6, `atom_count_H`
5.44, `num_bonds` 3.70, `heavy_atom_count` 3.11, `atom_count_C` 3.13, plus `num_tautomers` and
`num_stereoisomers`). A property whose whole range is 0–5 *cannot* have σ ≥ 2.5 unless it is
bimodal at the extremes. Most `oe_*` integers are small-range counts.

| Property | Measured anchor | σ prediction | Clears 2.5? |
|---|---|---|---|
| `oe_aromatic_atom_count` | `num_aromatic_rings` σ **0.929**, p5 = 1, p95 = 4 → ×≈5.5 atoms/ring | **≈ 4–5.5** | **likely yes** |
| `oe_aromatic_bond_count` | as above; aromatic bonds ≈ aromatic atoms + fused shared bonds | **≈ 4–5.5** | **likely yes** |
| `oe_ring_bond_count` | `ring_count` σ **0.934** → ×≈5.5 bonds/ring | **≈ 4–5** | **likely yes** |
| `oe_longest_unbranched_chain` | `MAX_UNBRANCHED` default 13; drug-like tails run 2–5 atoms | ≈ 1.5–2.0 | borderline, probably no |
| `oe_aromatic_ring_count` | `num_aromatic_rings` σ **0.929** (same quantity) | ≈ 0.93 | no |
| `oe_ring_system_count` | `ring_count` σ **0.934**, and systems ≤ rings | < 0.93 | no |
| `oe_net_charge_neutral_ph` | `formal_charge` σ **0.049** (pool is drawn near-neutral); pH 7.4 adds real spread via carboxylates and amines | ≈ 0.4–0.8 | no |
| `oe_unspecified_bond_stereo_count` | `num_unspecified_atom_stereo_centers` σ **0.057**, mean 0.002 — ZINC SMILES are essentially fully specified | ≈ 0.05 | no (near-degenerate) |
| `oe_is_macrocycle` | boolean, and macrocycles are rare at MW 300–450 | ≈ 0.05 | no (near-degenerate) |
| `oe_anionic_carbon_count` | aromatic carbanions essentially absent from purchasable space (§3.8) | ≈ 0 | no (degenerate) |

### 7.3 The number #16 asked for

**About 3 of the 15 look like plausibly usable integer objectives with meaningful variance** —
`oe_aromatic_atom_count`, `oe_aromatic_bond_count`, `oe_ring_bond_count`.

**But they collapse.** **[INFER]** Aromatic atom count and aromatic bond count are near-identical
by construction (an aromatic ring of *k* atoms contributes *k* atoms and *k* bonds; they differ
only by fused shared bonds), so their Spearman ρ will be ≈ 0.99 and #7's |ρ| > 0.95 rule deletes
one. Ring bond count is a third view of ring content and correlates with both, and with
`heavy_atom_count` — so it is partly size-like, the very thing #16 is trying to escape.

**Net expected gain: 1, at most 2, new integer objectives**, and the one that is clearly worth
having is an **"aromatic content" axis** — which would be the first *non-size* integer objective to
survive the gates. Qualitatively valuable, quantitatively small.

**On the continuous side the gain is also smaller than it looks.** Per §2.5,
`oe_molecular_complexity` implemented as `BertzCT` is **numerically identical to the pool's existing
`bertz_ct`** (ρ = 1.0 by construction), and `oe_connective_complexity` tracks it above 0.95. So of
5 continuous additions, **3 are new**: `oe_elemental_complexity`, `oe_symmetry_complexity` (the only
symmetry-sensitive descriptor anywhere in the 116) and `oe_halide_fraction`. The continuous pool
already has 23 usable members, so 3 more is a marginal improvement to a part that is not broken.

### 7.4 What #16 should take from this

1. **Reimplementing the 15 does not repair the integer pool.** It takes it from ~5 to ~6–7 usable
   objectives, not to ~10. #16's direction — re-weight toward the continuous pool, and/or collapse
   the size cluster — **stands on its own merits** and should not be deferred waiting for the 15.
2. **But it does buy one thing nothing else does:** a non-size integer axis (aromatic content).
   If #16's worry is that "a large share of tasks would reduce to *make the molecule bigger*",
   adding one orthogonal integer objective is a disproportionately useful repair relative to its
   size.
3. **The real diagnosis is the gate, not the pool.** σ ≥ 2.5 in natural units is **unit-dependent**:
   it systematically excludes every small-range count regardless of how informative that count is.
   `num_aromatic_rings` (σ 0.93, p5 = 1, p95 = 4, max 8) is a perfectly good optimisation target
   that spans a useful range — it fails only because the threshold is absolute. **[INFER]** A gate
   expressed on the *achievable range* (e.g. p95 − p5 ≥ 3 distinct attainable values) rather than on
   σ in natural units would admit far more of the integer pool, and is worth considering as #16's
   decision point 1 or 2 rather than re-weighting away from integers wholesale. This is a question
   #16 can now ask with the numbers in hand.
4. **Fidelity bookkeeping.** Adopting the 15 means logging, under map constraint 3: 15 open
   look-alikes unvalidatable against the original; two deliberate departures from Table A4's own
   descriptions (§3.7, §3.8); one departure from its word "fused" (§3.4); one choice between two
   contradictory OpenEye pages (§3.6); one reconstructed formula (§2.2); and one rule-set
   substitution where the vendor's rules are withheld (§3.10).

---

## 8. Open questions and what could not be verified

- **Bertz 1981 itself** — JACS, paywalled. The formulas in §2.2 are reconstructed from RDKit's
  implementation (which cites it) and verified algebraically, **not** read from the paper. If the
  PDF becomes available, check the sign and scaling of the symmetry correction and whether Bertz
  intends the hydrogen-suppressed graph (RDKit uses it; OpenEye **[not documented]**).
- **Ritchie & Macdonald 2009's own wording** — ScienceDirect HTTP 403, no open copy. §3.1's
  definition is quoted *as OpenEye attributes it*; whether it is verbatim or an OpenEye paraphrase
  is unverified.
- **Which OpenEye complexity entry point `oe_molecular_complexity` is** — four candidates, and the
  paper does not say. §2.4(3) argues for `OEDetermineMolecularComplexity` on [INFER] grounds only.
- **What `OEDetermineSymmetryComplexity` actually returns** — no formula is published anywhere. The
  §2.2 reconstruction is the weakest link in the complexity family.
- **OpenEye's pKa rule set** for `OESetNeutralpHModel` — the only genuinely withheld *content*
  among the 15.
- **Which aromaticity model the paper used**, and the rate at which RDKit and OpenEye disagree on
  aromatic-atom counts. The second is unmeasurable here by construction (§5.3) and **nobody has
  published it**.
- **`oe_longest_unbranched_chain`'s branch-point rule** — two OpenEye pages give two readings
  (§3.6). The function page's worked examples, which would settle it, are images.
- **Whether OpenEye's "percent of molecular weight" for `oe_halide_fraction`** means 0–1 or 0–100,
  and whether its molecular weight includes hydrogens.
- **No cross-check on `BertzCT` exists.** RDKit holds the only open implementation of the Bertz
  index (§2.3), and its own values changed incompatibly at `BertzCT.version 2.0.0`, so neither a
  second open tool nor the pre-2.0 literature can corroborate it.
- **Dimorphite-DL's reduce-to-one-state rule is unspecified.** The 65% figure (§3.10) says that for
  about a third of molecules it returns several states at pH 7.4. Which one to keep — most
  populated, lowest absolute charge, first returned — is a design decision this ticket does not
  make, and it changes `oe_net_charge_neutral_ph` values directly.
- **Every σ prediction in §7** is inferred from measured analogues, not measured. The follow-on
  ticket should compute all 15 over the existing 1 M pool using #15's pass and replace §7's table
  with real numbers — and should measure ρ against `bertz_ct` and `heavy_atom_count` first, since
  §2.5 and §7.3 predict the collapses that decide whether the exercise is worth finishing.
- **`scripts/pool/properties.py:4`** asserts the 15 are "gated, out of scope". If #16 adopts the
  look-alikes, that header comment and the module's 101-property framing need updating — flagged in
  #18, not fixed here.

---

*Written 2026-10-11. Primary sources are linked inline throughout. OpenEye documentation URLs were
read without a licence (the docs site is public); the software itself was never run, here or
anywhere in this project. Package versions and vendor doc pages drift — the OpenEye pages read here
were "Last updated on Aug 12, 2026" and describe Toolkits 2026.1.0.*

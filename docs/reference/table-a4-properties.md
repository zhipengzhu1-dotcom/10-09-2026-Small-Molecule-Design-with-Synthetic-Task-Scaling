# Table A4 — the 116 molecular properties of the Tier-1 environment

Extracted verbatim from `docs/reference/paper-2609.04735-fulltext.txt`, lines 2176-2879
(table caption at 2176, body 2178-2879, terminated by the `Prompt/Response 0:` block at 2880).
Group names are carried forward onto every row; the paper prints each only on its group's first row.

The caption reads: *"The 116 molecular properties presented to the model in the Tier-1
molecular-optimization environment (as optimization targets and constraints), grouped by family:
101 computed with RDKit and 15 with OpenEye. Property names are the identifiers shown in the prompt.
Most are scalar targets; `scaffold` is a BRICS-substructure constraint (a string) and `oe_is_macrocycle`
is a boolean flag."*

`Type` is **inferred**, not stated by the paper, except for `scaffold` (string) and `oe_is_macrocycle`
(boolean), which the caption names explicitly. A trailing `?` marks a genuine uncertainty.

## The table

| Group | Property | Description | Type |
| --- | --- | --- | --- |
| Size / physico. | `molecular_weight` | Average molecular weight in Daltons (Da) | continuous |
| Size / physico. | `exact_molecular_weight` | Monoisotopic (exact) molecular weight in Da | continuous |
| Size / physico. | `heavy_atom_molecular_weight` | Average molecular weight ignoring hydrogens | continuous |
| Size / physico. | `heavy_atom_count` | Number of heavy (non-hydrogen) atoms | integer |
| Size / physico. | `num_heteroatoms` | Number of heteroatoms (non-carbon atoms) | integer |
| Size / physico. | `tpsa` | Topological polar surface area in Å2 | continuous |
| Size / physico. | `logp` | Octanol/water partition coefficient (Crippen LogP) | continuous |
| Size / physico. | `molar_refractivity` | Crippen molar refractivity | continuous |
| Size / physico. | `labute_asa` | Labute approximate accessible surface area in Å2 | continuous |
| Size / physico. | `qed` | Quantitative estimate of drug-likeness (QED) score | continuous |
| Size / physico. | `qed_alerts` | Number of QED structural alerts matched | integer |
| Size / physico. | `fraction_csp3` | Fraction of carbons that are sp3-hybridized | continuous |
| H-bond / charge | `hbd` | Number of hydrogen bond donors (Lipinski definition) | integer |
| H-bond / charge | `num_h_acceptors` | Number of hydrogen bond acceptors | integer |
| H-bond / charge | `num_lipinski_h_donors` | Hydrogen bond donors, Lipinski N–H  +  O–H definition | integer |
| H-bond / charge | `num_lipinski_h_acceptors` | Hydrogen bond acceptors, Lipinski all-N  +  O definition | integer |
| H-bond / charge | `nhoh_count` | Number of implicit hydrogens attached to N and O atoms | integer |
| H-bond / charge | `nocount` | Number of nitrogen and oxygen atoms | integer |
| H-bond / charge | `formal_charge` | Net formal charge of the molecule | integer |
| H-bond / charge | `num_valence_electrons` | Number of valence electrons | integer |
| H-bond / charge | `num_radical_electrons` | Number of radical electrons | integer |
| H-bond / charge | `max_partial_charge` | Maximum Gasteiger partial charge over all atoms | continuous |
| H-bond / charge | `min_partial_charge` | Minimum Gasteiger partial charge over all atoms | continuous |
| H-bond / charge | `max_estate_index` | Maximum electrotopological-state (E-state) index | continuous |
| H-bond / charge | `min_estate_index` | Minimum electrotopological-state (E-state) index | continuous |
| Bond / stereo | `num_bonds` | Total number of bonds | integer |
| Bond / stereo | `num_rotatable_bonds` | Number of rotatable bonds | integer |
| Bond / stereo | `num_amide_bonds` | Number of amide bonds | integer |
| Bond / stereo | `num_brics_bonds` | Number of BRICS-cleavable bonds | integer |
| Bond / stereo | `scaffold` | Random BRICS-derived scaffold substructure (used as a structural constraint) | string |
| Bond / stereo | `num_fragments` | Number of disconnected fragments (components) | integer |
| Bond / stereo | `num_tautomers` | Number of tautomers enumerated by RDKit | integer |
| Bond / stereo | `num_atom_stereo_centers` | Number of atom stereocenters | integer |
| Bond / stereo | `num_unspecified_atom_stereo_centers` | Number of atom stereocenters with unassigned configuration | integer |
| Bond / stereo | `num_stereoisomers` | Number of stereoisomers implied by unspecified stereocenters | integer |
| Atom counts | `atom_count_C` | Number of carbon (C) atoms | integer |
| Atom counts | `atom_count_H` | Number of hydrogen (H) atoms (implicit  +  explicit) | integer |
| Atom counts | `atom_count_N` | Number of nitrogen (N) atoms | integer |
| Atom counts | `atom_count_O` | Number of oxygen (O) atoms | integer |
| Atom counts | `atom_count_S` | Number of sulfur (S) atoms | integer |
| Atom counts | `atom_count_F` | Number of fluorine (F) atoms | integer |
| Atom counts | `atom_count_Cl` | Number of chlorine (Cl) atoms | integer |
| Atom counts | `atom_count_Br` | Number of bromine (Br) atoms | integer |
| Atom counts | `atom_count_P` | Number of phosphorus (P) atoms | integer |
| Atom counts | `atom_count_I` | Number of iodine (I) atoms | integer |
| Atom counts | `num_leadopt_disallowed_atoms` | Number of atoms whose element is disallowed for lead optimization | integer |
| Ring counts | `ring_count` | Total number of rings | integer |
| Ring counts | `num_aromatic_rings` | Number of aromatic rings | integer |
| Ring counts | `num_aliphatic_rings` | Number of aliphatic (non-aromatic) rings | integer |
| Ring counts | `num_saturated_rings` | Number of saturated rings | integer |
| Ring counts | `num_heterocycles` | Number of rings containing at least one heteroatom | integer |
| Ring counts | `num_aromatic_heterocycles` | Number of aromatic rings with at least one heteroatom | integer |
| Ring counts | `num_aromatic_carbocycles` | Number of all-carbon aromatic rings | integer |
| Ring counts | `num_saturated_heterocycles` | Number of saturated rings with at least one heteroatom | integer |
| Ring counts | `numaliphaticcarbocycles` | Number of aliphatic carbocycles | integer |
| Ring counts | `numaliphaticheterocycles` | Number of aliphatic heterocycles | integer |
| Ring counts | `numsaturatedcarbocycles` | Number of saturated carbocycles | integer |
| Ring counts | `num_spiro_atoms` | Number of spiro atoms (single shared ring atom) | integer |
| Ring counts | `num_bridgehead_atoms` | Number of bridgehead atoms (rings sharing \geq 2 bonds) | integer |
| Topological | `bertz_ct` | Bertz molecular complexity index | continuous |
| Topological | `balaban_j` | Balaban’s J topological connectivity index | continuous |
| Topological | `hall_kier_alpha` | Hall–Kier alpha flexibility index | continuous |
| Topological | `kappa1` | First Hall–Kier kappa molecular shape index | continuous |
| Topological | `kappa2` | Second Hall–Kier kappa molecular shape index | continuous |
| Topological | `kappa3` | Third Hall–Kier kappa molecular shape index | continuous |
| Topological | `chi0` | Zeroth-order (simple) molecular connectivity index | continuous |
| Topological | `chi1` | First-order (simple) molecular connectivity index | continuous |
| Topological | `chi0v` | Valence-corrected zeroth-order connectivity index | continuous |
| Topological | `chi1v` | Valence-corrected first-order connectivity index | continuous |
| Topological | `fp_density_morgan1` | Radius-1 Morgan fingerprint bit density per heavy atom | continuous |
| Topological | `fp_density_morgan2` | Radius-2 Morgan fingerprint bit density per heavy atom | continuous |
| Functional grps. | `fr_benzene` | Number of benzene rings | integer |
| Functional grps. | `fr_halogen` | Number of halogen atoms | integer |
| Functional grps. | `fr_amide` | Number of amide groups | integer |
| Functional grps. | `fr_ketone` | Number of ketone groups | integer |
| Functional grps. | `fr_ester` | Number of ester groups | integer |
| Functional grps. | `fr_ether` | Number of ether oxygens | integer |
| Functional grps. | `fr_aldehyde` | Number of aldehyde groups | integer |
| Functional grps. | `fr_nitrile` | Number of nitrile (cyano) groups | integer |
| Functional grps. | `fr_nitro` | Number of nitro groups | integer |
| Functional grps. | `fr_sulfonamd` | Number of sulfonamide groups | integer |
| Functional grps. | `fr_sulfone` | Number of sulfone groups | integer |
| Functional grps. | `fr_aniline` | Number of aniline (aromatic amine) groups | integer |
| Functional grps. | `fr_pyridine` | Number of pyridine rings | integer |
| Functional grps. | `fr_imidazole` | Number of imidazole rings | integer |
| Functional grps. | `fr_phenol` | Number of phenol groups | integer |
| Functional grps. | `fr_COO` | Number of carboxylic acid groups | integer |
| Functional grps. | `fr_NH2` | Number of primary amine groups | integer |
| Functional grps. | `fr_NH1` | Number of secondary amine groups | integer |
| Functional grps. | `fr_NH0` | Number of tertiary amine groups | integer |
| Functional grps. | `fr_methoxy` | Number of methoxy groups | integer |
| Functional grps. | `fr_furan` | Number of furan rings | integer |
| Functional grps. | `fr_thiophene` | Number of thiophene rings | integer |
| Functional grps. | `fr_piperdine` | Number of piperidine rings | integer |
| Functional grps. | `fr_piperzine` | Number of piperazine rings | integer |
| Functional grps. | `fr_morpholine` | Number of morpholine rings | integer |
| Functional grps. | `fr_urea` | Number of urea groups | integer |
| Functional grps. | `fr_alkyl_halide` | Number of alkyl halide groups | integer |
| Functional grps. | `fr_aryl_methyl` | Number of aryl-methyl groups | integer |
| Functional grps. | `fr_Ar_N` | Number of aromatic nitrogen atoms | integer |
| Functional grps. | `fr_C_O` | Number of carbonyl (C = O) groups | integer |
| OpenEye | `oe_molecular_complexity` | OpenEye molecular complexity index | continuous |
| OpenEye | `oe_connective_complexity` | Connectivity component of OpenEye molecular complexity | continuous |
| OpenEye | `oe_symmetry_complexity` | Symmetry component of OpenEye molecular complexity | continuous |
| OpenEye | `oe_elemental_complexity` | Elemental-diversity component of OpenEye molecular complexity | continuous |
| OpenEye | `oe_aromatic_atom_count` | Number of aromatic atoms | integer |
| OpenEye | `oe_aromatic_bond_count` | Number of aromatic bonds | integer |
| OpenEye | `oe_aromatic_ring_count` | Number of aromatic rings (OpenEye Ritchie definition) | integer |
| OpenEye | `oe_ring_system_count` | Number of distinct (fused) ring systems | integer |
| OpenEye | `oe_is_macrocycle` | Whether the molecule contains a macrocyclic ring ( \geq 10 atoms) | boolean |
| OpenEye | `oe_ring_bond_count` | Number of bonds that are part of a ring | integer |
| OpenEye | `oe_longest_unbranched_chain` | Length of the longest unbranched heavy-atom chain | integer |
| OpenEye | `oe_halide_fraction` | Fraction of heavy atoms that are halogens | continuous |
| OpenEye | `oe_unspecified_bond_stereo_count` | Number of double bonds with unassigned E/Z configuration | integer |
| OpenEye | `oe_anionic_carbon_count` | Number of formally negatively-charged carbon atoms | integer |
| OpenEye | `oe_net_charge_neutral_ph` | Net formal charge after OpenEye neutral-pH (7.4) protonation | integer? |

## Counts

**Total rows extracted: 116** — matches the 116 the caption claims.

| Group | Rows |
| --- | --- |
| Size / physico. | 12 |
| H-bond / charge | 13 |
| Bond / stereo | 10 |
| Atom counts | 11 |
| Ring counts | 13 |
| Topological | 12 |
| Functional grps. | 30 |
| OpenEye | 15 |
| **Total** | **116** |

RDKit families (every group except OpenEye) sum to **101**; OpenEye is **15**.
Both match the caption's "101 computed with RDKit and 15 with OpenEye".

Inferred type distribution:

| Type | Rows |
| --- | --- |
| continuous | 30 |
| integer | 83 |
| string | 1 |
| boolean | 1 |
| integer? | 1 |

### The split that matters: the 101 free RDKit properties

The 15 OpenEye properties are gated (see map issue #1, out of scope pending #5), so the usable
pool is the other 101. Cross-tabulating group against inferred type gives:

| Type | RDKit rows | Reward treatment (Eq A5 / A6) |
| --- | --- | --- |
| integer | **75** | **hard** — 1 or 0, no partial credit |
| continuous | **25** | **soft** — Gaussian partial credit, scale `s` = 0.1 |
| string (`scaffold`) | 1 | the BRICS scaffold constraint itself |
| **Total** | **101** | |

The 25 continuous ones are: the three molecular weights, `tpsa`, `logp`, `molar_refractivity`,
`labute_asa`, `qed`, `fraction_csp3`, the four partial-charge / E-state extrema, and all twelve
Topological indices. Every `fr_*` row is an integer fragment-match count despite the prefix, and
`qed_alerts` is a count.

So **74% of the usable property space yields all-or-nothing constraints** — a much sparser reward
surface than "integer → hard, continuous → soft" suggests on its own. This is the number that
drove the two-pool decision in [#7](https://github.com/zhipengzhu1-dotcom/10-09-2026-Small-Molecule-Design-with-Synthetic-Task-Scaling/issues/7).

## The 15 OpenEye properties

The `OpenEye` group, isolated. These are the 15 the caption attributes to OpenEye; every
identifier in the group carries the `oe_` prefix, and no `oe_`-prefixed identifier appears
outside it.

| # | Property | Description | Type |
| --- | --- | --- | --- |
| 1 | `oe_molecular_complexity` | OpenEye molecular complexity index | continuous |
| 2 | `oe_connective_complexity` | Connectivity component of OpenEye molecular complexity | continuous |
| 3 | `oe_symmetry_complexity` | Symmetry component of OpenEye molecular complexity | continuous |
| 4 | `oe_elemental_complexity` | Elemental-diversity component of OpenEye molecular complexity | continuous |
| 5 | `oe_aromatic_atom_count` | Number of aromatic atoms | integer |
| 6 | `oe_aromatic_bond_count` | Number of aromatic bonds | integer |
| 7 | `oe_aromatic_ring_count` | Number of aromatic rings (OpenEye Ritchie definition) | integer |
| 8 | `oe_ring_system_count` | Number of distinct (fused) ring systems | integer |
| 9 | `oe_is_macrocycle` | Whether the molecule contains a macrocyclic ring ( \geq 10 atoms) | boolean |
| 10 | `oe_ring_bond_count` | Number of bonds that are part of a ring | integer |
| 11 | `oe_longest_unbranched_chain` | Length of the longest unbranched heavy-atom chain | integer |
| 12 | `oe_halide_fraction` | Fraction of heavy atoms that are halogens | continuous |
| 13 | `oe_unspecified_bond_stereo_count` | Number of double bonds with unassigned E/Z configuration | integer |
| 14 | `oe_anionic_carbon_count` | Number of formally negatively-charged carbon atoms | integer |
| 15 | `oe_net_charge_neutral_ph` | Net formal charge after OpenEye neutral-pH (7.4) protonation | integer? |

Bare identifier list:

```
oe_molecular_complexity
oe_connective_complexity
oe_symmetry_complexity
oe_elemental_complexity
oe_aromatic_atom_count
oe_aromatic_bond_count
oe_aromatic_ring_count
oe_ring_system_count
oe_is_macrocycle
oe_ring_bond_count
oe_longest_unbranched_chain
oe_halide_fraction
oe_unspecified_bond_stereo_count
oe_anionic_carbon_count
oe_net_charge_neutral_ph
```

## Notes on the type inference

Relevant because the paper's reward treats integer and boolean constraints as hard (1/0) and
continuous ones as soft (Gaussian partial credit), so a misclassification changes the reward shape.

- **Stated by the paper, not inferred:** `scaffold` = string (a BRICS substructure), `oe_is_macrocycle` = boolean.
- **Continuous despite reading like counts:** `fraction_csp3` and `oe_halide_fraction` are ratios;
  `qed` is a 0-1 desirability score; `fp_density_morgan1`/`fp_density_morgan2` are bits per heavy atom.
- **A count despite its neighbours:** `qed_alerts` is the number of QED structural alerts matched, an integer.
- **All `fr_*` rows are integers** — they are RDKit fragment-match counts, not fractions, despite the `fr_` prefix.
- **Molecular weights are continuous** (`molecular_weight`, `exact_molecular_weight`,
  `heavy_atom_molecular_weight`) while `heavy_atom_count` is an integer.
- **Charge/E-state extrema are continuous:** `max_partial_charge`, `min_partial_charge` (Gasteiger),
  `max_estate_index`, `min_estate_index`. But `formal_charge`, `num_valence_electrons` and
  `num_radical_electrons` are integers.
- **Topological indices are continuous:** `bertz_ct`, `balaban_j`, `hall_kier_alpha` (can be negative),
  `kappa1`-`kappa3`, `chi0`/`chi1`/`chi0v`/`chi1v`.
- **The three OpenEye complexity components** (`oe_connective_complexity`, `oe_symmetry_complexity`,
  `oe_elemental_complexity`) and `oe_molecular_complexity` are real-valued indices.

### Flagged uncertain

- `oe_net_charge_neutral_ph` -> **`integer?`**. "Net formal charge after OpenEye neutral-pH (7.4)
  protonation". Formal charges are integers, so a single assigned protomer gives an integer; but if
  the implementation averages over a protonation-state ensemble at pH 7.4 it would be fractional,
  i.e. continuous. Worth checking against the implementation before wiring the reward.

Everything else is classified without a `?`.

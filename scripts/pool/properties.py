"""The 101 free RDKit properties of Table A4, mapped to RDKit calls.

Table A4 of arXiv:2609.04735 lists 116 properties by their *prompt identifier*; 101 are
computable with RDKit and 15 need OpenEye (gated, out of scope). The paper never states the
RDKit function behind each identifier, so this module is that mapping, inferred from each
identifier's description in docs/reference/table-a4-properties.md.

One of the 101 (``scaffold``) is a string, so 100 are numeric and carry a sigma.

Conventions:
  * ``KIND`` is "integer" (hard constraint, Eq A5) or "continuous" (soft, Gaussian partial
    credit) exactly as Table A4's inferred-type column has it.
  * Every getter returns a float, or nan when RDKit cannot compute it. Nothing raises: the
    per-property non-finite rate is one of the things the pool pass has to measure.
"""

from __future__ import annotations

import math

from rdkit import Chem
from rdkit.Chem import BRICS, Crippen, Descriptors, Fragments, QED, rdMolDescriptors
from rdkit.Chem import EnumerateStereoisomers as _enum_stereo
from rdkit.Chem.MolStandardize import rdMolStandardize

# --- helpers ---------------------------------------------------------------------------------

_TAUTOMER_ENUMERATOR = rdMolStandardize.TautomerEnumerator()
_TAUTOMER_ENUMERATOR.SetMaxTautomers(1000)

# The ten elements Table A4's "Atom counts" group enumerates individually. The paper does not
# define num_leadopt_disallowed_atoms's allowed set [not documented]; taking it to be exactly
# these ten is the reading that makes the group self-consistent.
_LEADOPT_ALLOWED = {"C", "H", "N", "O", "S", "F", "Cl", "Br", "P", "I"}


def _safe(fn):
    """Wrap a getter so an RDKit exception becomes nan rather than killing the pass."""

    def inner(mol):
        try:
            v = fn(mol)
        except Exception:
            return math.nan
        if v is None:
            return math.nan
        try:
            return float(v)
        except (TypeError, ValueError):
            return math.nan

    return inner


def _atom_count(symbol):
    if symbol == "H":
        # implicit + explicit, per Table A4's "(implicit + explicit)"
        def h_count(mol):
            return sum(a.GetTotalNumHs() for a in mol.GetAtoms()) + sum(
                1 for a in mol.GetAtoms() if a.GetSymbol() == "H"
            )

        return h_count
    return lambda mol: sum(1 for a in mol.GetAtoms() if a.GetSymbol() == symbol)


def _n_leadopt_disallowed(mol):
    return sum(1 for a in mol.GetAtoms() if a.GetSymbol() not in _LEADOPT_ALLOWED)


def _qed_alerts(mol):
    return QED.properties(mol).ALERTS


def _num_brics_bonds(mol):
    return len(list(BRICS.FindBRICSBonds(mol)))


def _num_tautomers(mol):
    return len(_TAUTOMER_ENUMERATOR.Enumerate(mol).tautomers)


def _num_atom_stereo_centers(mol):
    Chem.AssignStereochemistry(mol, cleanIt=True, force=True, flagPossibleStereoCenters=True)
    return rdMolDescriptors.CalcNumAtomStereoCenters(mol)


def _num_unspecified_atom_stereo_centers(mol):
    Chem.AssignStereochemistry(mol, cleanIt=True, force=True, flagPossibleStereoCenters=True)
    return rdMolDescriptors.CalcNumUnspecifiedAtomStereoCenters(mol)


def _num_stereoisomers(mol):
    return _enum_stereo.GetStereoisomerCount(mol)


_FRAGMENT_NAMES = (
    "benzene", "halogen", "amide", "ketone", "ester", "ether", "aldehyde", "nitrile",
    "nitro", "sulfonamd", "sulfone", "aniline", "pyridine", "imidazole", "phenol",
    "COO", "NH2", "NH1", "NH0", "methoxy", "furan", "thiophene", "piperdine",
    "piperzine", "morpholine", "urea", "alkyl_halide", "aryl_methyl", "Ar_N", "C_O",
)

_ATOM_SYMBOLS = ("C", "H", "N", "O", "S", "F", "Cl", "Br", "P", "I")

# --- the table -------------------------------------------------------------------------------
# (identifier, group, kind, getter)

_SPEC = [
    # Size / physico. (12)
    ("molecular_weight", "size", "continuous", Descriptors.MolWt),
    ("exact_molecular_weight", "size", "continuous", Descriptors.ExactMolWt),
    ("heavy_atom_molecular_weight", "size", "continuous", Descriptors.HeavyAtomMolWt),
    ("heavy_atom_count", "size", "integer", Descriptors.HeavyAtomCount),
    ("num_heteroatoms", "size", "integer", Descriptors.NumHeteroatoms),
    ("tpsa", "size", "continuous", Descriptors.TPSA),
    ("logp", "size", "continuous", Crippen.MolLogP),
    ("molar_refractivity", "size", "continuous", Crippen.MolMR),
    ("labute_asa", "size", "continuous", Descriptors.LabuteASA),
    ("qed", "size", "continuous", QED.qed),
    ("qed_alerts", "size", "integer", _qed_alerts),
    ("fraction_csp3", "size", "continuous", Descriptors.FractionCSP3),
    # H-bond / charge (13)
    ("hbd", "hbond", "integer", Descriptors.NumHDonors),
    ("num_h_acceptors", "hbond", "integer", Descriptors.NumHAcceptors),
    ("num_lipinski_h_donors", "hbond", "integer", rdMolDescriptors.CalcNumLipinskiHBD),
    ("num_lipinski_h_acceptors", "hbond", "integer", rdMolDescriptors.CalcNumLipinskiHBA),
    ("nhoh_count", "hbond", "integer", Descriptors.NHOHCount),
    ("nocount", "hbond", "integer", Descriptors.NOCount),
    ("formal_charge", "hbond", "integer", Chem.GetFormalCharge),
    ("num_valence_electrons", "hbond", "integer", Descriptors.NumValenceElectrons),
    ("num_radical_electrons", "hbond", "integer", Descriptors.NumRadicalElectrons),
    ("max_partial_charge", "hbond", "continuous", Descriptors.MaxPartialCharge),
    ("min_partial_charge", "hbond", "continuous", Descriptors.MinPartialCharge),
    ("max_estate_index", "hbond", "continuous", Descriptors.MaxEStateIndex),
    ("min_estate_index", "hbond", "continuous", Descriptors.MinEStateIndex),
    # Bond / stereo (10, of which `scaffold` is the string one, handled separately)
    ("num_bonds", "bond", "integer", lambda m: m.GetNumBonds()),
    ("num_rotatable_bonds", "bond", "integer", Descriptors.NumRotatableBonds),
    ("num_amide_bonds", "bond", "integer", rdMolDescriptors.CalcNumAmideBonds),
    ("num_brics_bonds", "bond", "integer", _num_brics_bonds),
    ("num_fragments", "bond", "integer", lambda m: len(Chem.GetMolFrags(m))),
    ("num_tautomers", "bond", "integer", _num_tautomers),
    ("num_atom_stereo_centers", "bond", "integer", _num_atom_stereo_centers),
    (
        "num_unspecified_atom_stereo_centers",
        "bond",
        "integer",
        _num_unspecified_atom_stereo_centers,
    ),
    ("num_stereoisomers", "bond", "integer", _num_stereoisomers),
    # Atom counts (11)
    *[(f"atom_count_{s}", "atoms", "integer", _atom_count(s)) for s in _ATOM_SYMBOLS],
    ("num_leadopt_disallowed_atoms", "atoms", "integer", _n_leadopt_disallowed),
    # Ring counts (13)
    ("ring_count", "rings", "integer", Descriptors.RingCount),
    ("num_aromatic_rings", "rings", "integer", Descriptors.NumAromaticRings),
    ("num_aliphatic_rings", "rings", "integer", Descriptors.NumAliphaticRings),
    ("num_saturated_rings", "rings", "integer", Descriptors.NumSaturatedRings),
    ("num_heterocycles", "rings", "integer", rdMolDescriptors.CalcNumHeterocycles),
    ("num_aromatic_heterocycles", "rings", "integer", Descriptors.NumAromaticHeterocycles),
    ("num_aromatic_carbocycles", "rings", "integer", Descriptors.NumAromaticCarbocycles),
    ("num_saturated_heterocycles", "rings", "integer", Descriptors.NumSaturatedHeterocycles),
    ("numaliphaticcarbocycles", "rings", "integer", Descriptors.NumAliphaticCarbocycles),
    ("numaliphaticheterocycles", "rings", "integer", Descriptors.NumAliphaticHeterocycles),
    ("numsaturatedcarbocycles", "rings", "integer", Descriptors.NumSaturatedCarbocycles),
    ("num_spiro_atoms", "rings", "integer", rdMolDescriptors.CalcNumSpiroAtoms),
    ("num_bridgehead_atoms", "rings", "integer", rdMolDescriptors.CalcNumBridgeheadAtoms),
    # Topological (12)
    ("bertz_ct", "topological", "continuous", Descriptors.BertzCT),
    ("balaban_j", "topological", "continuous", Descriptors.BalabanJ),
    ("hall_kier_alpha", "topological", "continuous", Descriptors.HallKierAlpha),
    ("kappa1", "topological", "continuous", Descriptors.Kappa1),
    ("kappa2", "topological", "continuous", Descriptors.Kappa2),
    ("kappa3", "topological", "continuous", Descriptors.Kappa3),
    ("chi0", "topological", "continuous", Descriptors.Chi0),
    ("chi1", "topological", "continuous", Descriptors.Chi1),
    ("chi0v", "topological", "continuous", Descriptors.Chi0v),
    ("chi1v", "topological", "continuous", Descriptors.Chi1v),
    ("fp_density_morgan1", "topological", "continuous", Descriptors.FpDensityMorgan1),
    ("fp_density_morgan2", "topological", "continuous", Descriptors.FpDensityMorgan2),
    # Functional groups (30) -- every one an rdkit.Chem.Fragments counter
    *[
        (f"fr_{n}", "functional", "integer", getattr(Fragments, f"fr_{n}"))
        for n in _FRAGMENT_NAMES
    ],
]

NAMES = [s[0] for s in _SPEC]
GROUP = {s[0]: s[1] for s in _SPEC}
KIND = {s[0]: s[2] for s in _SPEC}
_GETTERS = [(s[0], _safe(s[3])) for s in _SPEC]

#: `scaffold`, the 101st: a string, so it has no sigma and is not in the numeric table.
STRING_PROPERTY = "scaffold"


def compute(mol):
    """All 100 numeric properties for one molecule, in NAMES order."""
    return [fn(mol) for _, fn in _GETTERS]


def scaffold(mol):
    """Largest BRICS fragment, dummies stripped (issue #7), or "" if decomposition is degenerate."""
    try:
        frags = BRICS.BRICSDecompose(mol, returnMols=False)
    except Exception:
        return ""
    dummy = Chem.MolFromSmarts("[#0]")
    best, best_n = "", -1
    for f in frags:
        m = Chem.MolFromSmiles(f)
        if m is None:
            continue
        stripped = Chem.DeleteSubstructs(m, dummy)
        try:
            Chem.SanitizeMol(stripped)
        except Exception:
            continue
        n = stripped.GetNumHeavyAtoms()
        if n > best_n:
            best, best_n = Chem.MolToSmiles(stripped), n
    return best

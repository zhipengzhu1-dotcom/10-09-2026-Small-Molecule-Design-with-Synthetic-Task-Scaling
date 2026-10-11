"""PROTOTYPE -- throwaway. Property identifier -> natural-language gloss.

Issue #8 renders tasks in the paper's own style ("maximize the primary amine groups",
"sulfone groups > 2") rather than with bare identifiers. The glosses are derived
mechanically from the Description column of docs/reference/table-a4-properties.md:
strip a leading "Number of", lowercase the first word, tidy LaTeX leftovers.

That rule is *validated*, not assumed: it reproduces both glosses in the paper's one
rendered example exactly --
    fr_NH2      -> "primary amine groups"   (paper: "maximize the primary amine groups")
    fr_sulfone  -> "sulfone groups"         (paper: "sulfone groups > 2")
``_OVERRIDES`` only repairs proper nouns the lowercasing rule mangles.
"""

from __future__ import annotations

import re
from pathlib import Path

_TABLE = Path(__file__).resolve().parents[2] / "docs" / "reference" / "table-a4-properties.md"

_ROW = re.compile(r"\|\s*(.+?)\s*\|\s*`(.+?)`\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")

# Proper nouns and acronyms the "lowercase the first letter" rule breaks.
_OVERRIDES = {
    "qed_alerts": "QED structural alerts matched",
    "num_brics_bonds": "BRICS-cleavable bonds",
    "bertz_ct": "Bertz molecular complexity index",
    "balaban_j": "Balaban's J topological connectivity index",
    "hall_kier_alpha": "Hall-Kier alpha flexibility index",
    "kappa1": "first Hall-Kier kappa molecular shape index",
    "kappa2": "second Hall-Kier kappa molecular shape index",
    "kappa3": "third Hall-Kier kappa molecular shape index",
    "molar_refractivity": "Crippen molar refractivity",
    "labute_asa": "Labute approximate accessible surface area",
    "num_bridgehead_atoms": "bridgehead atoms",
    "fr_C_O": "carbonyl (C=O) groups",
    "logp": "octanol/water partition coefficient (LogP)",
    "tpsa": "topological polar surface area (TPSA)",
}


def _tidy(text: str) -> str:
    text = text.replace(" ", " ").replace("–", "-").replace("’", "'")
    text = re.sub(r"\\geq", ">=", text)
    text = re.sub(r"\s*Å2", "", text)  # drop the "Å2" unit suffix
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _derive(description: str) -> str:
    d = _tidy(description)
    d = re.sub(r"^(Number of|Count of|Total number of)\s+", "", d)
    return (d[0].lower() + d[1:]) if d else d


def _load() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in _TABLE.read_text(encoding="utf-8").splitlines():
        m = _ROW.match(line)
        if m:
            out[m.group(2)] = _derive(m.group(3))
    out.update(_OVERRIDES)
    return out


GLOSS = _load()


def gloss(name: str) -> str:
    return GLOSS.get(name, name)

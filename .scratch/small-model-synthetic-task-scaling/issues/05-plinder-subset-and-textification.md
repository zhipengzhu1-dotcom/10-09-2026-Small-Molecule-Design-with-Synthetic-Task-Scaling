# 05 — PLINDER subsetting and binding-context textification without OpenEye

Type: prototype
Status: open
Blocked by: —
Map: [Synthetic Task Scaling at <8B](../map.md)

## Question

How do we build the Tier-2 / evaluation task set from PLINDER, and reproduce the paper's
"textified" binding context using only free tools?

PLINDER is **Apache-2.0 for data and code, no registration, default download ~1.5 GiB** (the
full 2026-09 release is 64 GiB and is not needed). So the paper's structural dataset is fully
available — this ticket is about reproducing its *curation* and *prompt rendering*.

Build a prototype that produces, for a handful of systems, exactly the prompt block the paper
shows, then decide the open questions.

**Filtering** — reproduce the paper's criteria: seed ligand MW 200–600 Da; exclude ions,
cofactors, covalent binders, oligomers and crystallisation artifacts; crystal resolution ≤ 3 Å;
scores computable for the seed ligand; passes **all PoseBusters** validity checks. Drop the
OpenEye `.oedu` criterion (ticket 04). Decide how "cofactor", "covalent binder" and
"crystallisation artifact" are operationalised — the paper names the categories but not the
test, and PLINDER's own annotations may already encode them. **Preserve the train/test split
discipline: Tier-2 tasks come from the official PLINDER train split, evaluation from the
official test split.** Report final counts and compare them to the paper's 999 / 40.

**Textification** — reproduce this block shape verbatim:

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

This needs no OpenEye. Decide the tool — **PLIP**, **ProLIF**, MDAnalysis, or direct RDKit +
geometry — for each of the four components: H-bonds with strength/ideality grading and
water-mediation, steric clashes, **unfilled polar sites with distances** (the hardest one — it
requires finding pocket donors/acceptors that are *not* satisfied by the ligand), and pocket
residues ordered by ligand contact.

Also resolve: how to produce the **atom-map-labelled seed SMILES** (`[CH3:19][C:4](=[O:23])...`)
so that atom numbers in the binding context line up with the SMILES the model is shown — the
labels are what make the context block usable, so a numbering mismatch silently poisons the
whole Tier-2 prompt.

## Answer

<!-- append on resolution -->

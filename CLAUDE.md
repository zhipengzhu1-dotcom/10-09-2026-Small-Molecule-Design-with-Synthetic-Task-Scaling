# LLM Fine Tuning

Reproducing arXiv:2609.04735 ("Training Large Language Models for Small-Molecule Design with
Synthetic Task Scaling") with a **sub-8B model on one RTX 5090**, using only free and open
software. The paper trained a 35B MoE on 32 × B200.

**There is no code yet.** This repo currently holds a wayfinder map and its research. Work is
planning, not building — produce decisions, not deliverables, until the map says otherwise.

## Start here

- **[The map](.scratch/small-model-synthetic-task-scaling/map.md)** — destination, standing
  constraints, known traps, decisions so far, and what is in and out of scope. Read its
  `## Notes` block before choosing any work. Tickets are in
  `.scratch/small-model-synthetic-task-scaling/issues/`.
- **[The paper digest](.scratch/reference/paper-2609.04735-digest.md)** — reward equations,
  Tables A1/A2, task-construction algorithms, both prompt templates, and the inventory of what
  is gated vs. free. **Read this before the full text**; it is the condensed specification.
- **[The paper full text](.scratch/reference/paper-2609.04735-fulltext.txt)** — 3,179 lines.
  Already local; do not re-fetch it, and read it by section rather than whole.
- **Research findings** — `.scratch/research/`: Unsloth RL capability, the open chemistry oracle
  stack, and the ZINC seed source.

## Non-obvious constraints

- **Unsloth Studio cannot do this work.** Its GUI is supervised fine-tuning only. The RL work
  runs through the Unsloth Python library under **WSL2** — vLLM, which GRPO rollouts require,
  does not run on native Windows.
- **ZINC seed structures must never be committed.** ZINC's terms forbid redistributing major
  portions. The repo ships the generation script, ZINC IDs and the σ cache — not the SMILES.
  `.gitignore` enforces this; do not override it.
- The map's **Known traps** section lists the mistakes already paid for (σ caching, tool-call
  penalty warmup units, zero-advantage groups, poisoned pip package names). Read it rather than
  rediscovering them.

## Working agreements

- Download and read primary sources in full before planning from them; do not plan from
  WebFetch summaries. See `.scratch/reference/` for where they land.
- The user is new to machine learning and is not a computational chemist. Name jargon on first
  use, prefer measuring over asserting, and flag genuinely hard parts once rather than letting
  difficulty arrive as a surprise.

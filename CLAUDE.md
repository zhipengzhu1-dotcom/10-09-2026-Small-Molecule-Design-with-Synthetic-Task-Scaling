# LLM Fine Tuning

Reproducing arXiv:2609.04735 ("Training Large Language Models for Small-Molecule Design with
Synthetic Task Scaling") with a **sub-8B model on one RTX 5090**, using only free and open
software. The paper trained a 35B MoE on 32 × B200.

**There is no code yet.** Work is currently planning, not building — produce decisions, not
deliverables, until the map says otherwise.

## Start here

- **The wayfinder map is [issue #1](https://github.com/zhipengzhu1-dotcom/10-09-2026-Small-Molecule-Design-with-Synthetic-Task-Scaling/issues/1)**,
  and its decision tickets are its sub-issues. Read the map's `## Notes` block before choosing
  any work. **The issue tracker is GitHub** — see [`docs/agents/issue-tracker.md`](docs/agents/issue-tracker.md)
  for the wayfinding operations (claim, resolve, frontier query, blocking edges).
- **[The paper digest](docs/reference/paper-2609.04735-digest.md)** — reward equations, Tables
  A1/A2, task-construction algorithms, both prompt templates, and the inventory of what is gated
  vs. free. **Read this before the full text**; it is the condensed specification.
- **[The paper full text](docs/reference/paper-2609.04735-fulltext.txt)** — 3,179 lines. Already
  local; do not re-fetch it, and read it by section rather than whole.
- **Research findings** — [`docs/research/`](docs/research/): Unsloth RL capability, the open
  chemistry oracle stack, and the ZINC seed source.

## Non-obvious constraints

- **Unsloth Studio cannot do this work.** Its GUI is supervised fine-tuning only. The RL work
  runs through the Unsloth Python library under **WSL2** — vLLM, which GRPO rollouts require,
  does not run on native Windows.
- **This repo is public.** Nothing enters git history that cannot be redistributed.
  `.gitignore` mechanically enforces the two live constraints: **ZINC seed structures** (ZINC's
  terms forbid redistributing major portions — ship the script, the IDs and the σ cache, never
  the SMILES) and **publisher-copyright PDFs** (kept in `References/`, which is ignored). The
  arXiv source paper is committed because it is CC BY 4.0. Do not override these.
- The map's **Known traps** section lists the mistakes already paid for (σ caching, tool-call
  penalty warmup units, zero-advantage groups, poisoned pip package names). Read it rather than
  rediscovering them.

## Working agreements

- Download and read primary sources in full before planning from them; do not plan from
  WebFetch summaries. They land in `docs/reference/`.
- The user is new to machine learning and is not a computational chemist. Name jargon on first
  use, prefer measuring over asserting, and flag genuinely hard parts once rather than letting
  difficulty arrive as a surprise.

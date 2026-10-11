# LLM Fine Tuning

Reproducing arXiv:2609.04735 ("Training Large Language Models for Small-Molecule Design with
Synthetic Task Scaling") with a **sub-8B model on one RTX 5090**, using only free and open
software. The paper trained a 35B MoE on 32 × B200.

**There is no code in this repo yet.** Work is currently planning, not building — produce
decisions, not deliverables, until the map says otherwise. A **`wayfinder:task` ticket is the
map saying otherwise**: that type exists to do manual work a decision is blocked on, so
install, run and measure as it asks, and record the result.

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
- **[The Tier-2 docking oracle record](docs/research/tier2-docking-oracle.md)** — the chosen
  oracle (smina/Vinardo `--minimize` on a `ConstrainedEmbed` pose, MCS fallback), its measured
  0.133 s/molecule cost, its failure contract and sign convention. **Read it before quoting a
  docking cost**, including why the 126 s/complex figure does not apply to template docking.
- **[The bring-up record](docs/research/rtx5090-wsl2-grpo-bringup.md)** — the pinned stack that
  works on sm_120, plus measured VRAM, throughput, s/step and KV-cache concurrency. **Read it
  before installing anything or quoting a hardware number**, including why `nvidia-smi` and
  `torch` disagree about free VRAM under WDDM.

## Non-obvious constraints

- **Unsloth Studio cannot do this work.** Its GUI is supervised fine-tuning only. The RL work
  runs through the Unsloth Python library under **WSL2** — vLLM, which GRPO rollouts require,
  does not run on native Windows.
- **Run things in WSL by writing a script to a file and invoking the file:**
  `wsl.exe -d Ubuntu-24.04 -- bash /mnt/c/.../script.sh`. PowerShell expands `$var` and pipes
  before bash sees them, and `head`/`tail`/`grep` are not cmdlets, so inline one-liners fail in
  ways that read like bash errors. The GRPO venv is `~/.venvs/stsc`; `sudo` needs a password
  there, so reach for `uv`, which has covered every install so far (it lives at
  `~/.local/bin/uv` and is **not** on a non-login `PATH`).
  From the **Bash tool** (Git Bash) rather than PowerShell, two different traps apply: Git Bash
  rewrites `/mnt/...` arguments into `C:/Program Files/Git/mnt/...`, so export
  `MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'` before any `wsl.exe` call; and Git Bash's `/tmp`
  is invisible to Windows Python, so hand files between them through the scratchpad directory,
  never `/tmp`.
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

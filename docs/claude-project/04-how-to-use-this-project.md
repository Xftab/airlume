# How to use this claude.ai project (free plan)

A free chat cannot be fine-tuned. "Training" here means: the Instructions box and these
files are read at the start of every chat in this project. Keep them current and every
new chat starts informed.

## Setup (once)
1. Project → Instructions → paste `00-project-instructions.md`.
2. Project → Files → upload `01-goal-and-phases.md`, `02-architecture-and-rules.md`,
   `03-status-and-next.md`, and the latest `docs/STATUS.md` and `docs/HISTORY.md`.
3. Optional: upload `docs/pdf/Airlume_Complete_Project_Plan.pdf` (full plan) and
   `docs/research/e1-results.md`.

## Each session
- Start with: "start work" (it reads status and continues) or a specific ask.
- End with: "update status" — then replace `03-status-and-next.md` and `STATUS.md` in Files.

## Good prompts for this project
- "Explain the project to my supervisor in plain words, 5 sentences."
- "What is left in Phase 3 and what is the next command I run?"
- "Review this screenshot of an error and tell me what to run."
- "Write the Phase 1 section of the report from plan.md and HISTORY.md."

## Do not
- Paste API keys or tokens into chat. Keys live only in `K:\airlume\.env`.
- Ask it to cut the plan. The ten-week plan stands.

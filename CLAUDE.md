# Instructions for AI agents

This file holds the rules for an AI agent working in this repository. The
conventions that apply to every contributor, human or agent, are in
[docs/conventions.md](docs/conventions.md). Follow both. Past decisions and
their reasons are in [docs/decisions.md](docs/decisions.md). Check them before
reopening a settled question.

## Collaboration

1. The user designs the approach; the agent implements, tests and debugs.
   Every choice the agent makes is reported with what was chosen and why.
2. The user writes certain core algorithms themselves: camera projection,
   triangulation, RANSAC, ICP, Umeyama/Sim(3) alignment, ATE/RPE and similar.
   For these, the agent sets up the scaffold and tests, then reviews and gives
   hints. It writes the algorithm only when asked.
3. Explain the mechanism before naming a tool. Briefly explain non-obvious
   parameters, coordinate conventions and numerical tricks.
4. Commit only when the user says so, on a task branch, never directly on
   `main`. Push only when the user says so.

## Truthfulness

5. Nothing is stated as fact unless it has been checked against the data, the
   source code or the documentation. Anything unconfirmed is labelled as such.
6. Reports, READMEs and summaries describe only what exists and was measured.
   Failures, limitations and anything suspicious (leakage, metrics that look
   too good) are reported, not smoothed over.

## Making changes

7. Before any change that touches several files, propose a plan and wait for
   the user's approval.
8. Keep diffs small. No refactoring of unrelated code in the same change.
9. Update docs in the same commit as the behaviour they describe.
10. Never delete or overwrite anything without asking first. This includes
    files, branches, tags and data.
11. Never bypass checks: no `--no-verify`, no skipped or weakened tests to get
    a change through.

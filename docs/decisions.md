# Decision log

Each entry records a decision that would be costly to reverse, or that someone
would later ask about. Entries are not edited after the fact. A changed
decision gets a new entry that supersedes the old one.

Format: context, decision, alternatives considered, consequences.

---

## D-001: Use ROS 2, converting the ROS 1 bag

**Date:** 2026-11-27 · **Status:** accepted (the ROS 2 distribution is still open)

**Context.** `Outdoor01.bag` is a ROS 1 bag. The deployment goal needs a live
ROS system, and the C++ perception node needs a ROS framework to run in.

**Decision.** Use ROS 2. Convert the bag to ROS 2 format once, and run all
ROS tooling on the converted bag.

**Alternatives.**
- *ROS 1 Noetic:* reads the bag natively, and several SLAM packages were
  written for it. But Noetic reached end of life in May 2025, and ROS 2 is
  what current robotics teams use.

**Consequences.**
- The Livox custom message types (`livox_ros_driver/CustomMsg`) must survive
  conversion. This is checked in the data inventory.
- SLAM packages need a working ROS 2 port, or a containerised alternative.
- The distribution (Humble or Jazzy) is chosen with the rest of the tool
  stack.

---

## D-002: Git workflow

**Date:** 2026-11-27 · **Status:** accepted

**Context.** The project is developed solo with an AI agent, but is meant to
follow the same practice a team would.

**Decision.**
- One branch per task. Changes reach `main` only through a pull request.
- Pull requests are squash-merged, so each one becomes one commit on `main`.
- Commit messages follow Conventional Commits.

**Alternatives.**
- *Committing directly to `main`:* simpler, but CI would not gate changes.
- *Rebase-merge:* keeps every commit of a branch. Work-in-progress commits
  would then end up in `main`.
- *Merge commits:* history is no longer linear and is harder to read.

**Consequences.** Branch protection on `main` (pull request required, CI must
pass, no force-push) is configured once CI exists.

---

## D-003: Public repository under the MIT license

**Date:** 2026-11-27 · **Status:** accepted

**Context.** The repository is meant to be read by others, and CI runs on
GitHub.

**Decision.** Host the repository publicly on GitHub, under the MIT license.

**Alternatives.**
- *Apache-2.0:* the same freedoms plus an explicit patent grant. That grant
  matters little for a project like this, and the license is much longer.
- *No license:* the code would be visible, but legally nobody could reuse it.

**Consequences.**
- The dataset is not redistributed. `data/` is gitignored.
- Third-party code under copyleft licenses (for example GPL) is run as an
  external tool, not copied into this repository. Each tool's license is
  recorded when the tool is chosen.

---

## D-004: Rule placement and enforcement

**Date:** 2026-11-27 · **Status:** accepted

**Context.** Written rules drift, especially when an agent starts each session
with no memory of the last one.

**Decision.**
- Rules that a tool can check are enforced by that tool (linter, pre-commit
  hook or CI) rather than by a written rule alone.
- Agent-specific rules live in `CLAUDE.md`, kept short because it is loaded
  into every agent session.
- Conventions shared by every contributor live in `docs/conventions.md`.

**Consequences.** Until the tooling phase, the rules marked **[tool]** in
`docs/conventions.md` are followed by hand.

---

## D-005: Transform naming and time representation

**Date:** 2026-11-27 · **Status:** accepted

**Context.** This project combines many coordinate frames: world, body, two
LiDARs, several cameras and IMUs. Frame mix-ups and time-matching errors are
easy to make and often fail silently.

**Decision.**
- A transform is named `T_a_b` and maps points from frame `b` into frame `a`.
- Timestamps are stored as integer nanoseconds.

**Alternatives.**
- *`T_b_a` or `T_from_to` ordering:* equally valid. One convention is needed,
  and `T_a_b` makes chained products easy to check, because the inner frames
  match.
- *Timestamps as float seconds:* convenient, but a `float64` holding
  nanosecond-scale epoch times loses precision, and comparing floats for
  equality is unreliable.

**Consequences.** Every module that handles poses or time depends on this.
Changing it later would touch the whole codebase.

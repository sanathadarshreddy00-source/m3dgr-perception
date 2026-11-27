# Conventions

These conventions apply to everyone who changes this repository, human or AI
agent.

Rules marked **[tool]** are to be enforced automatically by linters,
pre-commit hooks or CI, so they cannot be forgotten. That tooling does not
exist yet. Until it does, they are followed by hand. Rules marked **[rule]**
need judgement and are enforced only in review.

## Data

1. **[rule]** `data/raw/` is read-only. Nothing in the pipeline writes to it.
2. **[tool]** No data, model checkpoints or generated outputs are committed to
   git. `.gitignore` covers the known formats.
3. **[rule]** Every output records the config, random seed and git commit that
   produced it.

## Units, time and frames

4. **[rule]** SI units throughout: metres, seconds, radians. Units are
   converted once, where data enters the code, never inside it.
5. **[rule]** Timestamps are stored as integer nanoseconds (`int64`), as ROS
   does, and converted to seconds only for display. Exact integers avoid
   rounding errors when matching sensors by time.
6. **[rule]** A rigid transform is named `T_a_b` and maps points from frame `b`
   into frame `a`: `p_a = T_a_b @ p_b`. When transforms are chained, the inner
   frames must match:

   ```python
   T_world_cam = T_world_body @ T_body_cam    # body ... body: valid
   T_world_cam = T_world_body @ T_cam_body    # body ... cam: visibly wrong
   ```

## Code design

7. **[rule]** Dependencies point one way. Core math depends on nothing else in
   the project. I/O depends on core. Pipelines depend on both. Command-line
   tools and ROS nodes sit on top. Core never imports ROS and never touches
   files.
8. **[rule]** Library code holds the logic. Command-line tools and ROS nodes
   are thin wrappers around it.
9. **[rule]** Algorithms are pure functions: data in, data out, no hidden
   state.
10. **[rule]** Typed domain objects are used instead of raw arrays and dicts,
    for example `Pose`, `Trajectory`, `CameraIntrinsics` and `PointCloud`.
    Each carries its frame and units.
11. **[rule]** Fail loudly. No `except Exception: continue`. Inputs are
    validated where data enters. When skipping something is genuinely
    correct, the skips are counted and reported.
12. **[rule]** No speculative abstraction. Write the concrete thing first, and
    generalise only once a third use appears.
13. **[tool]** Public functions have type hints, checked by a type checker.
    **[rule]** Docstrings state units and frames.
14. **[rule]** No magic numbers in code. Parameters live in `configs/`.
15. **[tool]** Configs are typed and validated when loaded, so a typo fails
    immediately instead of silently falling back to a default.
16. **[tool]** Use `logging`, not `print`.

## Testing

17. **[rule]** Core math is tested against known answers on synthetic data.
    For example: move a trajectory by a known transform, align it back, and
    check that the known transform is recovered.
18. **[rule]** Every bug fix comes with a test that fails before the fix and
    passes after it.
19. **[tool]** Unit tests run in seconds. Slow tests that use real data are
    marked and run separately.

## C++

20. **[tool]** C++17 or later, formatted with clang-format and checked with
    clang-tidy.
21. **[rule]** Resources are owned by objects (RAII). No raw `new`/`delete`.
    Code is const-correct.
22. **[rule]** The same layering as Python: a plain C++ library holds the
    logic, and the ROS node is a thin wrapper. Tests use gtest.

## Dependencies

23. **[tool]** All dependencies are pinned in a lockfile.
24. **[rule]** A new dependency needs a stated reason, recorded in its pull
    request.

## Git

25. **[rule]** One logical change per commit. The message says why, not only
    what.
26. **[tool]** Commit messages follow
    [Conventional Commits](https://www.conventionalcommits.org/):
    `type(scope): summary`, for example `feat(trajectory): add ATE` or
    `fix(io): handle empty scans`.
27. **[tool]** Every commit passes lint and tests. Hooks are never bypassed.
28. **[rule]** One branch per task, named `type/short-description`, for
    example `feat/ate-metric`. Changes reach `main` only through a pull
    request, so CI runs on them.
29. **[rule]** Pull requests are squash-merged. `main` is never force-pushed.
30. **[rule]** Commits that produced reported results are tagged, so every
    published number can be traced to the exact code that produced it.
31. **[rule]** No secrets are committed.

## Decision log

32. **[rule]** A decision gets an entry in [decisions.md](decisions.md) when
    it would be costly to reverse, or when someone would later ask why it was
    made.

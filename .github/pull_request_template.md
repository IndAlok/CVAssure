# PR template. Keep it short; a wall of checkboxes gets rubber-stamped.

## What

<!-- one line. The observable change. -->

## Why

<!-- link the issue, or the PS clause, or the contract row -->

## Contract impact

- [ ] No change to `contracts/` — schema and interfaces are frozen at `contracts-v1`
- [ ] I changed a contract and opened a team discussion first (`CHANGELOG.md` updated)
- [ ] Files touched are inside my own folder (see `.github/CODEOWNERS`)

## Correctness

- [ ] Tests pass on my machine, and I ran `python -m pytest`
- [ ] `python -m ruff check .` clean
- [ ] New behaviour has a test that fails without this change
- [ ] Ran with sockets blocked if I added a code path (`--disable-socket`)

## Honesty, the CVAssure rules

- [ ] Every `Finding` I emit validates against `contracts/finding.schema.json`
- [ ] `limitations` says what the method did **not** check
- [ ] `severity` and `confidence` are set independently
- [ ] `link_hints` present on any `patch_trigger` / `blend_trigger` /
      `trigger_sweep_hit` / `trigger_reconstructed` finding
- [ ] I did not read Person 5's ground-truth manifest from inside `cvassure audit`
- [ ] No contributor id, class id, or dataset name hard-coded in policy, linker, or core
- [ ] Thresholds I added are in config and marked `UNCALIBRATED` in `docs/p1/DECISIONS.md`
- [ ] No new number in a doc or slide that I did not measure in a run

## Stub → real

- [ ] This PR replaces a stub. The stub keeps the **same detector id** so the registry
      prefers the real module. The removed stub is deleted in this PR, not left behind.
- [ ] This PR is a stub. It sets `stub: true`, prefixes `reason` with `[STUB]`, and the
      CLI shows a STUB badge.

## Data

- [ ] Fixtures and demo data are synthetic or clearly public-licence
- [ ] No classified, operational, or service-generated data
- [ ] No large binaries, no `out/`, no `wheelhouse/`, no secrets

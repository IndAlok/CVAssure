# Contributing — CVAssure

## The five rules that matter

1. **Never invent a number.** No detection rate, risk score, hash, or runtime that this run did
   not compute. Placeholder-looking values (`0.xx`, `xx%`, `N`) belong in mock-ups, never in a
   report, a slide, or a doc that claims to describe a result.
2. **No hard-coded contributor id, class id, or dataset name** in policy, linker, CLI format
   strings, or core. The demo story appears because the *inputs* contain it. `C-07` is a
   fixture value.
3. **No ground truth in the audit path.** Nothing under `src/cvassure/` reads
   `contracts/MANIFEST.md` or `demo/manifest.json`. Evaluation and coverage code may. If a
   detector needs the answers to work, it is a script under `scripts/`.
4. **`limitations` is mandatory and is never a formality.** Write what the method did *not*
   check. A finding with an empty `limitations` is a schema error, on purpose.
5. **Thresholds live in config** and stay marked `UNCALIBRATED` in `docs/p1/DECISIONS.md` until
   they are fitted on seeded data **that includes negative controls**.

## Branches and PRs

- Branch `pN/short-description`. Never commit to `main`.
- Under 400 lines. Split anything larger.
- One concern per commit. Tests with each unit.
- Fill in `.github/pull_request_template.md`. The honesty section is not decorative.
- Only touch your own folder (`.github/CODEOWNERS`). Need a change elsewhere? Open an issue.

## Contracts are frozen

`contracts/` is frozen at `contracts-v1`. **A contract change is a team event**: discuss it,
get a yes from every affected owner, add a row to `contracts/CHANGELOG.md` with a date and
who it breaks, then edit.

An unannounced contract change breaks every detector written against the old one, and the
resulting failures look like bugs in the detectors.

## Stubs

Day 2 has one stub per package so the pipeline runs end to end before the real detectors exist.
A stub must:

- register under **the same detector id the real one will use**, so the registry prefers the
  real module automatically
- set `stub: true` and prefix `reason` with `[STUB]`
- write a small PNG under the evidence directory so the report has something to open

`cvassure audit --strict` exits 5 if any stub ran. **Slides come from a `--strict` run**, so a
stub must never appear in a picture.

When you land the real detector, delete the stub in the same PR.

## Testing

```bash
pytest
ruff check . && ruff format --check .
pytest --disable-socket          # the audit path must need no network
```

- Non-trivial logic leaves one runnable check behind. A branch, a loop, a parser, a policy
  rule, a hash-chain operation: all need a test that fails without the change.
- Deterministic given `ctx.seed`. Seed every RNG from it. No wall-clock time, temp paths, or
  PIDs in a `reason`, `metadata`, or `summary`.
- New behaviour needs a test that fails on `main` today.

## Security

- `yaml.safe_load` only. No `eval`, no `exec`, no `simpleeval`, anywhere.
- No `pickle` on an untrusted file. `torch.load(..., weights_only=True)`. A `.npy` file loads
  with `allow_pickle=False`. This product is an integrity tool; it cannot be the thing that
  executes an attacker's payload.
- Evidence paths stay relative, under `out/evidence/`, with no `..` and no absolute paths. The
  schema rejects them and the pipeline resolves them before writing.
- Plugins load only from the `cvassure.detectors` entry-point group or an explicit module list
  in config. Never from a path a finding or a record names.
- Never log a private key. Public-key fingerprints only.
- No secrets in the repo. Not test keys, not sample keys.

## What not to commit

`out/`, `wheelhouse/`, `*.egg-info`, `.venv/`, large binaries, generated embeddings, generated
scenarios, anything from `demo/manifest.json`.

## Data

Development and evaluation data is **publicly available under an applicable licence, or
synthetic**. No classified, operational, or service-generated data — not in fixtures, not in
demos, not in docs. This is the problem statement's dataset rule, and the coverage statement
repeats it as an assumption.

Attack *definitions* may be cited from NIST TrojAI benchmark artefacts and BackdoorBench, which
the problem statement names as reference resources. **Do not install either repo and do not
download their pretrained weights.** The audit command runs with no network and without them.

## Commit messages

Short, imperative, one line. Conventional prefix when it fits: `feat:`, `fix:`, `docs:`,
`test:`, `refactor:`, `chore:`.

```text
feat(link): renormalise link weights over present components only
fix(policy): fail closed on a !!python tag in a policy file
test(records): cover the reused-nonce replay case
```

## Append-only logs

`docs/p1/PROGRESS.md` and `docs/p1/DECISIONS.md` are never edited in place. Append a dated
entry. A rewritten history is how the team loses the reason a decision was made.

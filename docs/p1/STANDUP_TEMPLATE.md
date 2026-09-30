# Standup template

15 minutes, `[[FILL]]`, same call every day. **Yesterday / today / blocked.** Nothing else.

A block longer than a few hours is said the same day, in this meeting. Not at the end of the
week, not in a PR comment, not silently absorbed.

---

```text
DATE:  ____________   ATTENDANCE: P1 P2 P3 P4 P5 [PPT owner]

P1  yesterday: <one line, the thing that actually landed>
     today:     <one line>
     blocked:    <none | BLOCKED-ON: P<n> — what I need, from whom, since when>

P2  yesterday:
     today:
     blocked:

P3  yesterday:
     today:
     blocked:

P4  yesterday:
     today:
     blocked:

P5  yesterday:
     today:
     blocked:

GATE STATUS
  day 2 stub pipeline            [ ] green   [ ] not yet   owner: P1
  day 4 first real detectors     [ ] green   [ ] not yet
  day 6 full demo scenario       [ ] green   [ ] not yet
  day 8 feature freeze           [ ] green   [ ] not yet

NUMBERS WE CAN STAND BEHIND TODAY
  - <a measured number, with the file it came from>
  - <a measured number, with the file it came from>
  (blank is a fine answer. a guessed number is not.)

CONTRACT CHANGES REQUESTED TODAY
  - <contract> — <what> — <who it breaks> — needs a yes/no before it lands
  (most days: none. that is the point of freezing at contracts-v1.)

DECISIONS NEEDED (goes into docs/p1/DECISIONS.md)
  - <the question>  -> <decision>  -> decided by <who> on <date>
```

---

## Rules for the meeting

- **Numbers, not intentions.** "Working on label flip" is not an answer. "Label flip fixture
  passes, 0.91 on 3 seeds, `demo/results_table.csv`" is.
- **Blocked is a status, not a failure.** Saying it early costs nothing. Discovering on day 6
  that a demo asset was never built costs the demo.
- **No contract changes decided in the standup.** Raise it, get the owners, decide in the
  thread, then it goes in `DECISIONS.md` and `CHANGELOG.md` with a date.
- **Person 1 keeps `main` green and reverts a red nightly the same day.** If your PR is red,
  fix it today or revert it today; do not leave `main` broken overnight.
- **Log appends only.** `docs/p1/PROGRESS.md` and `docs/p1/DECISIONS.md` are never edited in
  place. A rewritten history is how we lose the reason a decision was made.

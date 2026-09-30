# Cross-asset linking — how a model trigger and a data patch become one story

**Owner:** Person 1. **Code:** `src/cvassure/core/linking.py`. **Outputs:** `out/link_report.json`,
`out/evidence/LINK_<model>_<data>.png`.

PS §2.2.1 asks for source-level risk from sample-level evidence, and §2.2.2 asks whether a model
"exhibits anomalous, substituted or backdoor-like behaviour". Neither clause asks for the join
between them. The join is what makes this a *unified* assurance layer instead of three reports in
one file — and it is the hardest one to do honestly, because it is the only place where two
detectors' outputs are combined into a claim neither of them made.

---

## 1. The rule that shapes everything

**The linker reads `link_hints` and nothing else.** Not metadata, not arrays, not the ground-truth
manifest. It must also be able to print nothing, and printing nothing is a correct result, not a
failure.

That restriction is why `link_hints` is **required** by the schema on any data finding tagged
`patch_trigger` or `blend_trigger`, and on any model finding tagged `trigger_sweep_hit` or
`trigger_reconstructed`. A trigger finding with no geometry is a schema error, not a degraded link.

It also means a detector cannot "help" the linker by inventing a bounding box it did not measure.
A guessed bbox produces a real-looking link score and a demo that cannot survive "how do you know
these are the same trigger?".

---

## 2. The score

For each pair of (model finding with a trigger hint) × (data finding with a patch hint):

**Step 0 — class gate.** If both sides carry a `target_class` and they differ, the score is **0**
and evaluation stops. A trigger for class 1 is not the trigger found in class 0's samples, whatever
else matches.

**Step 1 — components in [0, 1].** Only those present on **both** sides:

| Component | Value | Absent when |
|---|---|---|
| `identity` | 1 if `patch_id` is equal, else 0 | either side has no `patch_id` |
| `overlap` | IoU of the two normalised bboxes | either side has no `location_bbox` |
| `pattern` | `max(0, NCC)` between the two template images, resampled to a common grid | either image is missing or unreadable |

**Step 2 — renormalise the configured weights over the components that exist.** Defaults,
uncalibrated: identity `0.5`, overlap `0.2`, pattern `0.3`.

This step is the one that keeps the score honest. A black-box sweep that has only a `patch_id` and
a class scores on `identity` with weight `1.0`, **not** with weight `0.5` scaled down to a
suspiciously-low `0.5`. Both the configured and the used weights are written to `link_report.json`,
so a reader can see exactly which evidence carried the decision.

If every present component has configured weight 0, the weights are split equally, and
`weights_used` records that this is what happened rather than hiding it.

**Step 3 — link if `score >= tau_link`.** Default `tau_link = 0.50`, marked `UNCALIBRATED`.

---

## 3. What happens on a link

1. Each finding id is added to the other's `linked_findings`, sorted.
2. The **model** finding's severity is escalated by noisy-OR:
   `after = 1 - (1 - s_model) * (1 - s_data)`, capped at 1. The data finding's severity is not
   changed.
3. `escalation` is recorded on **both** sides: `severity_before` keeps the pre-link value, so a
   reader can see the link did the raising rather than assuming the detector found a `0.97`.
   The model side gets `method: "noisy-or"`; the data side gets `method: "link"` and
   `escalated: false`, because the link did not change the data severity and saying otherwise
   would overstate what happened.
4. **The disposition is not touched here.** Rule `R5-review-linked-model` sets it, in the policy
   file, where a judge can read it. The plan's §0 decision is explicit: a link must not force a
   quarantine of the model.
5. `out/link_report.json` gets the pair: components, score, `tau_link`, and the weights used.
6. `out/evidence/LINK_<model>_<data>.png` is written: the two templates side by side, resampled to
   a common grid, or a plain placeholder if either image is unreadable. The report always has a
   file to open.
7. An audit event `link_created` is appended.

**When `pattern` is absent**, the model finding's `limitations` gains the sentence
*"pattern similarity was not available."* The plan requires that a link restricted to identity and
class says so where a reader will see it, not only in the link report.

---

## 4. Honest degradation, in three flavours

| Situation | What happens |
|---|---|
| Black-box sweep, `patch_id` + class only | links on `identity` alone, weight 1.0, `limitations` notes pattern unavailable |
| `reconstructed` trigger from P3 | no `patch_id` by construction (the schema *rejects* one), so identity cannot be faked; the pair needs `overlap` and/or `pattern` to link |
| Neither side has usable geometry | no component survives, the pair is skipped, and **no LINK line prints** |

That third row is the important one. The LINK line is the demo's most quotable moment, which makes
it the most tempting to fake. `test_no_link_line_when_the_model_is_absent` asserts the pipeline
prints nothing rather than inventing a match.

### The `reconstructed` rule, restated

`TriggerHint` rejects `kind: reconstructed` **with** a `patch_id`, and rejects
`kind: patch_library` **without** one. A reconstruction produces a mask; identity comes from a
patch library. Allowing a reconstruction to carry an id would let a detector claim an identity
match it never measured, and the linker would score it as though two sides had independently named
the same patch. That is a schema-level guarantee, not a code-review convention.

---

## 5. Calibration — not done yet, and the plan says why

`tau_link` and the three weights are starting values, registered `UNCALIBRATED` in
`docs/p1/DECISIONS.md` §D. They get fitted only once Person 5 supplies the four variants on the
same seed family:

| Variant | Expected |
|---|---|
| Backdoor patch equals the data patch | link |
| Backdoor patch differs from the data patch | no link |
| Clean model, poisoned data | no link |
| Backdoored model, clean data | no link |

Then: link precision and recall over at least **3 seeds**, a coverage row `Cross-asset linking`,
and a dated `DECISIONS.md` row freezing the numbers; and add `Cross-asset linking` to the results
table. `configs/coverage_rules.yaml` already lists that class as `Untested`, which is the correct
status until those numbers exist.

**`tau_link` must never be tuned to force the demo contributor to link.** If the seeded scenario
needs a lower threshold to link, the scenario is wrong, not the threshold — and a threshold fitted
to make one id link will not generalise, which is the definition of overfitting on a demo.

---

## 6. Tests

`tests/core/test_linking.py` covers every case in the plan's §10.4 with tiny PNGs and `.npy` files
generated inside the test, never real photos:

`iou` identical / disjoint / half-overlap · `ncc` identical `1.0` and inverted `-1.0` · `ncc` on a
flat image returns `0.0` rather than crashing on the `0/0` · `ncc` resamples different sizes ·
same `patch_id` + matching geometry links · both sides naming a library patch gives an identity
component · escalation follows noisy-OR · both findings cross-reference · **linking does not change
the disposition** · an evidence PNG is written · class mismatch never links · different `patch_id`
never links · no hints means no link · one-sided hints do not link · a missing image leaves
`pattern` absent · weights renormalise over present components · a reconstructed trigger without a
pattern says so in `limitations` · the threshold is respected · the report records the calibration
state · no contributor id appears in the linker source.

The last one runs over executable code with comments and docstrings stripped, so naming `C-07` in a
comment as the thing we refuse to hard-code stays legal while a string literal would fail the
build.

---

## 7. Why numpy and not OpenCV

IoU is four lines of arithmetic. NCC on a pair of small crops is a mean-subtracted dot product over
a resampled grid. OpenCV would add tens of megabytes, a C extension, and a licensing conversation
to compute both, and the plan's §0 decision names it as rejected. `max(0, NCC)` is deliberately
conservative: a *negatively* correlated pattern is evidence against a match, and letting it
contribute negatively to the weighted sum would make a bad match reduce the score of a good one.

Image decoding is the one thing numpy cannot do unaided, so `_read_gray` reads `.npy` natively and
attempts an **optional, lazily imported** Pillow for PNG/JPEG. If Pillow is absent the `pattern`
component is simply absent — recorded as absent, never as a zero that reads like "measured, no
match". `import cvassure.core` pulls no image library; a test asserts exactly that.
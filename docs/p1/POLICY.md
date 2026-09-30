# Policy — `when` / `then`, and why it is not Rego

**Owner:** Person 1. **Engine:** `src/cvassure/core/policy.py`. **File:** `policies/default.yaml`.
**Schema:** `contracts/policy.schema.json`.

The policy engine writes every final `disposition`. Detectors may propose one; policy overwrites
it. This is the split that makes the report honest: a detector reports what it found, and one
readable file decides what to do about it.

---

## 1. The language, in full

A policy file is a mapping with `version`, `name`, `defaults`, `precedence` and `rules`. Loaded
with `yaml.safe_load` **only**.

```yaml
version: 1
name: cvassure-default
defaults:
  disposition: review          # an emitted finding is never silent
precedence: [rejected, quarantine, review, accept]
rules:
  - id: R1-quarantine-high-data
    when: { asset: data, severity: { gte: 0.8 }, confidence: { gte: 0.6 } }
    then: { disposition: quarantine, scope: source }
```

A `when` block is an **AND** of field tests. There is no OR, no NOT, and no nesting except the one
special form `linked` (below).

| Operator | Meaning |
|---|---|
| `eq`, `ne` | equality / inequality |
| `gte`, `lte`, `gt`, `lt` | ordered comparison. A `None` field never satisfies an ordered test |
| `in` | field is a member of the operand list |
| `contains` | operand is a member of the field list, or a substring when both are strings |

A bare value means `eq`: `when: { asset: data }` and `when: { asset: { eq: data } }` are the same
test.

**Testable fields** are the flat top-level Finding keys: `asset`, `severity`, `confidence`,
`disposition`, `reason`, `access_level`, `source_id`, `batch_id`, `class_label`, `sample_count`,
`tags`, `stub`. Plus `linked`.

Anything else — an unknown field name, an unknown operator, a `then.disposition` outside the
precedence list, a `scope` outside `source|batch|sample|record`, a duplicate rule id — is a
**config error and exit code 2**. Not a skip. A rule that silently does not apply produces a report
that looks complete and is not, which is the worst failure mode this engine could have.

Every `when` block is also compiled against a real probe Finding **at load time**, so a typo in
field or operator name surfaces before any detector runs rather than at stage 3 of a demo.

---

## 2. Precedence, ties, and the default

Three rules decide the outcome when more than one rule matches:

1. **The default is a floor, not a competitor.** A rule that fires always beats the declared
   default. Otherwise `accept` would be unreachable and a rule that happens to produce
   `review` would be recorded in the report as `default` — blurring "the policy said this" with
   "the policy said nothing".
2. **Precedence decides among firing rules:** `rejected` beats `quarantine` beats `review` beats
   `accept`.
3. **On a tie, the later rule wins.** A specific rule placed after a general one refines it. This
   is why `R5-review-linked-model` follows `R2-review-model` and is the rule reported for a linked
   model finding.

`defaults.disposition` **may not be `accept`**. The engine refuses to load a policy that declares
it. A high-severity finding nobody wrote a rule for must not read as a clean bill of health — that
is the rejected alternative from the plan §0, and this is where the decision is enforced rather
than merely documented.

Every finding records `policy.rule_id` and `policy.policy_hash`. `run_manifest.json` carries a hit
count per rule, so "which rule never fired" is answerable without reading the log.

---

## 3. `linked` — the one cross-finding test

```yaml
  - id: R5-review-linked-model
    when: { asset: model, linked: { any: { disposition: quarantine } } }
    then: { disposition: review, escalate: true }
```

`linked` supports exactly one form, `any`, over the finding's `linked_findings`. It is what lets
"this model trigger is tied to a contributor we quarantined" become a policy decision instead of a
hard-coded branch in the linker.

It requires two passes, and the reason is worth recording: when the model finding is evaluated, the
data finding beside it has not been dispositioned yet. So pass one resolves every finding from its
own fields, and pass two re-runs with pass one's answers available to `linked`.

**Known limitation, stated rather than hidden:** the two-pass scheme resolves a one-hop reference.
A rule chain longer than one hop — A depends on B which depends on C — is **not** resolved, and no
rule set in this repo depends on one. If a future rule needs it, that is a third pass and a
changelog line, not a quiet edit.

---

## 4. Security boundary

`yaml.safe_load` is not a style preference here, it is the boundary.

A `!!python/object` tag makes PyYAML reach for `object.__new__`. `safe_load` refuses to construct
it and the loader raises `ConfigError`, so a policy file that a judge edits in front of us cannot
become code execution. **There is a test per failure mode**: each rule, precedence, the tie, a
missing field, malformed YAML, an unknown operator, and the `!!python/object` tag.

Also enforced: `MAX_CONFIG_BYTES = 512 KB` on any config or policy file, so an oversized YAML
document is rejected before it is parsed.

No `eval`. No `exec`. No `simpleeval`. Rejected in the plan §0 and rejected here for the same
reason: `simpleeval` is a dependency whose entire job is to evaluate expressions we deliberately
decided not to have.

---

## 5. What this DSL cannot express, in one line

**No loops, no arithmetic beyond the linker's own formula, no OR/NOT, no cross-finding
aggregation, and no rule chain longer than one hop.** For four rules over flat Finding fields that
is the whole requirement; if policy ever needs aggregation or arithmetic, OPA and Rego become the
right answer and this file is the wrong tool. `docs/research/standards.md` §6 records that
trade-off.

The DSL was chosen over OPA for an offline MVP because OPA adds either a second binary or a
subprocess to an air-gapped CPU tool, and because a judge can read four `when`/`then` blocks off
the file in ten seconds while a Rego bundle needs a policy-language primer first.

---

## 6. Thresholds are uncalibrated

The cut-offs in `policies/default.yaml` (`R1` at severity 0.8 / confidence 0.6, `R2` at 0.5) are
**starting values**, registered as `UNCALIBRATED` in `docs/p1/DECISIONS.md` section D. They are
fitted on seeded data that includes a clean control and then frozen with a dated row. Until then
no headline result may be quoted as if these numbers meant something.

**No contributor id appears in any rule.** `C-07` is a value in the demo inputs, not a constant in
policy. There is a test that scans executable core code for contributor and batch ids, and it skips
exactly one file — `stubs.py`, where the day-2 demo story is allowed to live.
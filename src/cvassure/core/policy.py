"""Declarative policy engine. `when` and `then`, eight operators, no code.

The policy file decides every `disposition`. Detectors propose. Policy decides.
An emitted finding that matches no rule gets the declared default, which is
`review`. A high-severity flag does not fall through to `accept`.

There is no `eval`, no `exec`, and no `simpleeval`. An unknown field or operator
is a config error and exit 2.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cvassure.core.finding import Finding, PolicyRef
from cvassure.core.hashing import canonical_sha256

#: Strongest first. This order, not rule order, decides a tie.
PRECEDENCE: tuple[str, ...] = ("rejected", "quarantine", "review", "accept")

SCALARS = (str, int, float, bool)


class PolicyError(ValueError):
    """Malformed policy. Fails closed. The CLI turns this into exit 2."""


@dataclass(frozen=True)
class Rule:
    id: str
    when: Mapping[str, Any]
    then: Mapping[str, Any]


@dataclass(frozen=True)
class Policy:
    version: int
    name: str
    default_disposition: str
    precedence: tuple[str, ...]
    rules: tuple[Rule, ...]
    policy_hash: str
    source: Path | None = None

    def apply(self, f: Finding, *, linked: Sequence[Finding] = ()) -> tuple[str, str, bool]:
        """Return (disposition, rule_id, escalated).

        The default is a floor, not a competitor. A rule that fires always beats
        the default, otherwise `accept` would be unreachable and a rule that
        happens to produce the same disposition would be recorded as `default`
        in the report - which is exactly the "the policy said nothing" case we
        must not blur.

        Among firing rules, `precedence` decides, strongest first. On a tie the
        later rule wins, so a specific rule placed after a general one refines
        it. That is a deliberate choice and it is why `R5` follows `R2` in
        `policies/default.yaml` and is the rule reported for a linked model.
        """
        rank = {name: i for i, name in enumerate(self.precedence)}
        best: tuple[str, str, bool] | None = None
        for rule in self.rules:
            if not _when_block(rule.when, f, linked):
                continue
            then = rule.then
            disp = str(then.get("disposition", self.default_disposition))
            candidate = (disp, rule.id, bool(then.get("escalate", False)))
            if best is None or rank.get(candidate[0], len(rank)) <= rank.get(best[0], len(rank)):
                best = candidate
        if best is None:
            return self.default_disposition, "default", False
        return best


# --- operators. The whole language is this table. ---


def _as_comparable(v: Any) -> Any:
    return v


def _op_eq(field: Any, operand: Any) -> bool:
    return bool(_as_comparable(field) == operand)


def _op_ne(field: Any, operand: Any) -> bool:
    return bool(_as_comparable(field) != operand)


def _op_gte(field: Any, operand: Any) -> bool:
    return field is not None and field >= operand


def _op_lte(field: Any, operand: Any) -> bool:
    return field is not None and field <= operand


def _op_gt(field: Any, operand: Any) -> bool:
    return field is not None and field > operand


def _op_lt(field: Any, operand: Any) -> bool:
    return field is not None and field < operand


def _op_in(field: Any, operand: Any) -> bool:
    return field in operand


def _op_contains(field: Any, operand: Any) -> bool:
    if isinstance(field, (list, tuple, set)):
        return operand in field
    if isinstance(field, str) and isinstance(operand, str):
        return operand in field
    return False


OPERATORS = {
    "eq": _op_eq,
    "ne": _op_ne,
    "gte": _op_gte,
    "lte": _op_lte,
    "gt": _op_gt,
    "lt": _op_lt,
    "in": _op_in,
    "contains": _op_contains,
}

#: Top-level Finding keys a rule may test. Anything else is a config error.
FINDING_FIELDS = frozenset(
    {
        "asset",
        "severity",
        "confidence",
        "disposition",
        "reason",
        "access_level",
        "source_id",
        "batch_id",
        "class_label",
        "sample_count",
        "tags",
        "stub",
    }
)


def _field_value(name: str, f: Finding, linked: Sequence[Finding]) -> Any:
    if name == "linked":
        return list(linked)
    if not hasattr(f, name):
        return None
    return getattr(f, name)


def _linked_test(spec: Mapping[str, Any], linked: Sequence[Finding]) -> bool:
    """`linked: {any: {disposition: quarantine}}` ,  does any linked finding match?"""
    if "any" not in spec:
        raise PolicyError("linked supports only `any`")
    inner = spec["any"]
    if not isinstance(inner, dict):
        raise PolicyError("linked.any must be a mapping")
    return any(_when_block(inner, neighbour, ()) for neighbour in linked)


def _when_block(when: Mapping[str, Any], f: Finding, linked: Sequence[Finding]) -> bool:
    for name, test in when.items():
        if name == "linked":
            if not _linked_test(test, linked):
                return False
            continue
        if name not in FINDING_FIELDS:
            raise PolicyError(
                f"unknown field {name!r}. Policy may test only "
                f"{sorted(FINDING_FIELDS)} plus `linked`"
            )
        value = _field_value(name, f, linked)
        if isinstance(test, dict):
            for op, operand in test.items():
                if op not in OPERATORS:
                    raise PolicyError(
                        f"unknown operator {op!r} on field {name!r}. Allowed: {sorted(OPERATORS)}"
                    )
                try:
                    ok = OPERATORS[op](value, operand)
                except TypeError as exc:
                    raise PolicyError(
                        f"operator {op!r} on {name!r} cannot compare "
                        f"{type(value).__name__} with {type(operand).__name__}"
                    ) from exc
                if not ok:
                    return False
        else:
            # bare value means eq
            if value != test:
                return False
    return True


def _validate_rules(rules: Iterable[Any]) -> tuple[Rule, ...]:
    out: list[Rule] = []
    seen: set[str] = set()
    for i, raw in enumerate(rules):
        if not isinstance(raw, dict):
            raise PolicyError(f"rule {i} is not a mapping")
        rid = raw.get("id")
        if not isinstance(rid, str) or not rid:
            raise PolicyError(f"rule {i} needs a non-empty string id")
        if rid in seen:
            raise PolicyError(f"duplicate rule id {rid!r}")
        seen.add(rid)
        when = raw.get("when", {})
        then = raw.get("then", {})
        if not isinstance(when, dict):
            raise PolicyError(f"{rid}: when must be a mapping")
        if not isinstance(then, dict):
            raise PolicyError(f"{rid}: then must be a mapping")
        disp = then.get("disposition")
        if disp is not None and disp not in PRECEDENCE:
            raise PolicyError(f"{rid}: disposition {disp!r} is not one of {PRECEDENCE}")
        if "scope" in then and then["scope"] not in ("source", "batch", "sample", "record"):
            raise PolicyError(f"{rid}: scope {then['scope']!r} is not a known scope")
        out.append(Rule(id=rid, when=when, then=then))
    return tuple(out)


def load_policy(path: Path) -> Policy:
    from cvassure.core.config import load_yaml  # local: config imports nothing from here

    doc = load_yaml(path)
    if doc is None:
        raise PolicyError(f"{path} is empty")
    if not isinstance(doc, dict):
        raise PolicyError(f"{path} must contain a mapping at the top level")
    _validate_against_schema(doc, path)

    version = doc.get("version")
    if version != 1:
        raise PolicyError(f"policy version must be 1, got {version!r}")
    name = doc.get("name")
    if not isinstance(name, str) or not name:
        raise PolicyError("policy needs a non-empty name")

    precedence = tuple(doc.get("precedence", PRECEDENCE))
    if set(precedence) != set(PRECEDENCE):
        raise PolicyError(f"precedence must be a permutation of {list(PRECEDENCE)}")

    defaults = doc.get("defaults") or {}
    if not isinstance(defaults, dict):
        raise PolicyError("defaults must be a mapping")
    default_disp = defaults.get("disposition", "review")
    if default_disp not in PRECEDENCE:
        raise PolicyError(f"defaults.disposition {default_disp!r} is not one of {PRECEDENCE}")
    if default_disp == "accept":
        # A rule may say accept. The *default* may not: a finding nobody wrote a
        # rule for must never read as a clean bill of health.
        raise PolicyError(
            "defaults.disposition may not be 'accept'. An emitted finding with no "
            "matching rule defaults to 'review'. 'accept' is only reachable by a rule."
        )

    rules = _validate_rules(doc.get("rules", []))
    policy = Policy(
        version=version,
        name=name,
        default_disposition=default_disp,
        precedence=precedence,
        rules=rules,
        policy_hash=canonical_sha256(doc),
        source=path,
    )
    # Compile every `when` against a real draft so a bad operator or field is a
    # load-time error, not a surprise at stage 3 of a run.
    probe = _probe_finding()
    for rule in rules:
        _when_block(rule.when, probe, ())
    return policy


def _probe_finding() -> Finding:
    """A minimal valid Finding used only to type-check `when` blocks at load.

    Values are placeholders. The point is that it is a real Finding, so a rule
    referencing a field that does not exist fails here rather than mid-run.
    """
    return Finding.draft(
        asset="data",
        reason="policy probe, not a real finding",
        evidence=["evidence/probe.png"],
        severity=0.0,
        confidence=0.0,
        access_level="not-applicable",
        limitations="Synthetic object used to validate policy rule syntax at load.",
        disposition="review",
    )


def apply_policy(
    findings: Sequence[Finding], policy: Policy
) -> tuple[list[Finding], dict[str, int]]:
    """Write the final disposition. Returns the findings and per-rule hit counts.

    Two passes, and the reason is `linked: {any: {disposition: quarantine}}` (R5).
    A rule that asks about a *neighbour's* disposition cannot work in one pass:
    when the model finding is evaluated, the data finding beside it has not been
    dispositioned yet. So pass one resolves every finding using only its own
    fields, and pass two re-runs with pass one's answers available to the
    `linked` block.

    The result is a fixed point in one iteration for our rule set, and the
    second pass is what the report and the `policy.rule_id` reflect. The
    limitation is honest and belongs in the coverage statement: a rule chain
    longer than one hop (A depends on B which depends on C) is not resolved.
    """
    by_id = {f.id: f for f in findings if f.id}

    # Pass one: no neighbours. Establishes the disposition each finding would
    # get on its own evidence.
    first_pass = {}
    for f in findings:
        first_pass[f.id] = policy.apply(f, linked=())[0]

    # Pass two: neighbours carry their pass-one disposition.
    links = {
        f.id: [
            by_id[i].model_copy(update={"disposition": first_pass[i]})
            for i in f.linked_findings
            if i in by_id
        ]
        for f in findings
        if f.id
    }

    out: list[Finding] = []
    hits: dict[str, int] = {r.id: 0 for r in policy.rules}
    for f in findings:
        disposition, rule_id, _escalate = policy.apply(f, linked=links.get(f.id or "", ()))
        if rule_id in hits:
            hits[rule_id] += 1
        out.append(
            f.model_copy(
                update={
                    "disposition": disposition,
                    "policy": PolicyRef(rule_id=rule_id, policy_hash=policy.policy_hash),
                }
            )
        )
    return out, hits


def _schema_path() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "contracts" / "policy.schema.json"
        if candidate.is_file():
            return candidate
    return None


def _validate_against_schema(doc: Mapping[str, Any], path: Path) -> None:
    schema_path = _schema_path()
    if schema_path is None:
        raise PolicyError("contracts/policy.schema.json is missing. Refusing to load a policy")
    import json

    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import ValidationError

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        Draft202012Validator(schema).validate(doc)
    except ValidationError as exc:
        raise PolicyError(f"{path}: {exc.message}") from exc

# SIH26228 — what the problem statement actually says, and who owns it

**Owner:** Person 1. **Re-fetched and re-read on 30 September 2026.**
Source: <https://sih2026.vuce.in/ps/SIH26228>. Theme page:
<https://sih2026.vuce.in/themes/blockchain-cybersecurity>.

This file separates **verified text** from **assumption**. Everything in §2 is quoted or
paraphrased from the page as it loaded. Everything labelled `ASSUMPTION` is our reading, not the
organiser's words. Nothing here is invented.

---

## 1. Metadata, as displayed

| Field | Value |
|---|---|
| ID | SIH26228 |
| Title | *Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines* |
| Organisation | Ministry of Defence (MoD) |
| Department | Indian Army (DGIS) |
| Category | Software |
| Theme | Blockchain & Cybersecurity |
| Deadline shown | **30 September 2026** |
| Submitted ideas | 1/500 |
| Attached dataset link | `https://sih2026.vuce.in/ps/Dataset` — **404, "Problem statement not found"** on 30 Sep 2026 |
| Practical | `https://sih.gov.in/sih2026PS` |

### Decision E1 — what the deadline means

The listing shows `Deadline 30 September 2026` and a `Due today` badge. The **page does not say**
whether that is the portal closing for idea submission, a listing date, or the last date to
submit something else. `DECISIONS.md` records this as `HUMAN TODO`: confirm with the SPOC. **Do
not invent a second deadline and do not state a time of day.**

### Decision E2 — evaluation weights

**There is no weights table on the page. Re-confirmed 30 September 2026.**

A keyword scan of the full fetched text found exactly one occurrence of "weight", inside §2.2.3:
*"model identifier or **weight** digest"*. It is not an evaluation weight. There are zero
occurrences of "marking", "criteria", "score" or "evaluation weight".

The visible page structure is: problem description and statement details (§2.1–§2.3, the dataset
rule, §7.1), then a "Similar Problem Statements" rail — the same block repeated on every statement
— then the footer and a command palette. Nothing after §7.1 belongs to this statement.

**Therefore: no weights are recorded anywhere in this repo, and `docs/images/` must not show any.**
A judge's rubric is not ours to guess. If the SPOC or the SIH portal later publishes one, paste it
here verbatim with the access date and add a row to `DECISIONS.md`.

---

## 2. Verified statement text, split by owner

Re-fetched 30 September 2026. §2.1 as published contains the stray token **"of Fos"** immediately
after the last sentence of §2.1 — the same copy glitch the hand-off documented. It is not
meaningful and we ignore it.

### §2.1 Background — no owner; it is the premise

> Operational computer vision pipelines may combine training data from multiple contributors,
> pretrained or vendor-supplied models, and inference outputs consumed by downstream systems. This
> creates distinct integrity and assurance risks across the data, model and inference lifecycle.
> Data may contain deliberately or inadvertently mislabelled samples, duplicated content,
> out-of-distribution material or trigger-based backdoors. A model may be substituted, modified or
> contain hidden behaviour that is not apparent during routine validation. Inference records may
> also be replayed, replaced or altered after generation unless they are cryptographically linked
> to the exact input, model and processing chain that produced them. Existing controls often
> address only individual parts of this lifecycle. The challenge is therefore to create a unified,
> evidence-based assurance layer that can assess these risks without assuming that every
> contributing source is trusted.

The last sentence is the product definition: **one layer, three assets, no trusted contributor.**

| PS clause | Requirement, in our words | Owner |
|---|---|---|
| §2.2.1 Training-data integrity | trigger injection, label flipping, systematic mislabelling, near-duplicate flooding, OOD insertion; aggregate sample evidence into a **source-level** risk assessment where contributor/batch metadata exists | **P2** |
| §2.2.2 Model integrity | anomalous / substituted / backdoor-like behaviour, "methods appropriate to the level of access available"; behavioural fingerprinting, trigger search or reconstruction, parameter or activation statistics, comparison against a reference battery; **must state access assumptions, confidence and limitations** | **P3** (P1 surfaces the access tier and enforces non-empty `limitations`) |
| §2.2.3 Inference provenance | verifiable cryptographic binding among input image, model id or weight digest, preprocessing, inference config, and result; alteration/substitution/replay detectable via hashes, signatures and sequence/timestamp/nonce controls | **P4** (P1 consumes the chain for the audit log) |
| §2.2.4 Distribution shift | material deviation from a declared reference distribution, including terrain, season, sensor, illumination, acquisition; characterise the shift, give a calibrated score, **distinguish probable operational drift from suspicious manipulation** where the evidence supports it | **P5** |
| §2.2.5 Assurance and governance | every flag carries a human-readable reason, supporting evidence, confidence or severity, the affected asset, and a disposition such as accept/review/quarantine; tamper-evident audit trail; **explicitly declare attack classes or conditions it does not support** | **P1** — this is Person 1's clause, plus the team plan's added `rejected` disposition |
| §2.2.6 Constraints | whole workflow offline and air-gapped, no cloud service or external API; ingest COCO and YOLO; support ONNX and PyTorch/TorchScript; baseline assessment **must not retrain** the model (optional remediation may); white-box methods must "fall back gracefully or clearly report that the relevant assessment is unavailable" when only black-box access is given | **P1 enforces in the pipeline**, with P2/P3 per detector |

Two clauses are worth quoting exactly because they are the ones a demo can fail silently:

> The system must state the access assumptions, confidence and limitations of its assessment. (§2.2.2)

> Methods that require white-box access must fall back gracefully or clearly report that the
> relevant assessment is unavailable when only black-box access is provided. (§2.2.6)

Both are why `limitations` is a required, non-empty schema field, why an access-tier mismatch
produces a `skipped` result with a reason rather than a silent pass, and why a skipped stage prints
`skipped (<reason>)` on the demo line instead of nothing.

### §2.3 Expected solution

> Teams are expected to develop a model-agnostic assurance system for assessing the integrity of
> training data, trained computer-vision models and inference outputs. The solution shall use
> publicly available or team-generated datasets and models, with teams developing reproducible
> methods to introduce representative poisoning, backdoor, substitution and tampering scenarios
> for testing. The system should identify suspicious data or contributor behaviour, assess model
> integrity, detect tampering of inference records, provide supporting evidence for each finding,
> and generate a clear assurance report stating confidence, limitations and recommended action.

**Submission artefacts named by §2.3**, mapped to this repo:

| Named artefact | Where it lives | Owner |
|---|---|---|
| source code | `src/`, `tests/`, `scripts/` | all |
| architecture and setup notes | `README.md`, `docs/diagrams/`, `docs/images/p1_architecture.png` | P1 |
| assurance-report schema | `contracts/finding.schema.json` + `contracts/FINDING.md` | **P1** |
| reproducible audit log | `out/audit.log`, `cvassure verify-log`, `--reproducible` | P1 (chain), P4 (signatures) |
| coverage statement | `out/coverage.json`, `out/coverage.md`, `configs/coverage_rules.yaml` | **P1** |

### The dataset rule (pasted verbatim after §2.3 on the page)

> All development and evaluation data will be publicly available under applicable licences or
> synthetically generated. No classified, operational or service-generated data will be used.

Consequences we enforce rather than document:

- P5 generates the synthetic scenario. No real photographs, no downloaded dataset.
- `tests/fixtures/` is synthetic and says so in its own README.
- No classified, operational or service-generated data in fixtures, demos, docs **or slides**.
- This sentence is an **assumption line in the coverage statement** (`configs/coverage_rules.yaml`),
  so it ships with every report rather than living only in the README.

### §7.1 Reference attack and assurance resources — the truncated clause

Page text, verbatim, and it ends there:

> **7.1. Reference attack and assurance resources.** NIST TrojAI benchmark artefacts, BackdoorBench
> and other reproducible public backdoor or adversarial-machi

The token is cut mid-word. Re-fetched 2026-09-30: the page still ends at exactly this point. A
keyword scan of the full fetched text found **zero** occurrences of "TrojAI" or "BackdoorBench" in
the aggregated body and **zero** occurrences of "7.2". There is no later section, no appendix and
no continuation on the theme page.

**ASSUMPTION A1 (binding, from the plan §0):** the cut-off token means *adversarial-machine-learning
material*. Read as a whole, the clause says: use NIST TrojAI benchmark artefacts, BackdoorBench and
other reproducible public backdoor or adversarial-machine-learning material as **references**. This
is an assumption about a truncated sentence, **not a quote**, and it is labelled as such everywhere
it appears.

What A1 authorises and forbids:

| | |
|---|---|
| Authorised | naming the attack families those benchmarks use (BadNets-style patch, blend) in the coverage statement; citing them as related work in `docs/research/related_tools.md` |
| Forbidden | installing either, vendoring either, downloading their weights or corpora into this repo, or making the audit command depend on them |
| Binding on | P5 (implements the families from definitions, downloads nothing), P1 (forbids non-public data in core fixtures), everyone (no vendoring) |

The licence finding makes this concrete: BackdoorBench is **CC BY-NC 4.0, non-commercial** (read
from its `LICENSE` on 30 Sep 2026). Treating it as a definition reference rather than a shipped
dependency is not just tidiness, it is the licence-safe choice.

**Allowed demo attack families** — P5 implements these, P1 only names them in coverage:
BadNets-style patch, blend, label flip, near-duplicate flood, OOD insertion, model swap, record
tamper/replay, natural fog.

**Declared out of scope, matching the team plan and the coverage statement:** WaNet and
imperceptible clean-label perturbations (both `Unsupported`), plus adaptive attackers and hardware
or compiler backdoors.

---

## 3. Idea PPT format — verified

**Maximum 6 slides including the title. PDF only. Points and pictures, not paragraphs.**

Template sections, in order: title, proposed solution, technical approach, feasibility, impact,
references.

Sources: [SIH2026 idea presentation format](https://www.scribd.com/document/1075380264/SIH2026-IDEA-Presentation-Format)
and a [mirror of the same template](https://studylib.net/doc/28802638/sih2026-idea-presentation-format--1-).

**Conflict, flagged not resolved (E3 in `DECISIONS.md`):** some launch summaries show a different
six-slide split, with the tech stack as its own slide. The team plan's split is the one in the
plan §14. **The PPT owner follows the file the SPOC issued**, and if that differs, the deck changes
— not this repo. Two splits both claiming six slides is exactly the kind of thing that gets
discovered the night before.

The software edition also requires a demo video that is **not AI-generated** and a GitHub repo with
a README and at least a partial implementation
([Guidelines of SIH2026](https://www.scribd.com/document/1077654176/Guidelines-of-SIH2026)).
Video is **P4's**; README is **P1's**.

---

## 4. Gaps in the statement, recorded

| # | Gap | Status |
|---|---|---|
| G1 | No evaluation weights table on the page | Confirmed absent 30 Sep 2026. Nothing invented. See E2. |
| G2 | §7.1 truncated mid-token at `adversarial-machi` | Assumption A1 covers it. No later section exists. |
| G3 | Deadline shown but its meaning unstated | `HUMAN TODO`, ask the SPOC. See E1. |
| G4 | The attached-dataset link `ps/Dataset` 404s | Recorded. No dataset supplied, so the synthetic scenario is the only data path and that is consistent with the dataset rule. |
| G5 | §2.1 contains the stray token "of Fos" | Copy glitch, ignored, documented so nobody re-litigates it. |
| G6 | The reference model formats are "organiser-defined" but the page names only ONNX and PyTorch/TorchScript | We support those two. If a third is issued, it is a P3 contract change. |

---

## 5. Six-line checklist for the PPT owner

1. Title slide carries PS id **SIH26228**, the full title, and the team name — nothing else.
2. Six slides maximum, PDF only, points and pictures; six sections in template order.
3. No percentage, no detection rate, no risk score on any slide unless it is a value a run printed.
4. Every external claim has a URL and an access date, or is not on the slide.
5. Slide 6 states out loud what CVAssure does **not** detect — the declared-unsupported rows.
6. The demo video is filmed and narrated by team members, never AI-generated.

**Verified text vs anecdote.** The PS quotes above, the dataset rule, §7.1's truncation, the
six-slide format and the no-AI-video rule are all **verified against a page or PDF on 30 September
2026**. Anything about "past winners", judging behaviour, or which theme scores well is **anecdote**
and has no URL, so it must not appear on a slide.

---

## Sources

All accessed 30 September 2026.

- SIH26228 problem statement — <https://sih2026.vuce.in/ps/SIH26228>
- Blockchain & Cybersecurity theme list — <https://sih2026.vuce.in/themes/blockchain-cybersecurity>
- SIH2026 idea presentation format — <https://www.scribd.com/document/1075380264/SIH2026-IDEA-Presentation-Format>
- Mirror of the same template — <https://studylib.net/doc/28802638/sih2026-idea-presentation-format--1->
- Guidelines of SIH2026 — <https://www.scribd.com/document/1077654176/Guidelines-of-SIH2026>
- BackdoorBench licence — <https://raw.githubusercontent.com/SCLBD/BackdoorBench/main/LICENSE>
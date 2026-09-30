# P1 DECISIONS — append-only log of resolved calls

Owner: Person 1 (lead / integration). Every row of `Person1_Complete_Plan.md` Section 0 lives
here verbatim in intent. **Do not re-litigate a row without a new dated entry below.**
Where this file disagrees with `Planning/Whole Team Plan.md` on product scope, mock-up
layout, palette, or the MVP command, the team plan wins and the clash is recorded at the
bottom of this file.

Plan source: `Person1_Complete_Plan.md`. Web facts cited there were accessed 30 September 2026.

---

## A. Section 0 resolved decisions (binding, copied day 1)

| Topic | Decision | Rejected |
|---|---|---|
| Problem | [SIH26228](https://sih2026.vuce.in/ps/SIH26228), MoD / Indian Army (DGIS), theme Blockchain & Cybersecurity, category Software. Title: *Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines*. | Generic PM plan in `gpt.md`. |
| Person 1 scope | Governance layer (PS §2.2.5) plus the spine: schema, detector contract, CLI, plugin loader, YAML policy, audit log, coverage statement, cross-asset link, repo/CI, two PPT images, research notes. | Qwen: Person 1 writes Trojan-detection policy rules and a TrojAI log-score harness. That work is Person 3 and Person 5. |
| C-07 | A **contributor id in the demo story**, not a teammate. Strings `C-07`, `C-01`, class `0` may appear only in demo fixtures, stub payloads, and tests. | Qwen treats C-07 as a person who ships triggers. Grok hard-codes `contributor_id: C-07` inside policy YAML. |
| Ground truth | The audit pipeline **never reads** Person 5's ground-truth manifest. Only coverage/evaluation code may. Linking uses detector evidence (`link_hints`) only. | Grok §2.6: linking and coverage both read `demo/manifest.json`. |
| Finding `asset` | `data` \| `model` \| `records` \| `shift` \| `system`. Shift is its own asset. `system` is only for a detector crash or skip that must still become a Finding. | Glm folds shift into `asset: data`. Gemini omits `shift`. |
| Schema dialect | JSON Schema **2020-12**, `additionalProperties: false` at the top level, free-form only inside `metadata`. Validate with Python `jsonschema` (`Draft202012Validator`). | Qwen: Node `ajv-cli` and Draft 7. Glm: Draft 7. |
| Finding shape | Flat optional fields (`source_id`, `batch_id`, `class_label`, `sample_ids`, `tags`, `link_hints`). Policy matches top-level keys. | Grok's nested `subject` object as the only shape. |
| Disposition owner | Detectors may propose. **Policy writes the final `disposition`.** Default for an emitted finding is `review`. `accept` only when a rule says so. Absence of a finding means nothing was flagged. | Claude's default `accept` (a high-severity finding with no matching rule would look clean). Gemini's automatic QUARANTINE of the model on a link (mock-up 1B says model: REVIEW). |
| Policy language | Declarative `when` / `then` with a fixed operator set. `yaml.safe_load` only. No `eval`, no `exec`, no `simpleeval`. | Gemini: `simpleeval`. |
| Plugin loader | Entry-point group `cvassure.detectors`, plus modules listed in config, plus built-in stubs if the real module is absent. | Gemini: `pluggy`. Extra dependency, different shape than the Detector class. |
| Crypto | Person 1 ships `LocalSha256Chain` (hash chain, no signatures) so nothing waits. Swap to Person 4's chain + Ed25519 when that module exists. Person 1 does **not** mint signing keys. | Gemini Phase 4: random `SigningKey` inside the audit logger. |
| Linking | Score from whatever evidence both sides actually have: same `patch_id`, class gate, bbox IoU, normalised cross-correlation. Implement NCC and IoU in NumPy. Do not add OpenCV to core. Threshold lives in config, starts uncalibrated, freezes only after negative controls. | Gemini: OpenCV multi-scale match at R > 0.75 as a fixed truth, and a new Finding that forces QUARANTINE. |
| Coverage status | Derived from Person 5's table by rules in config. No row means `Untested`, never `Supported`. Three attack classes stay `Unsupported` by declaration. | Glm: hard-label Supported from the mock-up before numbers exist. Gemini/Qwen: hand-written status. |
| Report hash | Two hashes. An HTML file cannot contain its own digest. See §9. | Single self-hash. |
| Demo video | Person 4 owns it. Person 1 does not generate a narrated video. SIH software-edition guidance says the demo video and its narration must not be AI-generated and must be delivered by team members ([Guidelines of SIH2026](https://www.scribd.com/document/1077654176/Guidelines-of-SIH2026)). | Qwen: Playwright + Edge TTS + Remotion pipeline. |
| PPT | Six slides including the title. PDF only. Person 1 does not build the deck. Slide map is the team plan (Section 14). | Qwen: 12-slide blueprint. A secondary launch summary uses a different six-slide split; do not follow it unless the PPT owner confirms the college template differs. |
| Timeline in `gpt.md` | Ignore. This is a hackathon MVP with the team-plan checkpoints (day 2 / 4 / 6 / 8 / 10), not an 8–12 week PM engagement. | ClickUp, Asana, paid boards. Use GitHub Issues or a markdown board. |
| Data | Public-licence data or synthetic data only. No classified, operational, or service-generated data. Person 1 fixtures are synthetic. | Downloading TrojAI model zoos or BackdoorBench weight dumps into this repo. |
| PS §7.1 | **Assumption A1 (binding).** The site ends mid-token at `adversarial-machi`. Read the whole clause as: use NIST TrojAI artefacts, BackdoorBench, and other reproducible public backdoor or adversarial-machine-learning material as *references*. No later section exists. Cite them in the coverage assumptions. Do not install them. | Blocking on a longer official sentence. Vendoring either repo. |

---

## B. Fills (plan Section 17) — answered 30 September 2026

| Fill | Answer | Note |
|---|---|---|
| Team name | `CVAssure` | plan default |
| Repo URL | this repo, `https://github.com/indalok/cvassure` | remote already set |
| GitHub handles | `P2`…`P5` placeholders, `HUMAN TODO` | human answered: keep placeholders |
| Python | 3.11 | `C:\Program Files\Python311\python.exe`; venv `.venv` in repo |
| License | MIT | human answered |
| Demo CPU | `cvassure doctor` output at run time | do not hand-write |
| Daily call time | `[[FILL]]` in `docs/p1/DAY1_MESSAGE.md` | human answered: leave unset |
| Package name | `cvassure` | plan default |

---

## C. Live environment facts (day 1, Windows host)

| Fact | Value |
|---|---|
| Host OS | Windows 11, build 22631 |
| Shell used for all commands | git-bash / MSYS. Repo lives at `C:\Users\Admin\Desktop\cvassure`. |
| Shell quirk (repo root) | `cd /c/Users/Admin/Desktop/cvaccure` fails in this bash; `cd /c/Users/Admin/Desktop && cd cvassure` works. Native tools need `C:/…` forward-slash paths. |
| Python | 3.11.9 at `C:\Program Files\Python311\python.exe`; 3.13 and 3.14 also on PATH. Use `.venv` (3.11). |
| Git | branch `main`, HEAD `4bcbbd6` "Initial commit", remote `origin https://github.com/indalok/cvassure` |
| Repo content at Phase 0 | only `README.md` (empty after `# CVAssure`). No `.gitignore`, no code. |

---

## D. Uncalibrated thresholds (plan §2.7, §8, §10, §11)

These are **starting values**, not results. They stay marked `UNCALIBRATED` until fitted on
seeded data that includes negative controls, and then get frozen in a dated row below.

| Threshold | Start value | Where | Frozen? |
|---|---|---|---|
| `tau_link` | 0.50 | `configs/demo.yaml` | NO — `UNCALIBRATED` |
| link weights (identity / overlap / pattern) | 0.5 / 0.2 / 0.3 | `configs/demo.yaml` | NO — `UNCALIBRATED` |
| `T_support` (detection mean) | 0.80 | `configs/coverage_rules.yaml` | NO — `UNCALIBRATED` |
| `T_far` (clean-control false alarm) | 0.05 | `configs/coverage_rules.yaml` | NO — `UNCALIBRATED` |
| min `n_seeds` for Supported | 3 | `configs/coverage_rules.yaml` | fixed by plan §11 |
| policy severity/confidence cut-offs (R1 0.8/0.6, R2 0.5) | as written | `policies/default.yaml` | NO — `UNCALIBRATED` |

---

## E. Open items and clashes

| # | Item | Status | Owner |
|---|---|---|---|
| E1 | SIH mirror page shows `Deadline 30 September 2026`. Unknown whether that is the portal close or only a listing date. | `HUMAN TODO` — confirm with SPOC. Do not invent a second deadline. | P1 + team lead |
| E2 | SIH2026 problem page at fetch time (30 Sep 2026) carried **no evaluation weights table**. | Re-fetch day 1; if weights appear, paste into `docs/research/sih_insights.md`. If still absent, record `no weights published` — never invent weights. | P1 |
| E3 | Two different six-slide PPT splits exist (team plan vs a launch summary). | PPT owner follows the file the SPOC issued. Flagged, not resolved. | PPT owner |
| E4 | `CODEOWNERS` handles are placeholders `P2`…`P5`. | `HUMAN TODO` | team lead |
| E5 | Google Slides / college template may change the slide count. | Re-check before deck build. | PPT owner |
| E6 | `docs/p1/` clash log vs `Planning/Whole Team Plan.md` | No clash found yet at Phase 0 — team plan not present in this repo. **If/when it lands, diff scope, mock-up layout, palette, and the MVP command against Section 0 and record here.** | P1 |
| E7 | Demo video: SIH software edition says video + narration must not be AI-generated and must be delivered by team members. | Person 4 owns the video. Person 1 produces no video. | P4 |

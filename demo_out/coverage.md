# CVAssure coverage statement

Status is derived from the results table by the rules in `configs/coverage_rules.yaml`. It is not written by hand.

| Attack class | Status | Measured | Access | n seeds |
|---|---|---|---|---|
| Adaptive attackers | Unsupported | ,  | ,  | ,  |
| Imperceptible clean-label perturbations | Unsupported | ,  | ,  | ,  |
| Hardware / compiler backdoors | Unsupported | ,  | ,  | ,  |
| Patch / blend trigger in data | Untested | ,  | ,  | ,  |
| Label flipping | Untested | ,  | ,  | ,  |
| Near-duplicate flooding | Untested | ,  | ,  | ,  |
| OOD insertion | Untested | ,  | ,  | ,  |
| Model substitution | Untested | ,  | ,  | ,  |
| Backdoored model | Untested | ,  | ,  | ,  |
| Record tampering / replay | Untested | ,  | ,  | ,  |
| Natural shift (fog vs patch) | Untested | ,  | ,  | ,  |
| Cross-asset linking | Untested | ,  | ,  | ,  |
| Run integrity | Partial | ,  | ,  | ,  |

> no results table at None. Every non-declared class is Untested

## Assumptions

- All development and evaluation data is publicly available under an applicable licence, or synthetic. No classified, operational, or service-generated data.
- NIST TrojAI benchmark artefacts, BackdoorBench, and other reproducible public backdoor or adversarial-machine-learning material are used as references for attack families only. They are not installed and no artefact from them is vendored.
- Baseline assessment does not retrain the contributed model. The subject model's weights are read and hashed, never updated.
- The audit runs offline and air-gapped. No cloud service, external API, or CDN is contacted.
- Thresholds in this file are UNCALIBRATED starting values and are not a validated detection capability.

> Thresholds in this statement are **UNCALIBRATED** starting values. They are not a validated detection capability.

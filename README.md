# CVAssure - Person 5: Shift and Attack Testbed

CVAssure is an offline, model-agnostic, evidence-based integrity assurance tool for computer-vision datasets, models, and inference records (SIH 2026).

## Person 5 Scope

Person 5 provides the **Shift and Attack Testbed**: seeded attack generators with ground truth, calibrated distribution shift assessment, a four-axis drift-versus-manipulation decision engine, and an automated benchmark harness.

### Quickstart

```bash
make setup
make test
make demo
```

Outputs will be saved in `out/scenarios`, `out/profile`, `out/shift`, `out/results`, and `out/figures`.

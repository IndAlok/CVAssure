SYNTHETIC FIXTURES. Nothing in this directory is real data.

- `findings/*.json` — hand-written Finding objects used as schema fixtures. The
  contributor id `C-07` and class `0` in them are demo-story fixture values.
- `dummy_findings.json` — SYNTHETIC. A copy of a day-2 stub run (seed 42), so
  Person 4 can build the dashboard before the real detectors land. Every finding
  in it carries `stub: true` and a `[STUB]` reason prefix. It is not a result.
- `synthetic_scenario.py` — builds a small COCO dataset split into a clean
  contributor and a poisoned one, a JSONL record file, and a real minimal ONNX
  graph. Person 5's `build_demo_scenario(seed=42)` replaces it.

No classified, operational, or service-generated data. No downloaded dataset. No
real photographs. Images are generated at test time, and the ONNX file is a
five-node-free `Identity` graph that carries no backdoor and no training.

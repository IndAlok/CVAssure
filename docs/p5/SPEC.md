# Person 5 MVP Build Spec: Shift and Attack Testbed

_CVAssure | SIH 2026 | Everything you must do, and the exact MVP to push to GitHub, written so an AI coding agent (Antigravity) can build it task by task_

## 1. Master Prompt
Work only inside these folders: `testbed/`, `shift/`, `bench/`, `tests/p5/`, `docs/p5/`.
Rules: Python 3.10 or newer, type hints and short docstrings on every public function. Core code may import only numpy, scipy, scikit-learn, pillow, opencv-python-headless, pandas, matplotlib, pyyaml and tqdm. torch and torchvision are optional and must be imported lazily inside functions. No network access at runtime except inside testbed/data.py when requested. Every random operation must use a numpy Generator created from an explicit seed passed as an argument; never use global random state. Outputs must be deterministic for the same seed. CPU only, keep memory under 4 GB. Write pytest tests for every module and run them; tests must pass with the environment variable CVASSURE_FAKE_DATA=1.

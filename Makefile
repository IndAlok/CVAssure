PY=python
setup:
	pip install -r requirements-core.txt
setup-extra:
	pip install -r requirements-extra.txt
test:
	CVASSURE_FAKE_DATA=1 pytest -q tests/p5
scenarios:
	$(PY) -m testbed.scenarios --all --seed 0 --n 3000 --out out/scenarios
profile:
	$(PY) -m shift.plugin --build-profile --seed 0 --out out/profile
shift-demo:
	$(PY) -m shift.plugin --timeline fog --seed 10 --profile out/profile --out out/shift
	$(PY) -m shift.plugin --timeline patch --seed 10 --profile out/profile --out out/shift
bench:
	$(PY) -m bench.run --seeds 10 11 12 --n 3000 --out out/results
figures:
	$(PY) -m bench.figures --results out/results --out out/figures
demo: scenarios profile shift-demo bench figures

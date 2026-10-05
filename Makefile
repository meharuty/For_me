PYTHON ?= python3
MAP ?= maps/hard/03_ultimate_challenge.txt

.PHONY: install run run-gui debug test benchmark clean lint lint-strict

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) main.py $(MAP)

run-gui:
	$(PYTHON) main.py $(MAP) --gui

debug:
	$(PYTHON) -m pdb main.py $(MAP) --plain

test:
	$(PYTHON) -m pytest -q

benchmark:
	$(PYTHON) benchmark.py

clean:
	find . -type d \( -name __pycache__ -o -name .mypy_cache \
		-o -name .pytest_cache \) -prune -exec rm -rf {} +
	rm -f .coverage

lint:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --strict

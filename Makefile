MAP ?= maps/hard/03_ultimate_challenge.txt

.PHONY: install run run-gui debug clean lint lint-strict

install:
	python3 -m pip install -r requirements.txt

run:
	python3 main.py $(MAP)

run-gui:
	python3 main.py $(MAP) --gui

debug:
	python3 -m pdb main.py $(MAP) --plain

clean:
	find . -type d \( -name __pycache__ -o -name .mypy_cache \
		-o -name .pytest_cache \) -prune -exec rm -rf {} +
	rm -f .coverage

lint:
	python3 -m flake8 .
	python3 -m mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	python3 -m flake8 .
	python3 -m mypy . --strict

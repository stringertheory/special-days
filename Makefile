PYTHON ?= .venv/bin/python
PIP    ?= .venv/bin/pip

.PHONY: help venv install hooks lint test test-live snapshot snapshot-live clean

help:
	@echo "Targets:"
	@echo "  venv           create .venv (python3 -m venv)"
	@echo "  install        editable install with dev extras into .venv"
	@echo "  hooks          wire up pre-commit git hooks"
	@echo "  lint           run pre-commit (ruff lint + format) on all files"
	@echo "  test           run unit tests (mocked, fast)"
	@echo "  test-live      run unit tests + live Wikidata tests"
	@echo "  snapshot       regenerate data/super_bowl.json from embedded list"
	@echo "  snapshot-live  regenerate data/super_bowl.json from live Wikidata"
	@echo "  clean          remove build artifacts and __pycache__"

venv:
	python3 -m venv .venv

install:
	$(PIP) install -e ".[dev]"

hooks:
	.venv/bin/pre-commit install

lint:
	.venv/bin/pre-commit run --all-files

test:
	$(PYTHON) -m unittest discover -s tests -v

test-live:
	SPECIAL_DAYS_LIVE_TESTS=1 $(PYTHON) -m unittest discover -s tests -v

snapshot:
	$(PYTHON) scripts/build_super_bowl_snapshot.py

snapshot-live:
	$(PYTHON) scripts/build_super_bowl_snapshot.py --live

clean:
	rm -rf build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +

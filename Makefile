PYTHON ?= .venv/bin/python
PIP    ?= .venv/bin/pip

.PHONY: help venv install hooks lint test test-live type-check \
        snapshot-super-bowl snapshot-oscars snapshots \
        publish-patch publish-minor publish-major _check_publish_ready \
        clean

help:
	@echo "Targets:"
	@echo "  venv                  create .venv (python3 -m venv)"
	@echo "  install               editable install with dev extras into .venv"
	@echo "  hooks                 wire up pre-commit git hooks"
	@echo "  lint                  run pre-commit (ruff lint + format) on all files"
	@echo "  type-check            run mypy on src/special_days"
	@echo "  test                  run unit tests (mocked, fast)"
	@echo "  test-live             run unit tests + live Wikidata tests"
	@echo "  snapshot-super-bowl   regenerate data/super_bowl.json from Wikidata"
	@echo "  snapshot-oscars       regenerate data/oscars.json from Wikidata"
	@echo "  snapshots             regenerate every snapshot from Wikidata"
	@echo "  publish-patch         bump patch (x.y.Z+1), commit, tag, push"
	@echo "  publish-minor         bump minor (x.Y+1.0), commit, tag, push"
	@echo "  publish-major         bump major (X+1.0.0), commit, tag, push"
	@echo "  clean                 remove build artifacts and __pycache__"

venv:
	python3 -m venv .venv

install:
	$(PIP) install -e ".[dev]"

hooks:
	.venv/bin/pre-commit install

lint:
	.venv/bin/pre-commit run --all-files

type-check:
	$(PYTHON) -m mypy src/special_days

test:
	$(PYTHON) -m unittest discover -s tests -v

test-live:
	SPECIAL_DAYS_LIVE_TESTS=1 $(PYTHON) -m unittest discover -s tests -v

snapshot-super-bowl:
	$(PYTHON) scripts/build_snapshot.py super_bowl

snapshot-oscars:
	$(PYTHON) scripts/build_snapshot.py oscars

snapshots: snapshot-super-bowl snapshot-oscars

# --- release ---------------------------------------------------------------
# `make publish-{patch,minor,major}` bumps pyproject.toml, commits, tags
# vX.Y.Z, and pushes. The pushed tag triggers .github/workflows/release.yml,
# which builds + uploads to PyPI via OIDC trusted publishing.
#
# Requires `uv` on PATH (https://docs.astral.sh/uv/). `--frozen` skips
# re-locking since we don't ship a uv.lock; pip drives our installs.

_check_publish_ready:
	@command -v uv >/dev/null || { echo "uv not found on PATH; install from https://docs.astral.sh/uv/"; exit 1; }
	@[ "$$(git rev-parse --abbrev-ref HEAD)" = "main" ] || { echo "must be on main branch"; exit 1; }
	@git diff --quiet && git diff --cached --quiet || { echo "working tree dirty; commit or stash first"; exit 1; }
	@git fetch origin main --quiet
	@[ "$$(git rev-parse HEAD)" = "$$(git rev-parse origin/main)" ] || { echo "local main is not at origin/main; pull or push first"; exit 1; }

publish-patch publish-minor publish-major: _check_publish_ready test type-check
	@kind="$(@:publish-%=%)" && \
		new=$$(uv version --bump $$kind --short --frozen) && \
		echo "Releasing v$$new..." && \
		git add pyproject.toml && \
		git commit -m "Release v$$new" && \
		git tag -a "v$$new" -m "v$$new" && \
		git push origin main && \
		git push origin "v$$new"

clean:
	rm -rf build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +

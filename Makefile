PYTHON := python3
VENV := .venv
VENV_PY := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip

.PHONY: help venv build serve serve-drafts clean

help:
	@echo "Targets:"
	@echo "  make build         Build the site into dist/ (drafts excluded)"
	@echo "  make serve         Build and preview at http://127.0.0.1:8000"
	@echo "  make serve-drafts  Build including draft pages, then preview"
	@echo "  make clean         Remove dist/"

$(VENV_PY): requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install -r requirements.txt

venv: $(VENV_PY)

build: $(VENV_PY)
	$(VENV_PY) build.py

serve: $(VENV_PY)
	$(VENV_PY) serve.py

serve-drafts: $(VENV_PY)
	$(VENV_PY) serve.py --drafts

clean:
	rm -rf dist

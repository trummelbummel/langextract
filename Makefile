.PHONY: env test

VENV := langextract_env
PYTHON := python3

env:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/pip install -e .

test:
	$(VENV)/bin/pip install "setuptools>=77.0" wheel -e ".[openai,dev,test]"
	$(VENV)/bin/pytest tests -m "not live_api and not integration"

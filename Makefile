.PHONY: env test test-pip ollama

VENV := langextract_env
PYTHON := python3
OLLAMA_URL ?= http://localhost:11434
OLLAMA_MODEL ?= gemma2:2b
# Seconds to keep the model loaded (-1 = until the server stops).
OLLAMA_KEEP_ALIVE ?= 300
# Must match the num_ctx langextract sends, or its first call reloads the model.
OLLAMA_NUM_CTX ?= 2048

env:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/pip install -e .
	@echo "Starting a shell with $(VENV) activated (type 'exit' to leave)..."
	@. $(VENV)/bin/activate && exec $${SHELL:-/bin/sh} -i

test:
	$(VENV)/bin/pip install "setuptools>=77.0" wheel -e ".[openai,dev,test]"
	$(VENV)/bin/pytest tests -m "not live_api and not integration and not requires_pip"

test-pip:
	$(VENV)/bin/pip install "setuptools>=77.0" wheel -e ".[openai,dev,test]"
	$(VENV)/bin/pytest tests -m requires_pip

# Load the Ollama model before a run and print how long the load took.
ollama:
	@curl -sS $(OLLAMA_URL)/api/generate -d '{"model": "$(OLLAMA_MODEL)", "prompt": "hi", "stream": false, "keep_alive": $(OLLAMA_KEEP_ALIVE), "options": {"num_predict": 1, "num_ctx": $(OLLAMA_NUM_CTX)}}' \
	  | $(PYTHON) -c 'import json, sys; r = json.load(sys.stdin); sys.exit(r["error"]) if "error" in r else print("$(OLLAMA_MODEL): load %.2f s, total %.2f s" % (r["load_duration"] / 1e9, r["total_duration"] / 1e9))'

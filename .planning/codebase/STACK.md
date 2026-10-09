---
last_mapped_commit: a4c0aa4c1be98f441ffc7e1d0f85b1067748e1f3
last_mapped_at: 2026-10-09
---
<!-- refreshed: 2026-10-09 -->

# Technology Stack

**Analysis Date:** 2026-10-09

## Languages

**Primary:**

- Python `>=3.10` — the entire library in `langextract/`, tests in `tests/`, benchmarks in `benchmarks/`, and scripts in `scripts/`. Declared in `pyproject.toml` (`requires-python = ">=3.10"`). CI matrix in `.github/workflows/ci.yaml` runs `3.10`, `3.11`, and `3.12`. Tox environments in `tox.ini` are `py310`, `py311`, `py312`.

**Secondary:**

- Bash — `autoformat.sh` runs isort, pyink, and pre-commit. `.github/scripts/revalidate-all-prs.sh`, `.github/scripts/add-size-labels.sh`, and `.github/scripts/add-new-checks.sh` are GitHub Actions helpers.
- YAML — GitHub Actions under `.github/workflows/`, `tox.ini` is INI, provider config and prompts use PyYAML (`langextract/prompting.py`, `langextract/core/format_handler.py`, `langextract/core/base_model.py`).
- HTML (generated, not a web app) — `langextract/visualization.py` builds an HTML visualization for notebooks. Static concept page: `docs/_static/langextract_concept.html`.
- Jupyter — `examples/notebooks/romeo_juliet_extraction.ipynb`. Optional extra `notebook` in `pyproject.toml`.

No TypeScript, JavaScript application, Go, or Rust sources.

## Runtime

**Environment:**

- CPython 3.10–3.12. No `.python-version` or `.nvmrc`.
- Production image `Dockerfile` uses `python:3.10-slim` and installs the published package (`pip install --no-cache-dir langextract`).
- Ollama demo image `examples/ollama/Dockerfile` uses `python:3.11-slim-bookworm`.
- Inference parallelism uses `concurrent.futures.ThreadPoolExecutor` in `langextract/providers/gemini.py` and `langextract/providers/openai.py` (`max_workers`, default 10). Ollama calls in `langextract/providers/ollama.py` are sequential HTTP requests.

**Package Manager:**

- pip, driven by `pyproject.toml`. Install the library with `pip install -e .`, development tools with `pip install -e ".[dev]"`, tests with `pip install -e ".[test]"`, and OpenAI with `pip install -e ".[openai]"` (alias extra `all`).
- Lockfile: missing. There is no `requirements.txt`, `uv.lock`, `poetry.lock`, or `Pipfile.lock`. Dependency floors are the lower bounds in `pyproject.toml`.

## Frameworks

**Core:**

- No web framework, ORM, or application server. LangExtract is a library. Public entry is `langextract.extract` and `langextract.visualize` in `langextract/__init__.py`, implemented by `langextract/extraction.py` and `langextract/visualization.py`.
- Provider plugin system uses setuptools entry points, group `langextract.providers`, declared in `pyproject.toml` and loaded by `langextract/providers/__init__.py` and `langextract/plugins.py`.
- Data models are `@dataclasses.dataclass` types in `langextract/core/data.py` and `langextract/core/types.py`. Pydantic is used narrowly: `pydantic.TypeAdapter` in `langextract/prompting.py`, and `pydantic.BaseModel` JSON encoding in `langextract/providers/gemini_batch.py`.

**Testing:**

- pytest `>=7.4.0` — config in `pyproject.toml` under `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, files `test_*.py` and `*_test.py`).
- tox `>=4.0` — `tox.ini` orchestrates unit tests, format, lint, live API, Ollama, and plugin jobs.
- unittest.mock — provider tests patch `os.environ` and HTTP/SDK clients (for example `tests/factory_test.py`, `tests/gemini_retry_test.py`).

**Build/Dev:**

- setuptools `>=67.0.0` + wheel — `[build-system]` in `pyproject.toml`. `build-backend = "setuptools.build_meta"`. Packages are listed explicitly under `[tool.setuptools]` (`langextract`, `langextract._compat`, `langextract.core`, `langextract.providers`, `langextract.providers.schemas`).
- `python -m build` and `twine check` — release job `.github/workflows/publish.yml`.
- pyink `==24.3.0` — Google Black fork. `[tool.pyink]` sets `line-length = 80`, `pyink-indentation = 2`, `pyink-use-majority-quotes = true`.
- isort `==5.13.2` — `[tool.isort]` profile `google`, line length 80.
- pylint `>=3.0.0` — `.pylintrc` for `langextract/`, `tests/.pylintrc` for tests. Tox envs `lint-src` and `lint-tests`.
- pytype `>=2024.10.11` — declared in the `dev` extra. Inline `# pytype:` directives appear in `langextract/visualization.py` and `tests/data_lib_test.py`. No `pytype` tox env.
- import-linter `>=2.0` (CI pins `import-linter==2.11` in `.github/workflows/ci.yaml`) — contracts in `[tool.importlinter]` of `pyproject.toml`. Run with `lint-imports --config pyproject.toml`.
- pre-commit `>=3.5.0` — `.pre-commit-config.yaml` (isort, pyink, and `pre-commit-hooks` `v4.5.0`).
- `./autoformat.sh` — local formatter entry point.

## Key Dependencies

**Critical:**

- `google-genai>=1.39.0` — Gemini Developer API and Vertex AI client. `langextract/providers/gemini.py` constructs `google.genai.Client` and calls `client.models.generate_content`. `langextract/providers/gemini_batch.py` calls `client.batches.create` / `get` / `cancel`.
- `google-cloud-storage>=2.14.0` — GCS upload and download for Vertex AI batch jobs in `langextract/providers/gemini_batch.py` (`from google.cloud import storage`).
- `openai>=1.50.0` — optional extra `openai` and `all`. Imported inside `OpenAILanguageModel.__init__` in `langextract/providers/openai.py`. Missing install raises `InferenceConfigError` with the message to `pip install langextract[openai]`.
- `requests>=2.25.0` — Ollama HTTP client in `langextract/providers/ollama.py` (`POST` to `api/generate` and `api/chat`). Also `langextract/io.py` `download_text_from_url` and the Zenodo script `.github/scripts/zenodo_publish.py`.
- `pydantic>=1.8.0` — prompt template validation (`langextract/prompting.py`) and Gemini batch JSON encoding (`langextract/providers/gemini_batch.py`).
- `PyYAML>=6.0` — YAML prompt and model output parsing (`langextract/core/format_handler.py`, `langextract/prompting.py`, `langextract/core/base_model.py`).
- `regex>=2023.0.0` — Unicode tokenization in `langextract/core/tokenizer.py`. Dev extra also installs `types-regex>=2023.0.0`.
- `pandas>=1.3.0` — CSV dataset loading in `langextract/io.py` (`pd.read_csv` inside `_read_csv`).
- `absl-py>=1.0.0` — `from absl import logging` across providers, chunking, annotation, and the resolver.
- `tqdm>=4.64.0` — progress bars in `langextract/progress.py`.
- `more-itertools>=8.0.0` — chunk windows in `langextract/chunking.py`.
- `python-dotenv>=0.19.0` — `dotenv.load_dotenv` in `tests/test_live_api.py`, `benchmarks/benchmark.py`, `examples/ollama/demo_ollama.py`, and `examples/custom_provider_plugin/test_example_provider.py`. The library itself does not call `load_dotenv`; callers export variables or load a `.env` before `lx.extract`.
- `typing-extensions>=4.0.0` — `override` and related typing helpers (used in `langextract/prompting.py`).

**Declared but not imported by current library code:**

These floors are runtime dependencies in `pyproject.toml` and install with the package. No `langextract/` or `tests/` module imports them today:

- `aiohttp>=3.8.0`
- `async_timeout>=4.0.0`
- `exceptiongroup>=1.1.0`
- `ml-collections>=0.1.0`
- `numpy>=1.20.0` — imported only by `tests/data_lib_test.py` and `benchmarks/plotting.py`, not by `langextract/*.py`

Do not add a new caller for these without a real use. Do not remove them in a drive-by change; they are part of the published dependency set.

**Transitive imports the library relies on (not direct `pyproject.toml` entries):**

- `google.api_core.exceptions` — imported in `langextract/providers/gemini_batch.py` for GCS `Conflict` when creating the batch bucket. Comes with `google-cloud-storage`.
- `httpx` — optional import in `langextract/providers/gemini.py` to classify retryable transport errors (`TimeoutException`, `NetworkError`, `RemoteProtocolError`, `ProxyError`). Comes with `google-genai`.

**Infrastructure:**

- Docker — `Dockerfile` (library image) and `examples/ollama/Dockerfile` plus `examples/ollama/docker-compose.yml` (Ollama `0.5.4` bound to `127.0.0.1:11434`).
- GitHub Actions — CI, publish, and repository policy workflows under `.github/workflows/`.
- matplotlib — imported by `benchmarks/plotting.py` (`matplotlib.use("Agg")`) and **not** listed in `pyproject.toml`. Install it only when running benchmark plots.

**Dev and test extras (do not ship as required runtime deps):**

| Extra | Packages | Use |
| --- | --- | --- |
| `dev` | pyink `24.3.0`, isort `5.13.2`, pylint, pytype, tox, import-linter, pre-commit, types-regex | Format, lint, type check |
| `test` | pytest `>=7.4.0`, tomli `>=2.0.0` | `tests/` |
| `notebook` | ipython `>=7.0.0`, notebook `>=6.0.0` | `examples/notebooks/` |
| `openai` / `all` | openai `>=1.50.0` | `langextract/providers/openai.py` |

## Configuration

**Environment:**

Resolve provider credentials in `langextract/factory.py` `_kwargs_with_environment_defaults` before constructing a model. Pass an explicit `api_key` or `language_model_params` when the environment must not win.

| Variable | Read by | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | `langextract/factory.py` | Gemini API key. Preferred over `LANGEXTRACT_API_KEY` when both are set. |
| `LANGEXTRACT_API_KEY` | `langextract/factory.py`, `README.md` | Shared fallback key for Gemini and OpenAI model-id patterns. |
| `OPENAI_API_KEY` | `langextract/factory.py` | OpenAI key for `gpt-*` and `o[1-9]*` model ids. |
| `OLLAMA_BASE_URL` | `langextract/factory.py` | Ollama base URL when the model id contains `ollama`. Default `http://localhost:11434`. |
| `OLLAMA_HOST` | `examples/ollama/demo_ollama.py` only | Demo script default. Compose sets `OLLAMA_HOST=http://ollama:11434` in `examples/ollama/docker-compose.yml`. The library factory does **not** read `OLLAMA_HOST`. |
| `LANGEXTRACT_DISABLE_PLUGINS` | `langextract/providers/__init__.py` | Set to `1`, `true`, or `yes` to skip third-party entry points. |
| `GOOGLE_CLOUD_PROJECT` | `langextract/providers/gemini_batch.py` | GCS project for Vertex batch when the genai client has no `project`. |
| `GOOGLE_APPLICATION_CREDENTIALS` | tox `live-api` env in `tox.ini` | ADC file path passed through to live tests. Vertex mode itself takes a `credentials` object, `project`, and `location` in `langextract/providers/gemini.py`. |
| `VERTEX_PROJECT`, `GOOGLE_CLOUD_PROJECT`, `VERTEX_LOCATION` | `tests/test_live_api.py`, `tox.ini` | Live Vertex tests only. Default location in tests is `us`. Library default location is `us-central1` (`_DEFAULT_LOCATION` in `langextract/providers/gemini.py`). |
| `LANGEXTRACT_RUN_OPENAI_BATCH_LIVE_TESTS` | `tests/test_live_api.py` | Must be `1` to run live OpenAI Batch tests. |
| `ZENODO_TOKEN`, `ZENODO_RECORD_ID` | `.github/scripts/zenodo_publish.py` | Release DOI publish. GitHub Actions secrets, not library config. |

`.env` is listed in `.gitignore`. The working tree does not commit one. Load it in user code or in the scripts above with `python-dotenv` before calling `lx.extract`. Do not commit key values.

Gemini client construction (`langextract/providers/gemini.py`):

```python
self._client = genai.Client(
    api_key=self.api_key,
    vertexai=vertexai,
    credentials=credentials,
    project=project,
    location=location,
    http_options=http_options,
)
```

Vertex mode requires `vertexai=True` plus both `project` and `location`. Supplying both an API key and Vertex config logs a warning and lets the API key take precedence.

**Build:**

- `pyproject.toml` — project metadata (`name = "langextract"`, `version = "1.7.1"`, Apache-2.0), dependencies, extras, entry points, pytest, pyink, isort, import-linter.
- `tox.ini` — test and lint environments.
- `.pylintrc`, `tests/.pylintrc` — pylint.
- `.pre-commit-config.yaml` — hook pins.
- `Dockerfile`, `examples/ollama/Dockerfile`, `examples/ollama/docker-compose.yml` — container images.
- `examples/custom_provider_plugin/pyproject.toml` — sample plugin package `langextract-provider-example` with its own `langextract.providers` entry point. It is an example, not the published library.

Provider registration (built-ins) in `pyproject.toml`:

```toml
[project.entry-points."langextract.providers"]
gemini = "langextract.providers.gemini:GeminiLanguageModel"
ollama = "langextract.providers.ollama:OllamaLanguageModel"
openai = "langextract.providers.openai:OpenAILanguageModel"
```

Model-id routing patterns live in `langextract/providers/patterns.py` and are registered from `langextract/providers/builtin_registry.py`. Gemini matches `^gemini` (priority 10). OpenAI matches `^gpt-3\.5`, `^gpt-4`, `^gpt4\.`, `^gpt-5`, `^gpt5\.`, and `^o[1-9]` (priority 10). Ollama matches local names (`^llama`, `^gemma`, `^mistral`, …) and Hugging Face-style ids (`^meta-llama/[Ll]lama`, `^google/gemma`, …).

`[tool.setuptools.package-data]` lists `langextract/py.typed`, but that marker file is not in the tree. Add `langextract/py.typed` before relying on the package as typed for downstream checkers.

## Platform Requirements

**Development:**

- Python 3.10, 3.11, or 3.12.
- pip and a virtualenv (`python -m venv`, see `README.md`).
- For format checks: `pip install -e ".[dev]"` then `./autoformat.sh` or `tox -e format`.
- For unit tests: `pip install -e ".[openai,dev,test]"` then `tox` (default env skips `live_api`, `requires_pip`, and `integration` markers) or `pytest -ra -m "not live_api and not requires_pip and not integration"`.
- For Ollama: a local server (default `http://localhost:11434`) or `examples/ollama/docker-compose.yml`. Pull a model with `ollama pull` before extraction (`langextract/providers/ollama.py` documents `gemma2:2b`).
- For Gemini or OpenAI live tests: API keys in the environment and `tox -e live-api` (base Python 3.11).
- Google CLA is required for contributions (`CONTRIBUTING.md`).

**Production:**

- Library distribution on PyPI via trusted publishing (OIDC) in `.github/workflows/publish.yml` (`pypa/gh-action-pypi-publish`, environment `pypi`). Trigger: GitHub Release `published`.
- Run as an imported library inside the caller’s process. There is no long-running service in this repo.
- Container option: build `Dockerfile` (`python:3.10-slim`) and pass `LANGEXTRACT_API_KEY` at `docker run` (see `README.md`).
- Zenodo DOI publish on non-prerelease tags from `google/langextract` via `.github/workflows/zenodo-publish.yml` and `.github/scripts/zenodo_publish.py`. Concept DOI is declared in `pyproject.toml` (`https://doi.org/10.5281/zenodo.17015089`).
- Citation metadata: `CITATION.cff`.

---

*Stack analysis: 2026-10-09*

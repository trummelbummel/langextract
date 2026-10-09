---
last_mapped_commit: a4c0aa4c1be98f441ffc7e1d0f85b1067748e1f3
last_mapped_at: 2026-10-09
---
<!-- refreshed: 2026-10-09 -->

# External Integrations

**Analysis Date:** 2026-10-09

## APIs & External Services

**LLM providers (built-in):**

Route a call by model id through `langextract/factory.py` `create_model`, which calls `langextract/providers/router.py`. Patterns and priorities are in `langextract/providers/patterns.py`. Built-in classes are listed in `langextract/providers/builtin_registry.py`.

- Google Gemini Developer API — synchronous structured extraction.
  - SDK/Client: `google-genai` (`google.genai.Client`) in `langextract/providers/gemini.py`.
  - Call: `client.models.generate_content(model=..., contents=prompt, config=...)`.
  - Default model id: `gemini-3.5-flash` (`_DEFAULT_MODEL_ID`).
  - Auth: `api_key` argument, or `GEMINI_API_KEY`, then `LANGEXTRACT_API_KEY` (`langextract/factory.py`). Key signup is documented as AI Studio in `README.md`.
  - Schema: `langextract/providers/schemas/gemini.py` (`GeminiSchema`) sets JSON MIME type and response schema.
  - Retries: provider loop in `GeminiLanguageModel._process_single_prompt` (default 3 retries, base delay 1s, cap 16s, jitter). Retryable HTTP codes are 408, 429, 500, 502, 503, 504. Do not also set `http_options.retry_options` with `max_retries > 0`; `__init__` raises `InferenceConfigError` when both are set.
  - Parallelism: `ThreadPoolExecutor` with `max_workers` (default 10).

- Vertex AI (Gemini on Google Cloud) — same `GeminiLanguageModel`, different client mode.
  - SDK/Client: `google.genai.Client(vertexai=True, project=..., location=..., credentials=...)` in `langextract/providers/gemini.py`.
  - Auth: Application Default Credentials or an explicit `credentials` object. Requires `project` and `location`. Default location constant is `us-central1`.
  - Env (live tests and batch fallback, not a substitute for constructor args in realtime mode): `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`, `VERTEX_PROJECT`, `VERTEX_LOCATION` (`tox.ini`, `tests/test_live_api.py`).
  - Batch: `langextract/providers/gemini_batch.py` submits `client.batches.create` only when `client.vertexai is True`. Input JSONL is uploaded to GCS; results are read back from a `gs://` URI. Bucket name pattern is `langextract-{project}-{location}-batch` (`_get_bucket_name`). Optional `retention_days` adds a GCS lifecycle delete rule.
  - Console links logged from `gemini_batch.py`: Vertex batch predictions and Cloud Storage browser URLs. Those are log output, not webhooks.

- OpenAI Chat Completions — optional extra.
  - SDK/Client: `openai.OpenAI` in `langextract/providers/openai.py` (`chat.completions.create`).
  - Auth: `api_key` required at init. Factory fills it from `OPENAI_API_KEY`, then `LANGEXTRACT_API_KEY`, for model ids matching `gpt` or `^o[1-9]`.
  - Optional: `base_url` (OpenAI-compatible servers), `organization` (OpenAI-Organization).
  - Default model id: `gpt-4o-mini`.
  - Schema: `langextract/providers/schemas/openai.py` (`OpenAISchema`) via `response_format`.
  - Batch: `langextract/providers/openai_batch.py` uses the client `files` and `batches` resources. Default endpoint string is `/v1/chat/completions`, completion window `24h`, threshold 50 prompts, poll interval 10s, max 50,000 requests per job. Opt in with `language_model_params["batch"]`. Live coverage is gated by `LANGEXTRACT_RUN_OPENAI_BATCH_LIVE_TESTS=1` in `tests/test_live_api.py`.
  - Install: `pip install langextract[openai]`. The provider raises `InferenceConfigError` if `import openai` fails.

- Ollama — local or proxied HTTP, no SDK.
  - Client: `requests` in `langextract/providers/ollama.py`.
  - Base URL: constructor `model_url` or `base_url`, else `http://localhost:11434` (`_OLLAMA_DEFAULT_MODEL_URL`). Factory sets `base_url` from `OLLAMA_BASE_URL` when the model id contains `ollama` (`langextract/factory.py`).
  - Endpoints: `POST {base}/api/generate` for normal generation; `POST {base}/api/chat` for `gpt-oss` JSON mode (`_ollama_gpt_oss_chat_query`).
  - Auth: none by default. For a proxy, pass `api_key` (and optional `auth_scheme`, default `Bearer`, header `Authorization`) through `language_model_params`. Headers are built in `_request_headers`. `__repr__` redacts the key.
  - Timeout default: 120 seconds. `keep_alive` default 300 seconds. `num_ctx` default 2048.
  - Demo stack: `examples/ollama/docker-compose.yml` runs `ollama/ollama:0.5.4` on `127.0.0.1:11434` and sets `OLLAMA_HOST=http://ollama:11434` for `examples/ollama/demo_ollama.py` only.

**Community provider plugins (not installed by this repo):**

Third-party packages register the same entry-point group `langextract.providers`. Discovery is in `langextract/plugins.py` and `langextract/providers/__init__.py`. Disable with `LANGEXTRACT_DISABLE_PLUGINS=1|true|yes`. The registry table is `COMMUNITY_PROVIDERS.md`:

| Package | Backend |
| --- | --- |
| `langextract-bedrock` | AWS Bedrock |
| `langextract-litellm` | LiteLLM (OpenAI, Azure, Anthropic, and other LiteLLM providers) |
| `langextract-llamacpp` | llama.cpp / GGUF |
| `langextract-outlines` | Outlines structured generation |
| `langextract-vllm` | vLLM |

Do not import these from `langextract/`. Document new plugins in `COMMUNITY_PROVIDERS.md`; `.github/workflows/validate-community-providers.yaml` runs `scripts/validate_community_providers.py` when that file changes. The in-repo sample is `examples/custom_provider_plugin/` (entry point `custom_gemini` → `langextract_provider_example:CustomGeminiProvider`).

**Generic HTTP input fetch:**

- `lx.extract` accepts an `http://` or `https://` string. `langextract/extraction.py` calls `io.is_url` and `io.download_text_from_url` (`langextract/io.py`).
- Client: `requests.get` (streamed, 30s default timeout, 8 KiB chunks).
- Auth: none. The caller’s URL is fetched as-is. `is_url` allows IP hosts and `localhost`.
- Response must decode as text (utf-8, latin-1, ascii, utf-16). Content types other than `text/`, `application/json`, and `application/xml` warn and still download.

**Citation and archive (release automation only):**

- Zenodo / InvenioRDM — `.github/scripts/zenodo_publish.py` calls `https://zenodo.org/api` with `requests`.
  - Auth: `Authorization: Bearer` from `ZENODO_TOKEN`. Record id from `ZENODO_RECORD_ID`.
  - Trigger: `.github/workflows/zenodo-publish.yml` on GitHub Release `published` (skips prereleases and forks) or `workflow_dispatch`.
  - Accept header: `application/vnd.inveniordm.v1+json`.
  - Not used at library runtime.

## Data Storage

**Databases:**

- Not detected. No SQL, ORM, or database client in `langextract/`.

**File Storage:**

- Local filesystem is the default annotation store.
  - Write JSONL with `save_annotated_documents` in `langextract/io.py`. Default directory is `test_output/` when `output_dir` is omitted. Default file name is `data.jsonl`.
  - Read JSONL with `load_annotated_documents_jsonl`.
  - Read CSV inputs with `Dataset.load` → `_read_csv` (`pandas.read_csv`, `dtype=str`). Only `.csv` is implemented; other suffixes raise `NotImplementedError`.
- Google Cloud Storage — Vertex AI batch only (`langextract/providers/gemini_batch.py`).
  - Client: `storage.Client(project=project)`.
  - Objects: `batch-input/{display}-{uuid}.jsonl` uploaded with `blob.upload_from_filename`. Outputs downloaded from the job’s GCS URI.
  - Auth: the same Google Cloud project credentials as the Vertex client (`GOOGLE_CLOUD_PROJECT` fallback).

**Caching:**

- None. No Redis, Memcached, or on-disk response cache. Vertex batch GCS objects are job inputs and outputs, not a cache. Optional bucket lifecycle deletion is cost control, not a cache policy.

## Authentication & Identity

**Auth Provider:**

- No end-user identity provider. The library does not implement login, sessions, or OAuth for application users.

**Credential patterns to follow:**

- Cloud LLMs: environment variables resolved in `langextract/factory.py`, or an explicit `api_key` / `language_model_params` on `lx.extract`. Provider-specific variables win over `LANGEXTRACT_API_KEY`. If both are set, factory emits `UserWarning` and uses the first match.
- Gemini without a key: Vertex AI (`vertexai=True`, `project`, `location`, optional `credentials`) in `langextract/providers/gemini.py`.
- OpenAI: key is mandatory in `OpenAILanguageModel.__init__`. There is no unauthenticated mode.
- Ollama: unauthenticated local HTTP. Optional bearer (or raw) header for proxies (`langextract/providers/ollama.py` `_request_headers`).
- Release jobs: GitHub Actions secrets (`GEMINI_API_KEY`, `OPENAI_API_KEY` in `.github/workflows/ci.yaml`; `ZENODO_TOKEN`, `ZENODO_RECORD_ID` in `.github/workflows/zenodo-publish.yml`). PyPI publish uses GitHub OIDC (`id-token: write`, `pypa/gh-action-pypi-publish`) in `.github/workflows/publish.yml`, not a long-lived token in the workflow file.
- `.env` files: gitignored (`.gitignore`). Load with `python-dotenv` in user scripts, tests, and benchmarks. Do not commit values.

## Monitoring & Observability

**Error Tracking:**

- None. No Sentry, Datadog, or OpenTelemetry SDK.

**Logs:**

- `absl.logging` (`absl-py`) in providers, `langextract/annotation.py`, `langextract/chunking.py`, `langextract/resolver.py`, `langextract/plugins.py`, and `langextract/providers/gemini_batch.py`.
- Stdlib `logging` in `langextract/providers/openai.py`, `langextract/providers/openai_batch.py`, and `langextract/core/debug_utils.py` (which also imports absl).
- Gemini batch logs the Vertex console URL and GCS browser URL at info level (`langextract/providers/gemini_batch.py`).
- User-facing progress is `tqdm` via `langextract/progress.py` (save, load, download). `show_progress=False` disables bars.
- Failures surface as `langextract.core.exceptions` types (`InferenceConfigError`, `InferenceRuntimeError`, `LangExtractError`) rather than swallowed HTTP errors. Provider runtime errors set `provider=` (`'Gemini'`, `'Ollama'`).

## CI/CD & Deployment

**Hosting:**

- PyPI project `langextract` (version `1.7.1` in `pyproject.toml`). Homepage and issue tracker: `https://github.com/google/langextract`.
- Optional Docker image from `Dockerfile` (installs the PyPI package, not the local tree).
- No application hosting platform (no Cloud Run, App Engine, Kubernetes manifests, or serverless config).

**CI Pipeline:**

- GitHub Actions on `ubuntu-latest`.

| Workflow | File | Role |
| --- | --- | --- |
| CI | `.github/workflows/ci.yaml` | On push/PR to `main`: pyink, isort, `lint-imports`, tox unit tests and pylint on Python 3.10–3.12, live API tests (same-repo PRs and pushes only, skipped when both API secrets are empty), plugin integration when provider files change. `tj-actions/changed-files` detects provider diffs. |
| Publish to PyPI | `.github/workflows/publish.yml` | On release published: `python -m build`, `twine check`, trusted publish. |
| Publish to Zenodo | `.github/workflows/zenodo-publish.yml` | On release published or manual dispatch: build sdist/wheel and run `.github/scripts/zenodo_publish.py`. |
| Validate Community Providers | `.github/workflows/validate-community-providers.yaml` | Table check for `COMMUNITY_PROVIDERS.md`. |
| Protect Infrastructure Files | `.github/workflows/check-infrastructure-changes.yml` | `pull_request_target` collaborator-permission check via GitHub REST. |
| PR size, linked issue, template, up-to-date, revalidate, auto-update | `.github/workflows/check-pr-size.yml`, `check-linked-issue.yml`, `validate_pr_template.yaml`, `check-pr-up-to-date.yaml`, `revalidate-pr.yml`, `auto-update-pr.yaml` | Repository policy. They call the GitHub API with `GITHUB_TOKEN` / `actions/github-script`. They are not product integrations. |

Python in CI is installed with `actions/setup-python` (format and live jobs use 3.11; unit tests use the matrix).

## Environment Configuration

**Required env vars:**

None are required to import the library. They become required when a provider is selected:

- Gemini API: `GEMINI_API_KEY` or `LANGEXTRACT_API_KEY` (or `api_key=`).
- OpenAI: `OPENAI_API_KEY` or `LANGEXTRACT_API_KEY` (or `api_key=`).
- Vertex AI: `project` and `location` arguments; credentials via ADC (`GOOGLE_APPLICATION_CREDENTIALS`) or a `credentials` object. Batch also needs permission to create and read the GCS bucket.
- Ollama: a reachable server. `OLLAMA_BASE_URL` only if it is not the default `http://localhost:11434`.
- Zenodo publish (CI only): `ZENODO_TOKEN`, `ZENODO_RECORD_ID`, plus `RELEASE_TAG` and `GITHUB_REPOSITORY` set by the workflow.

**Secrets location:**

- Local: process environment or a gitignored `.env` (`.gitignore` line `.env`). Never commit keys. `README.md` shows writing `LANGEXTRACT_API_KEY` into `.env`.
- CI: GitHub Actions secrets referenced in `.github/workflows/ci.yaml` and `.github/workflows/zenodo-publish.yml`. Live-test steps clear `GITHUB_TOKEN` before pytest (`GITHUB_TOKEN: ""` on the format and live jobs).
- PyPI: GitHub environment `pypi` with OIDC trusted publishing, not a stored API token in the workflow YAML.

## Webhooks & Callbacks

**Incoming:**

- None. There is no HTTP server, route table, or webhook handler in `langextract/`.

**Outgoing:**

- Gemini `generateContent` and Vertex batch APIs via `google-genai` (`langextract/providers/gemini.py`, `langextract/providers/gemini_batch.py`).
- GCS JSONL upload and download via `google-cloud-storage` (`langextract/providers/gemini_batch.py`).
- OpenAI Chat Completions and Batch/Files APIs via the `openai` SDK (`langextract/providers/openai.py`, `langextract/providers/openai_batch.py`). Optional custom `base_url`.
- Ollama `POST /api/generate` and `POST /api/chat` via `requests` (`langextract/providers/ollama.py`).
- Arbitrary caller-supplied `http(s)` document URLs via `requests.get` (`langextract/io.py` `download_text_from_url`, invoked from `langextract/extraction.py`).
- Zenodo REST (`https://zenodo.org/api`) from `.github/scripts/zenodo_publish.py` during release only.
- GitHub REST from Actions (`actions/github-script` and `github.rest` in `.github/workflows/ci.yaml` and `.github/workflows/check-infrastructure-changes.yml`). Not called by the library.

No outbound webhook subscriptions, Slack, Stripe, or email providers.

---

*Integration audit: 2026-10-09*

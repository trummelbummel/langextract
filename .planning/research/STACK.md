# Stack Research

**Domain:** One-call developer trace of an existing source-grounded extraction library (LangExtract) through local Ollama
**Researched:** 2026-10-09
**Confidence:** HIGH

The product stays `langextract` 1.7.1 (public alias `lx`). The milestone adds a script that calls `lx.extract` once against local `gemma3:4b` and prints prompt, chunk, model, parse, alignment, and the `AnnotatedDocument`. No new framework, provider, or HTTP client.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| CPython | 3.12 (library floor remains `>=3.10`) | Run the script | Newest interpreter this repo's CI and tox already test (`3.10`, `3.11`, `3.12`). 3.10 reached end of life on 2026-10-01, so use 3.12 for the script. Do not raise `requires-python` in this milestone. | HIGH |
| langextract | 1.7.1 (this tree, editable) | The pipeline being traced | Current PyPI release and the version in `pyproject.toml`. `lx.extract` in `langextract/extraction.py` already owns prompt, chunk, infer, parse, align, and `AnnotatedDocument`. Replacing it would hide the stages the script exists to show. | HIGH |
| Ollama server | `>=0.6`, already serving `gemma3:4b` | Local model host | The official `gemma3:4b` model card requires Ollama 0.6 or later. The model is the milestone's model. A newer upstream server (release line observed at v0.40.2) is fine when this model is already pulled. Do not upgrade the server as part of the script. | HIGH |
| `gemma3:4b` | tag `gemma3:4b` (digest `68ceab7e468a`, about 3.4GB on the model card) | The one model call | `^gemma` in `langextract/providers/patterns.py` routes this id to `OllamaLanguageModel`. 128k context on the model card. The provider does not use that window; see version compatibility. | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| `requests` | Floor `>=2.25.0` (already in `pyproject.toml`). Current PyPI release is 2.34.2 (`requires-python >=3.10`). | HTTP client inside `OllamaLanguageModel` | Do not add a second pin. `pip install -e .` already installs it. `OllamaLanguageModel._ollama_query` POSTs JSON to `/api/generate` with this library. A pre-flight `GET /api/tags` in the script can use the same client. | HIGH |
| stdlib `inspect` | CPython 3.12 | Name the owning function and file | Same module `langextract/core/debug_utils.py` already uses. `inspect.getfile` plus `__qualname__` is enough to print `function` and `file` for each stage. | HIGH |
| stdlib `pprint`, `dataclasses`, `functools` | CPython 3.12 | Print stage inputs and outputs | `Extraction` and `AnnotatedDocument` are dataclasses. `pprint.pp` shows them without a pretty-printer dependency. `functools.wraps` keeps the real function identity when the script wraps a stage for the duration of one process. | HIGH |

The script installs no packages of its own. `absl-py` (floor `>=1.0.0`, current PyPI 2.5.1), `PyYAML` (floor `>=6.0`, current 6.0.3), and `pydantic` (floor `>=1.8.0`, current 2.14.0) stay as library dependencies. The script does not import them to do the walkthrough.

### How the one call is shaped

Call the public function once:

- `model_id="gemma3:4b"` — required. The default in `extract` is `"gemini-3.5-flash"`.
- `model_url="http://localhost:11434"` — pass it explicitly. `factory._kwargs_with_environment_defaults` reads `OLLAMA_BASE_URL` only when the model id contains the substring `ollama`. `gemma3:4b` does not, so that variable does not select the host. The provider default is already `http://localhost:11434`.
- Leave `fence_output` and `use_schema_constraints` unset. `OllamaLanguageModel.get_schema_class` returns `FormatModeSchema`, which asks Ollama for JSON (`format: "json"`) and sets `requires_fence_output` false. The official README says the same thing.
- Do not pass `output_schema`. `FormatModeSchema.from_schema_dict` is unsupported, and the README states Ollama does not support `output_schema`.
- `extraction_passes=1` so the trace is one model call.
- Keep the sample short enough for the provider's context pin (below).

Stage owners the printer should name, all already in this tree:

| Stage | Callable | File |
|-------|----------|------|
| Prompt | `QAPromptGenerator.render`, reached from `PromptBuilder.build_prompt` (or `ContextAwarePromptBuilder.build_prompt` when `context_window_chars` is set) | `langextract/prompting.py` |
| Chunk | `ChunkIterator` / `TextChunk`; batches from `make_batches_of_textchunk` | `langextract/chunking.py`, called by `langextract/annotation.py` |
| Model | `OllamaLanguageModel.infer` → `_ollama_query` | `langextract/providers/ollama.py` |
| Parse | `Resolver.resolve` → `FormatHandler.parse_output` | `langextract/resolver.py`, `langextract/core/format_handler.py` |
| Align | `Resolver.align` | `langextract/resolver.py` |
| Result | return value of `extract` | `langextract/extraction.py`; type `AnnotatedDocument` in `langextract/core/data.py` |

`debug=True` is not the printer. It calls `configure_debug_logging`, and `debug_log_calls` is applied only to tokenizer methods. Those logs truncate strings at 500 characters and sequences at 20 items (`_MAX_STR`, `_MAX_SEQ` in `langextract/core/debug_utils.py`). The script prints full stage inputs and outputs with stdlib `inspect` and `pprint` around the existing callables, in the script process, then calls `lx.extract` once.

The model request the provider already sends, which the model stage should show, matches the current Ollama generate API:

- `POST {model_url}/api/generate` (not `/api/chat`; the chat path in this provider is only for `gpt-oss`)
- `stream: false` (the API streams unless this is set)
- `format: "json"` (documented values are `"json"` or a JSON schema; `"yaml"` is not a documented format)
- `think: false` (provider default, so the answer is in `response`, not only in `thinking`)
- `options.temperature`: `0.1` (`_DEFAULT_TEMPERATURE`), not the Modelfile temperature of 1
- `options.num_ctx`: `2048` (`_DEFAULT_NUM_CTX`) unless the call passes `num_ctx`
- `timeout`: 120 seconds (`_DEFAULT_TIMEOUT`)
- Final text is `response` on the JSON body

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pip` + `python -m venv` | Install this tree | `pip install -e .` from the repo root. No lockfile. Do not add one for this script. |
| Existing `pytest` `>=7.4.0` | Only if a later task adds a test | Already the `test` extra. The milestone is a script, not a new test runner. |
| `curl` or `requests` against `GET /api/tags` | Confirm `gemma3:4b` is loaded before `extract` | Official list-local-models endpoint. Fail the script before the model call when the tag is absent. |

## Installation

```bash
# Core: this library only. Python 3.12 matches the newest CI interpreter.
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .

# The model must already be on the local server (Ollama >= 0.6).
# Do not point this milestone at examples/ollama/docker-compose.yml.
curl -s http://localhost:11434/api/tags
```

Do not run `pip install ollama`, `langsmith`, `langchain`, `dspy`, `llama-index`, `spacy`, or `opentelemetry-sdk` for this script.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `lx.extract(..., model_id="gemma3:4b")` through `OllamaLanguageModel` | PyPI package `ollama` 0.6.3 (`from ollama import chat`) | A standalone chat snippet, which is what the `gemma3:4b` model card shows. That client never enters `OllamaLanguageModel._ollama_query`, so it cannot trace this pipeline. |
| stdlib `inspect` + `pprint` around the existing callables | `debug=True` | Tokenizer debugging. It does not print prompt, chunk, parse, or alignment payloads in full. |
| Local `ollama serve` that already has `gemma3:4b` | `examples/ollama/docker-compose.yml` image `ollama/ollama:0.5.4` | The existing `gemma2:2b` demo only. 0.5.4 is older than the model card's Ollama 0.6 requirement. |
| One short `lx.extract` with `extraction_passes=1` | `examples/ollama/demo_ollama.py` | Showing extraction results and HTML. That demo defaults to `gemma2:2b` and does not print stages. |
| Provider defaults (`format: "json"`, fences off, `num_ctx` 2048, temperature 0.1) | Passing `output_schema`, `fence_output=True`, or `format: "yaml"` | Never for this call. User JSON schema is unsupported on this provider, fences fight JSON mode, and Ollama's `format` field is `"json"` or a JSON schema. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| A new extraction library (LangChain, LlamaIndex, DSPy, spaCy) | The milestone traces this pipeline. Those products have their own stage hooks (`run_type` spans, `CBEventType.CHUNKING` / `LLM`, `inspect_history`, `nlp.analyze_pipes`) that fire only inside their own pipelines. `inspect_history` prints LM messages and omits chunk, parse, and alignment. `analyze_pipes` is a static component table and does not run the pipeline. | `lx.extract` and the callables in the stage table above. |
| LangSmith, Langfuse, Arize Phoenix, Weights & Biases, OpenTelemetry GenAI | Hosted or collector-based traces. OpenTelemetry GenAI content (`gen_ai.input.messages`, `gen_ai.output.messages`) is off unless `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` is set, and nothing in this repo emits those spans. They also do not know `Resolver.align`. | A process-local print of the real arguments and return values. |
| PyPI `ollama` 0.6.3 | Second HTTP client. The model card's Python sample calls `/api/chat`. This provider calls `/api/generate` via `requests`, except for `gpt-oss`. | The built-in provider. |
| `google-genai` / `openai` for this script | Cloud providers. Both can stay installed because the library requires `google-genai` and offers `openai` as an extra. The script must not construct them. | `model_id="gemma3:4b"` and `model_url`. |
| `examples/ollama/docker-compose.yml` (`ollama/ollama:0.5.4`) | Image is below Ollama 0.6, which `gemma3:4b` requires. Compose also sets `OLLAMA_HOST`, which the factory does not read. | The local server that already has the model. |
| `output_schema=`, YAML format, `think=True` | Schema dicts are rejected by `FormatModeSchema`. YAML is not an Ollama `format` value. `think=True` can return an empty `response` with a reasoning trace, which this provider raises as `InferenceRuntimeError`. | Defaults: JSON, `think=False`, fences decided by `FormatModeSchema`. |

## Stack Patterns by Variant

**If the server is not on `http://localhost:11434`:**
- Pass `model_url=` on `lx.extract`.
- Because `OLLAMA_BASE_URL` is applied only when the model id contains `ollama`, and `gemma3:4b` does not.

**If the printed prompt is larger than the provider context pin:**
- Pass `language_model_params={"num_ctx": <tokens>}` on this call only.
- Because `_build_request_options` writes `options.num_ctx = 2048` when `num_ctx` is omitted, even though `gemma3:4b` advertises 128k. Do not change `_DEFAULT_NUM_CTX` in the library for this milestone. Keep the sample inside 2048 tokens when the goal is to show the default.

**If the first request hits the 120-second timeout while `gemma3:4b` is loading:**
- Pass `language_model_params={"timeout": 300}` (or `timeout=300` if the `extract` signature forwards it, as the Ollama example README does).
- Because the provider default is 120 seconds and a cold load of the 3.4GB model can exceed that. This is a call argument, not a new dependency. Confidence on the 300-second figure is MEDIUM: it is the example README's slower-model value, not a measurement on this machine.

**If the walkthrough must show more than one chunk:**
- Set `max_char_buffer` below the sample length and keep `extraction_passes=1`.
- Because chunking is `ChunkIterator` inside `extract`. A second pass repeats inference and merges spans. That is a different behavior from one call.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `langextract==1.7.1` | CPython `>=3.10`, CI-tested `3.10`–`3.12` | `requires-python` on PyPI and in `pyproject.toml`. Script runtime: 3.12. |
| `requests==2.34.2` (resolved; floor `>=2.25.0`) | CPython `>=3.10` | Same floor as the library. Do not pin a newer `requests` in the script. |
| `gemma3:4b` | Ollama server `>=0.6` | Model card requirement. `ollama/ollama:0.5.4` in `examples/ollama/docker-compose.yml` is too old. |
| Provider `num_ctx=2048` | Model card context 128k | The HTTP body wins. A prompt that does not fit 2048 tokens is truncated by Ollama under the provider default. |
| `format: "json"` | Current `POST /api/generate` | Documented. Do not send `format: "yaml"`. |
| `model_id="gemma3:4b"` | `OLLAMA_BASE_URL` | Not applied. Pass `model_url`. `OLLAMA_HOST` is read by `examples/ollama/demo_ollama.py` only. |
| PyPI `ollama==0.6.3` | This script | Incompatible with the tracing goal. Leave it uninstalled. |

## Sources

- PyPI JSON for `langextract` 1.7.1, `requests` 2.34.2, `ollama` 0.6.3, `absl-py` 2.5.1, `PyYAML` 6.0.3, `pydantic` 2.14.0 — fetched 2026-10-09. Confidence HIGH.
- `pyproject.toml`, `langextract/providers/ollama.py`, `langextract/factory.py`, `langextract/core/debug_utils.py`, `langextract/core/schema.py`, `examples/ollama/docker-compose.yml` — this repo. Confidence HIGH.
- https://github.com/google/langextract/blob/main/README.md — local Ollama quickstart: `model_id`, `model_url`, leave fence and schema-constraint flags unset, no `output_schema`. Confidence HIGH (cross-checked with this tree).
- https://ollama.com/library/gemma3:4b — Ollama 0.6 or later, 128k context, 3.4GB, digest `68ceab7e468a`. Confidence HIGH.
- https://github.com/ollama/ollama/blob/main/docs/api.md and https://docs.ollama.com/api/generate — `POST /api/generate`, `format` is `json` or a JSON schema, `stream: false`, `options.num_ctx`, `think`. Confidence HIGH.
- https://docs.ollama.com/capabilities/thinking — `think: false` asks for no thinking trace; generate puts the answer in `response`. Confidence HIGH.
- https://devguide.python.org/versions/ — 3.10 end of life 2026-10-01; 3.12 in security support until 2028-10. Confidence HIGH.
- https://github.com/open-telemetry/semantic-conventions/blob/v1.37.0/docs/gen-ai/gen-ai-spans.md and the Python GenAI util README — message content is opt-in. Confidence MEDIUM (verified web search; not a reason to add the SDK).
- https://dspy.ai/current/tutorials/observability/ — `inspect_history` is LM-call history only. Confidence MEDIUM.
- https://docs.langchain.com/langsmith/run-data-format — hosted run fields (`name`, `inputs`, `outputs`, `run_type`). Confidence MEDIUM.
- https://developers.llamaindex.ai/python/framework/module_guides/observability/callbacks/ — `CHUNKING` and `LLM` events exist only inside LlamaIndex. Confidence MEDIUM.
- https://spacy.io/api/language — `analyze_pipes` is static and does not run components. Confidence MEDIUM.

---
*Stack research for: one local-Ollama LangExtract call, printed by stage*
*Researched: 2026-10-09*

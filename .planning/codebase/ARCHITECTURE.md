---
last_mapped_commit: a4c0aa4c1be98f441ffc7e1d0f85b1067748e1f3
last_mapped_at: 2026-10-09
---
<!-- refreshed: 2026-10-09 -->

# Architecture

**Analysis Date:** 2026-10-09

## System Overview

LangExtract is a Python library (package `langextract`, public alias `lx`) that turns unstructured text into grounded `AnnotatedDocument` records. A few-shot prompt (or an explicit JSON output schema) drives an LLM; the library chunks long documents, calls a pluggable provider, parses the model text, and aligns each extraction back to character spans in the source.

```text
┌─────────────────────────────────────────────────────────────┐
│                    Public API (`lx.extract`)                 │
│  `langextract/__init__.py` → `langextract/extraction.py`    │
├──────────────────┬──────────────────┬───────────────────────┤
│  Prompt + schema │  Annotator       │  Resolver + aligner   │
│  `prompting.py`  │  `annotation.py` │  `resolver.py`        │
│  `factory.py`    │  `chunking.py`   │  `prompt_validation.py`│
└────────┬─────────┴────────┬─────────┴──────────┬────────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Provider router + language models               │
│  `langextract/providers/router.py`                           │
│  `gemini.py` · `openai.py` · `ollama.py` · plugins           │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Core types + optional persistence / visualization           │
│  `langextract/core/data.py`                                  │
│  `langextract/io.py` · `langextract/visualization.py`        │
└─────────────────────────────────────────────────────────────┘
```

There is no application server, database, or CLI entry point. Callers import the library. Setuptools packages are declared in `pyproject.toml`: `langextract`, `langextract._compat`, `langextract.core`, `langextract.providers`, `langextract.providers.schemas`.

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Public facade | Eager `extract` / `visualize`; PEP 562 lazy submodule access | `langextract/__init__.py` |
| Orchestrator | Validate inputs, build the model, prompt, format handler, resolver, and annotator | `langextract/extraction.py` |
| Annotator | Chunk documents, batch prompts, call `infer`, resolve, align, merge passes | `langextract/annotation.py` |
| Chunking | Sentence-aware `TextChunk` windows bounded by `max_char_buffer` | `langextract/chunking.py` |
| Prompting | Few-shot Q/A prompt text and optional previous-chunk context | `langextract/prompting.py` |
| Resolver | Parse fenced JSON/YAML into `Extraction` objects and ground them in source text | `langextract/resolver.py` |
| Format handler | Fence stripping, wrapper key `extractions`, attribute suffix, JSON/YAML parse | `langextract/core/format_handler.py` |
| Prompt validation | Pre-flight alignment of example `extraction_text` against example `text` | `langextract/prompt_validation.py` |
| Factory | `ModelConfig` → provider class, env API keys, schema application | `langextract/factory.py` |
| Provider router | Process-global regex registry mapping `model_id` to a provider class | `langextract/providers/router.py` |
| Built-in catalog | Pattern/priority table for Gemini, Ollama, OpenAI | `langextract/providers/builtin_registry.py`, `langextract/providers/patterns.py` |
| Plugin loader | Idempotent entry-point discovery for group `langextract.providers` | `langextract/providers/__init__.py` |
| Name catalog | Built-in plus third-party provider names → `module:Class` specs | `langextract/plugins.py` |
| Language model ABC | `infer`, schema hooks, fence policy | `langextract/core/base_model.py` |
| Provider schemas | Example-derived or user `output_schema` constraints | `langextract/providers/schemas/gemini.py`, `langextract/providers/schemas/openai.py`, `langextract/core/schema.py` |
| Output schema helpers | JSON Schema dicts and format checks for `output_schema=` | `langextract/core/output_schema.py`, `langextract/schema.py` |
| Domain records | `Document`, `ExampleData`, `Extraction`, `AnnotatedDocument` | `langextract/core/data.py` |
| Tokenizer | `RegexTokenizer` (default) and `UnicodeTokenizer`; sentence breaks | `langextract/core/tokenizer.py` |
| I/O | JSONL save/load, CSV `Dataset`, optional URL download | `langextract/io.py`, `langextract/data_lib.py` |
| Visualization | Self-contained animated HTML from an `AnnotatedDocument` or JSONL path | `langextract/visualization.py` |
| Progress | tqdm bars for extract, save, and load | `langextract/progress.py` |
| Batch backends | Gemini GCS batch jobs and OpenAI Batch API when a provider threshold is met | `langextract/providers/gemini_batch.py`, `langextract/providers/openai_batch.py` |
| Compat shims | Deprecated import paths scheduled for removal in v2.0.0 | `langextract/_compat/`, `langextract/data.py`, `langextract/tokenizer.py`, `langextract/inference.py`, `langextract/registry.py` |

## Pattern Overview

**Overall:** Layered pipeline with a factory-selected strategy for LLM backends.

**Key Characteristics:**

- One public orchestration function, `extract` in `langextract/extraction.py`, owns call order. Lower layers do not call back into `extract`.
- Providers implement `BaseLanguageModel.infer` in `langextract/core/base_model.py`. Selection is data-driven: regex patterns in `langextract/providers/patterns.py`, lazy registration in `langextract/providers/router.py`, entry points in `pyproject.toml` under `[project.entry-points."langextract.providers"]`.
- Import direction is enforced by import-linter contracts in `pyproject.toml`: `langextract.core` must not import `langextract.providers` or the pipeline modules `annotation`, `chunking`, `prompting`, `resolver`. `langextract.providers` must not import `langextract.inference`.
- Grounding is a separate step from parsing. `Resolver.resolve` yields unaligned `Extraction` objects; `Resolver.align` (via `WordAligner`) writes `char_interval`, `token_interval`, and `AlignmentStatus`.
- The package root stays import-light. `langextract/__init__.py` imports only `visualization` and `extraction.extract`; every other public submodule loads through `__getattr__`.

## Layers

**Public API:**

- Purpose: Stable caller surface `lx.extract` and `lx.visualize`, plus lazy attributes listed in `__all__`.
- Location: `langextract/__init__.py`
- Contains: Thin wrappers and `_LAZY_MODULES`.
- Depends on: `langextract.extraction`, `langextract.visualization`
- Used by: Application code and `skills/langextract-usage/`

**Orchestration:**

- Purpose: Argument precedence, preflight validation, model construction, wiring of prompt, format, resolver, and annotator.
- Location: `langextract/extraction.py`
- Contains: `extract`
- Depends on: `factory`, `prompting`, `prompt_validation`, `resolver`, `annotation`, `io`, `core.*`
- Used by: `langextract/__init__.py`

**Annotation pipeline:**

- Purpose: Turn documents into ordered `AnnotatedDocument` results.
- Location: `langextract/annotation.py`, `langextract/chunking.py`, `langextract/prompting.py`, `langextract/resolver.py`, `langextract/prompt_validation.py`
- Contains: `Annotator`, `TextChunk`, `ChunkIterator`, `QAPromptGenerator`, `ContextAwarePromptBuilder`, `Resolver`, `WordAligner`
- Depends on: `core` (data, tokenizer, format handler, exceptions, base model) and provider instances passed in
- Used by: `extract`; tests under `tests/annotation_test.py`, `tests/chunking_test.py`, `tests/resolver_test.py`, `tests/prompting_test.py`

**Provider layer:**

- Purpose: Resolve a `model_id` or provider name and run inference.
- Location: `langextract/factory.py`, `langextract/providers/`
- Contains: `ModelConfig`, `create_model`, `GeminiLanguageModel`, `OpenAILanguageModel`, `OllamaLanguageModel`, batch helpers
- Depends on: `core.base_model`, `core.schema`, `core.types`, `core.exceptions`; provider SDKs (`google-genai` required, `openai` optional extra)
- Used by: `extract` and callers who pass a pre-built `model=`

**Core:**

- Purpose: Types and ABCs with no dependency on the pipeline or on providers.
- Location: `langextract/core/`
- Contains: `data.py`, `types.py`, `tokenizer.py`, `base_model.py`, `schema.py`, `format_handler.py`, `output_schema.py`, `exceptions.py`, `debug_utils.py`
- Depends on: stdlib plus PyYAML / regex inside format handler and tokenizer
- Used by: every higher layer

**Persistence and presentation:**

- Purpose: Optional after the pipeline. JSONL round-trip and HTML highlighting.
- Location: `langextract/io.py`, `langextract/data_lib.py`, `langextract/visualization.py`, `langextract/progress.py`
- Contains: `save_annotated_documents`, `load_annotated_documents_jsonl`, `Dataset`, `visualize`
- Depends on: `core.data`; visualization also calls `io.load_annotated_documents_jsonl` for path inputs
- Used by: callers and `lx.visualize`

**Compatibility:**

- Purpose: Keep pre-split import paths working until v2.0.0.
- Location: `langextract/_compat/README.md` and the shim modules it lists
- Contains: Forwarders only. `langextract/data.py` re-exports `langextract.core.data`. `langextract/tokenizer.py` re-exports `langextract.core.tokenizer`. `langextract/exceptions.py` re-exports a subset of `langextract.core.exceptions`. `langextract/inference.py` forwards to `langextract/_compat/inference.py`. `langextract/registry.py` forwards to `langextract/plugins.py` and emits `FutureWarning`. `langextract/schema.py` exports current JSON-schema helpers and lazily warns on old schema class names.
- Depends on: canonical modules
- Used by: external code that has not migrated

## Data Flow

### Primary Request Path

1. Caller invokes `lx.extract(...)` (`langextract/__init__.py`). The wrapper calls `extract` in `langextract/extraction.py`.
2. `extract` requires `examples` unless `output_schema` is set or the passed `model` already carries a schema marked `from_output_schema` (`_has_preconfigured_output_schema`). `fence_output=True` together with an active schema raises `output_schema_fence_error` before any model mutation.
3. When `prompt_validation_level` is not `OFF`, `prompt_validation.validate_prompt_alignment` runs a `WordAligner` over the examples (`langextract/prompt_validation.py`). `WARNING` logs; `ERROR` raises `PromptAlignmentError`.
4. A string input is fetched with `io.download_text_from_url` only when `fetch_urls=True` and `io.is_url` matches (`langextract/io.py`). Otherwise the string is literal text.
5. Examples are stored on `prompting.PromptTemplateStructured`. Model selection precedence inside `extract` is: explicit `model`, then `config` (`factory.ModelConfig`), then `model_id` (default `"gemini-3.5-flash"`) wrapped in a new `ModelConfig`. Deprecated `language_model_type` emits `FutureWarning`.
6. `factory.create_model` (`langextract/factory.py`) calls `providers.load_builtins_once` and `providers.load_plugins_once`, then `router.resolve(model_id)` or `router.resolve_provider(name)`. With `use_schema_constraints` (default `True`) and examples, the provider's `get_schema_class().from_examples` builds a schema. An explicit `output_schema` uses `from_schema_dict` and skips example-derived constraints. API keys come from kwargs or, via `_kwargs_with_environment_defaults`, `GEMINI_API_KEY` / `OPENAI_API_KEY` then `LANGEXTRACT_API_KEY`. Ollama defaults `base_url` to `OLLAMA_BASE_URL` or `http://localhost:11434`.
7. `FormatHandler.from_resolver_params` (`langextract/core/format_handler.py`) merges resolver kwargs with the model's `requires_fence_output`. Default wrapper is `{"extractions": [...]}` (`data.EXTRACTIONS_KEY`) and attribute fields use `data.ATTRIBUTE_SUFFIX` (`"_attributes"`). `extract` forces `suppress_parse_errors=True` unless the caller overrides it.
8. `annotation.Annotator` builds a `QAPromptGenerator`. `annotate_text` wraps a string in one `data.Document`; `annotate_documents` streams an iterable.
9. `_document_chunk_iterator` tokenizes with the supplied tokenizer or `tokenizer.tokenize` (regex tokenizer) and yields `chunking.TextChunk` windows. `chunking.make_batches_of_textchunk` groups them with `more_itertools.batched` into batches of `batch_length` (default 10).
10. `ContextAwarePromptBuilder.build_prompt` renders description, optional `additional_context`, few-shot Q/A pairs, and the chunk. When `context_window_chars` is set, it prefixes a suffix of the previous chunk for the same `document_id`.
11. `language_model.infer(batch_prompts)` returns an iterator of `Sequence[ScoredOutput]` (`langextract/core/types.py`). Gemini and OpenAI fan out with `ThreadPoolExecutor` when `len(batch_prompts) > 1` and `max_workers > 1` (`langextract/providers/gemini.py`, `langextract/providers/openai.py`). The annotator consumes the highest-scored output (`scored_outputs[0]`).
12. `Resolver.resolve` calls `FormatHandler.parse_output`. Parse or schema failures return `[]` when `suppress_parse_errors` is true, otherwise `ResolverParsingError`. `Resolver.align` maps `extraction_text` onto the chunk, then shifts token and char offsets back to document coordinates. Status values live on `data.AlignmentStatus`: `MATCH_EXACT`, `MATCH_GREATER`, `MATCH_LESSER`, `MATCH_FUZZY`.
13. Single-pass mode emits each `AnnotatedDocument` as soon as later chunks cannot belong to it (`_emit_docs_iter`). Duplicate `document_id` values raise `InvalidDocumentError`.
14. Return type: one `AnnotatedDocument` for a string input; `list[AnnotatedDocument]` for an iterable of documents.

### Multi-pass recall

1. When `extraction_passes > 1`, `Annotator._annotate_documents_sequential_passes` materializes `list(documents)` and repeats the single-pass pipeline.
2. `_merge_non_overlapping_extractions` keeps the earlier pass when character spans overlap (first-pass wins). Extractions with `char_interval is None` are always appended.
3. Only pass 0 shows the progress bar and records debug alignment. Later passes rerun the same prompts and therefore repeat provider token use.

### Provider batch APIs

1. `GeminiLanguageModel.infer` delegates to `gemini_batch.infer_batch` when the provider's batch config threshold is met (`langextract/providers/gemini_batch.py`). Below the threshold it logs and uses the real-time client. Batch mode uploads prompts to GCS (`google-cloud-storage`) and polls a Gemini batch job.
2. `OpenAILanguageModel` follows the same shape via `openai_batch.infer_batch` (`langextract/providers/openai_batch.py`).
3. Both paths still yield `[ScoredOutput(score=1.0, output=text)]`, so the annotator and resolver stay unchanged.

### Visualization

1. `lx.visualize` calls `visualization.visualize` (`langextract/visualization.py`).
2. A path argument loads the first document via `io.load_annotated_documents_jsonl`. An `AnnotatedDocument` is used directly.
3. `_filter_valid_extractions` keeps spans that can be highlighted. `_assign_colors` maps `extraction_class` to colors. The function returns `IPython.display.HTML` inside Jupyter and an HTML string otherwise.

### JSONL persistence

1. `io.save_annotated_documents` serializes each document with `data_lib.annotated_document_to_dict` and writes JSON Lines. Default directory is `test_output/` when `output_dir` is omitted.
2. `io.load_annotated_documents_jsonl` reverses that with `data_lib.dict_to_annotated_document`.
3. `io.Dataset.load` reads a CSV (`text_key`, `id_key`) into `Document` objects. Non-CSV paths raise `NotImplementedError`.

**State Management:**

- Pipeline state is per call: prompt template, model instance, resolver, and the annotator's per-document extraction lists. Single-pass annotation streams and drops document text after emit.
- `Document.tokenized_text` and `AnnotatedDocument.tokenized_text` cache tokenization on the instance (`langextract/core/data.py`).
- Provider registration is process-global: `_entries` and `_entry_keys` in `langextract/providers/router.py`, plus `_plugins_loaded` / `_builtins_loaded` in `langextract/providers/__init__.py`. `resolve` and `resolve_provider` are `functools.lru_cache`d (maxsize 128). `router.clear()` drops entries and clears those caches; tests call it, production code does not.
- `plugins._discovered` and `plugins.get_provider_class` are also `lru_cache`d (`langextract/plugins.py`).
- `debug=True` calls `debug_utils.configure_debug_logging()`, which attaches a handler to the `langextract` logger for the rest of the process (`langextract/core/debug_utils.py`).

## Key Abstractions

**`BaseLanguageModel`:**

- Purpose: Inference contract. `infer(batch_prompts) -> Iterator[Sequence[ScoredOutput]]`. `infer_batch` collects that iterator. `parse_output` is a raw JSON/YAML helper; fence stripping belongs to the resolver.
- Examples: `langextract/providers/gemini.py` (`GeminiLanguageModel`), `langextract/providers/openai.py` (`OpenAILanguageModel`), `langextract/providers/ollama.py` (`OllamaLanguageModel`), `examples/custom_provider_plugin/langextract_provider_example/provider.py` (`CustomGeminiProvider`)
- Pattern: Subclass the ABC, implement `infer`, optionally override `get_schema_class`. Register with `router.register` / `register_lazy` or the entry-point group `langextract.providers`.

**`BaseSchema`:**

- Purpose: Provider-native structured-output config derived from examples or from a user JSON schema.
- Examples: `langextract/core/schema.py` (`BaseSchema`, `FormatModeSchema`), `langextract/providers/schemas/gemini.py` (`GeminiSchema`), `langextract/providers/schemas/openai.py` (`OpenAISchema`)
- Pattern: `from_examples` or `from_schema_dict`, then `to_provider_config()` returns kwargs merged into the provider constructor. `requires_raw_output` drives the default fence setting on `BaseLanguageModel.requires_fence_output`. `mark_from_output_schema` sets `from_output_schema=True` so later `extract` calls can skip examples.

**`FormatHandler`:**

- Purpose: Single place for prompt serialization and model-output parsing (JSON or YAML, fences, wrapper key, attribute suffix).
- Examples: `langextract/core/format_handler.py`
- Pattern: Build one handler in `extract` via `from_resolver_params` and pass that same instance to both `Resolver` and `Annotator`. Do not let the prompt formatter and the parser drift.

**`Extraction` / `Document` / `AnnotatedDocument` / `ExampleData`:**

- Purpose: Domain records. `ExampleData` is the few-shot pair (`text` + `extractions`). `Document` is an input. `AnnotatedDocument` is the result. `Extraction` holds `extraction_class`, verbatim `extraction_text`, optional `attributes`, and grounding fields.
- Examples: `langextract/core/data.py`. Public import `langextract.data` is a re-export shim (`langextract/data.py`).
- Pattern: Construct with keyword-only grounding fields. `document_id` is generated as `doc_` plus eight hex chars when unset. Character spans on extractions use `data.CharInterval` (`start_pos` / `end_pos` may be `None`). Token spans use `tokenizer.TokenInterval`.

**`Tokenizer`:**

- Purpose: Token stream shared by chunking and alignment.
- Examples: `langextract/core/tokenizer.py` — `RegexTokenizer` (default via `tokenize()`), `UnicodeTokenizer`
- Pattern: Pass one instance through `extract(..., tokenizer=...)` so chunk offsets and alignment offsets use the same token boundaries. `tokenizer.CharInterval` is a separate dataclass from `data.CharInterval`; pipeline code that stores spans on `Extraction` uses `data.CharInterval`.

**Provider router entry:**

- Purpose: Lazy class loading so optional SDKs import only after a pattern matches.
- Examples: `register_lazy(*patterns, target="langextract.providers.gemini:GeminiLanguageModel", priority=10)` from `BUILTIN_PROVIDERS` in `langextract/providers/builtin_registry.py`
- Pattern: Higher `priority` wins. `resolve` walks entries sorted by priority and returns the first `pattern.search(model_id)` hit. On a miss it raises `InferenceConfigError` listing registered patterns.

## Entry Points

**`lx.extract` / `extract`:**

- Location: `langextract/__init__.py`, `langextract/extraction.py`
- Triggers: Application code
- Responsibilities: Full pipeline from text or documents to annotated results

**`lx.visualize` / `visualize`:**

- Location: `langextract/__init__.py`, `langextract/visualization.py`
- Triggers: Notebooks and review scripts, including `examples/notebooks/romeo_juliet_extraction.ipynb`
- Responsibilities: HTML highlighting; does not call a model

**`factory.create_model` / `create_model_from_id`:**

- Location: `langextract/factory.py`
- Triggers: `extract`, or callers who want a reusable model instance to pass as `model=`
- Responsibilities: Provider resolution, environment defaults, schema constraints

**`io.save_annotated_documents` / `load_annotated_documents_jsonl` / `Dataset.load`:**

- Location: `langextract/io.py`
- Triggers: Callers persisting results or loading CSV inputs
- Responsibilities: JSONL and CSV only

**`plugins.available_providers` / `get_provider_class`:**

- Location: `langextract/plugins.py`
- Triggers: Tooling that lists providers by short name (`gemini`, `ollama`, `openai`, plus entry-point names)
- Responsibilities: Name → class catalog. `extract` itself resolves through `router.resolve`, not through `get_provider_class`.

**Provider plugin entry points:**

- Location: `pyproject.toml` `[project.entry-points."langextract.providers"]` and the same group on third-party packages
- Triggers: `providers.load_plugins_once` during `create_model`
- Responsibilities: Import the class and, when `get_model_patterns()` exists, `router.register` each pattern at the class's `pattern_priority` (default 20)

**Batch helpers (not public top-level APIs):**

- Location: `langextract/providers/gemini_batch.py` (`infer_batch`), `langextract/providers/openai_batch.py` (`infer_batch`)
- Triggers: The matching provider's `infer` when batch mode is enabled and the prompt count reaches the threshold
- Responsibilities: File upload, job poll, text extraction back into `ScoredOutput`

**Scripts (developer tooling, not installed console scripts):**

- Location: `scripts/create_provider_plugin.py`, `scripts/validate_community_providers.py`
- Triggers: Manual runs and `.github/workflows/validate-community-providers.yaml`
- Responsibilities: Scaffold a plugin package; check `COMMUNITY_PROVIDERS.md`

## Architectural Constraints

- **Threading:** The annotator loop is synchronous and single-threaded. Parallelism lives inside provider `infer`. Gemini and OpenAI submit one prompt per worker via `concurrent.futures.ThreadPoolExecutor`, then yield results in input order. `max_workers` (default 10) caps the pool; effective parallelism is `min(batch_length, max_workers)`. `extract` warns when `batch_length < max_workers`. Gemini batch GCS uploads use a separate pool of 10 workers in `langextract/providers/gemini_batch.py`. Ollama's `infer` does not use a thread pool (`langextract/providers/ollama.py`).
- **Global state:** `langextract/providers/router.py` module lists `_entries` and `_entry_keys`; `langextract/providers/__init__.py` flags `_plugins_loaded` and `_builtins_loaded`; `lru_cache` on `router.resolve`, `router.resolve_provider`, `plugins._discovered`, `plugins.get_provider_class`, `tokenizer._get_common_script_cached`, and `resolver._normalize_token`. `LANGEXTRACT_DISABLE_PLUGINS` set to `1`, `true`, or `yes` skips third-party entry points inside `load_plugins_once`. Debug logging, once enabled, stays enabled for the process.
- **Circular imports:** Avoided by lazy submodule loading in `langextract/__init__.py` and `langextract/providers/__init__.py`, and by keeping `router.py` free of provider imports (loaders are string targets such as `langextract.providers.gemini:GeminiLanguageModel`). `core` never imports `providers`. The compat package exists so old `inference` imports do not pull provider modules at package import time.
- **Layering:** New pipeline code may import `langextract.core`. `langextract.core` must not import `langextract.providers`, `langextract.annotation`, `langextract.chunking`, `langextract.prompting`, or `langextract.resolver`. Providers must not import `langextract.inference`. These three contracts are in `[tool.importlinter]` in `pyproject.toml`.
- **Schema vs fences:** `output_schema` requires JSON and forbids `fence_output=True` (`langextract/core/exceptions.py` helpers `output_schema_fence_error` and `output_schema_format_error`). Providers without `get_schema_class()` cannot accept `output_schema` (built-in support is Gemini and OpenAI).
- **Ordering:** Single-pass emission preserves input document order. Multi-pass also emits in original input order after the merge. Within a chunk, extractions stay in model order unless `extraction_index_suffix` is set (`Resolver`, default `None`; the constant `DEFAULT_INDEX_SUFFIX` is `"_index"`).
- **URL fetch:** Disabled by default. `fetch_urls=True` performs `requests.get` with no host allow-list (`langextract/io.py`).

## Anti-Patterns

### Importing providers or the pipeline from `langextract.core`

**What happens:** A module under `langextract/core/` imports `langextract.providers` or `annotation` / `chunking` / `prompting` / `resolver`.
**Why it's wrong:** Import-linter forbids it (`pyproject.toml`). Core is the shared base so provider plugins and the pipeline can both depend on it without a cycle.
**Do this instead:** Put the new type or helper in `langextract/core/` only if it has no provider or pipeline dependency. Otherwise add it beside `extraction.py` or under `langextract/providers/`.

### Providers importing `langextract.inference`

**What happens:** Provider modules import the legacy inference facade.
**Why it's wrong:** Forbidden by the import-linter contract "Providers must not import inference". `langextract/inference.py` is a deprecated shim over `langextract/_compat/inference.py`.
**Do this instead:** Import `BaseLanguageModel` from `langextract.core.base_model`, `ScoredOutput` from `langextract.core.types`, and errors from `langextract.core.exceptions`.

### Adding features under `langextract/_compat/`

**What happens:** New symbols land in `langextract/_compat/` or in the top-level shims `inference.py`, `registry.py`, `tokenizer.py`.
**Why it's wrong:** `langextract/_compat/README.md` states that directory is a removal target for v2.0.0 and that contributors must not add code there.
**Do this instead:** Add the symbol on the canonical module (`core/`, `providers/`) and, only if an old public path must keep working, re-export it from the existing shim.

### Building an `Annotator` with its constructor defaults

**What happens:** `Annotator.__init__` defaults `format_type` to `data.FormatType.YAML` and `fence_output` to `False` when no `format_handler` is passed (`langextract/annotation.py`). `extract` defaults `format_type` to JSON and derives fences from the schema.
**Why it's wrong:** Prompt formatting and `Resolver` parsing diverge, so chunks fail to parse or silently drop when `suppress_parse_errors` is true.
**Do this instead:** Go through `extract`, or construct one `FormatHandler` and pass it to both `Annotator` and `Resolver`, matching `extraction.py`.

### Assuming `annotate_documents` streams when `extraction_passes > 1`

**What happens:** `_annotate_documents_sequential_passes` calls `list(documents)` before the first pass.
**Why it's wrong:** A generator input is fully buffered, and every pass re-infers every chunk.
**Do this instead:** Use `extraction_passes=1` (the default) when the caller needs streaming emission. Use extra passes only for recall, with the cost called out in the `extract` docstring.

### Treating `plugins.get_provider_class` as the `model_id` router

**What happens:** Code registers a provider only in the name map (`plugins._BUILTINS`) or only on the router.
**Why it's wrong:** `extract` resolves with `router.resolve` / `router.resolve_provider` after `load_plugins_once`. `plugins.available_providers` is a separate name catalog and does not by itself make `model_id="my-model"` work.
**Do this instead:** For a built-in, add patterns to `langextract/providers/patterns.py` and a row in `BUILTIN_PROVIDERS` (`langextract/providers/builtin_registry.py`). For a third-party package, expose an entry point in group `langextract.providers` whose class implements `get_model_patterns()`, and follow `langextract/providers/README.md` or `scripts/create_provider_plugin.py`.

## Error Handling

**Strategy:** Typed exceptions rooted at `LangExtractError` (`langextract/core/exceptions.py`). Configuration failures abort before inference. Chunk-level parse failures are omitted by default inside `extract` so one bad chunk does not fail the document. Provider SDK exceptions are wrapped in `InferenceRuntimeError` with `original` and optional `provider`.

**Patterns:**

- `InferenceConfigError` — unknown `model_id`, provider constructor `TypeError`/`ValueError`, unsupported `output_schema`, fence/format conflicts, missing schema support. Helpers: `unsupported_output_schema_error`, `output_schema_fence_error`, `output_schema_format_error`, `output_schema_provider_kwargs_error`.
- `InferenceRuntimeError` — API, network, and parallel-worker failures in `gemini.py`, `openai.py`, and the batch modules. `original` holds the SDK exception.
- `InferenceOutputError` — `infer` returned an empty scored-output sequence (`annotation.py`).
- `InvalidDocumentError` — duplicate `document_id` while streaming.
- `FormatError` / `FormatParseError` — format handler cannot parse. `Resolver.resolve` turns `FormatError` and extraction `ValueError` into `ResolverParsingError` (`langextract/resolver.py`), unless `suppress_parse_errors=True`, which logs via `absl.logging` and returns `[]`. `extract` sets that flag by default.
- `PromptAlignmentError` — example text does not align when `prompt_validation_level` is `ERROR` (`langextract/prompt_validation.py`).
- `InvalidDatasetError` — empty JSONL save or empty CSV (`langextract/io.py`).
- Legacy resolver kwargs that are not real parameters raise `TypeError` from `extract` with the prefix `Unknown key in resolver_params`.

## Cross-Cutting Concerns

**Logging:** Pipeline modules use `absl.logging` (`annotation.py`, `resolver.py`, `providers/__init__.py`, `chunking.py`). `debug=True` additionally configures the stdlib logger named `langextract` in `langextract/core/debug_utils.py`. `debug_log_calls` redacts mapping values whose names look like secrets before logging. Do not enable debug logging in library import paths; it is process-wide once configured.

**Validation:** Three layers, in order: (1) prompt alignment of examples (`prompt_validation.py`) before the model is created; (2) `output_schema_lib.validate_output_schema` / `validate_output_schema_format_handler` and `schema.validate_format` against the `FormatHandler`; (3) `FormatHandler.parse_output` plus `Resolver.extract_ordered_extractions` on each model response. Alignment thresholds and algorithms are the keys in `resolver.ALIGNMENT_PARAM_KEYS` and may be passed through `resolver_params`.

**Authentication:** No user-account system. Cloud providers read an explicit `api_key` or the environment variables resolved in `factory._kwargs_with_environment_defaults`. Gemini skips that lookup when `vertexai=True`. Plugin loading can be disabled with `LANGEXTRACT_DISABLE_PLUGINS`. Secrets must stay in the environment or caller kwargs, not in `provider` pattern tables or example documents.

---

*Architecture analysis: 2026-10-09*

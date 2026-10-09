---
last_mapped_commit: a4c0aa4c1be98f441ffc7e1d0f85b1067748e1f3
last_mapped_at: 2026-10-09
---
# Codebase Structure

**Analysis Date:** 2026-10-09

## Directory Layout

```
langextract/
├── langextract/                 # Installable library package
│   ├── __init__.py              # Public facade: extract, visualize, lazy submodules
│   ├── extraction.py            # lx.extract orchestration
│   ├── annotation.py            # Annotator pipeline
│   ├── chunking.py              # Sentence-aware TextChunk windows
│   ├── prompting.py             # Few-shot prompt rendering
│   ├── resolver.py              # Parse model output and align to source
│   ├── prompt_validation.py     # Example alignment preflight
│   ├── factory.py               # ModelConfig and create_model
│   ├── plugins.py               # Provider name catalog
│   ├── io.py                    # JSONL, CSV Dataset, URL download
│   ├── data_lib.py              # AnnotatedDocument ↔ dict
│   ├── visualization.py         # HTML highlighting
│   ├── progress.py              # tqdm helpers
│   ├── schema.py                # Public JSON-schema helpers + legacy names
│   ├── data.py                  # Shim → core.data
│   ├── tokenizer.py             # Shim → core.tokenizer
│   ├── exceptions.py            # Shim → core.exceptions (subset)
│   ├── inference.py             # Shim → _compat.inference
│   ├── registry.py              # Shim → plugins (FutureWarning)
│   ├── core/                    # Types and ABCs; no provider or pipeline imports
│   ├── providers/               # Built-in LLM backends and router
│   └── _compat/                 # Deprecated forwarders; do not add features
├── tests/                       # pytest suite (not shipped in the wheel)
├── examples/                    # Runnable samples and a plugin skeleton
├── docs/                        # Example write-ups and static assets
├── scripts/                     # Maintainer CLIs (not setuptools entry points)
├── benchmarks/                  # Local benchmark scripts
├── skills/langextract-usage/    # Agent skill: how to call the library
├── .github/                     # CI workflows, PR templates, helper scripts
├── pyproject.toml               # Package metadata, extras, pytest, import-linter
├── tox.ini                      # Multi-env test runner
├── Dockerfile                   # Container build for the library
├── autoformat.sh                # pyink + isort helper
├── README.md                    # User-facing introduction and quick start
├── CONTRIBUTING.md              # Contributor workflow
└── COMMUNITY_PROVIDERS.md       # Third-party provider index
```

Setuptools `packages` in `pyproject.toml` are only `langextract`, `langextract._compat`, `langextract.core`, `langextract.providers`, and `langextract.providers.schemas`. `tests/`, `docs/`, `examples/`, `scripts/`, `benchmarks/`, and `skills/` stay in the repo and are excluded from package data.

## Directory Purposes

**`langextract/`:**

- Purpose: Runtime library. Every supported caller path starts here.
- Contains: Top-level pipeline modules plus `core/`, `providers/`, and `_compat/`.
- Key files: `langextract/__init__.py`, `langextract/extraction.py`, `langextract/annotation.py`, `langextract/factory.py`

**`langextract/core/`:**

- Purpose: Dependency-free foundation (relative to the rest of the package). Import-linter blocks imports of `providers` and of `annotation`, `chunking`, `prompting`, `resolver`.
- Contains: Dataclasses, tokenizer, format handler, schema ABC, exception hierarchy, debug logging.
- Key files: `langextract/core/data.py`, `langextract/core/base_model.py`, `langextract/core/tokenizer.py`, `langextract/core/format_handler.py`, `langextract/core/schema.py`, `langextract/core/output_schema.py`, `langextract/core/types.py`, `langextract/core/exceptions.py`, `langextract/core/debug_utils.py`, `langextract/core/__init__.py`

**`langextract/providers/`:**

- Purpose: LLM backends and the pattern router. Each provider module imports only when its pattern matches.
- Contains: Provider classes, batch helpers, schema implementations, registration tables.
- Key files: `langextract/providers/__init__.py`, `langextract/providers/router.py`, `langextract/providers/builtin_registry.py`, `langextract/providers/patterns.py`, `langextract/providers/gemini.py`, `langextract/providers/openai.py`, `langextract/providers/ollama.py`, `langextract/providers/gemini_batch.py`, `langextract/providers/openai_batch.py`, `langextract/providers/schemas/gemini.py`, `langextract/providers/schemas/openai.py`, `langextract/providers/README.md`

**`langextract/_compat/`:**

- Purpose: Backward-compatible re-exports. Removal target is v2.0.0 (`langextract/_compat/README.md`).
- Contains: `inference.py`, `schema.py`, `exceptions.py`, `registry.py`, `__init__.py`.
- Key files: `langextract/_compat/README.md` (migration map). Do not add new modules here.

**`tests/`:**

- Purpose: Pytest modules. `testpaths = ["tests"]` in `pyproject.toml`. File names match `test_*.py` or `*_test.py`.
- Contains: Unit tests per pipeline module, provider factory tests, live-API tests marked `live_api` / `vertex_ai`.
- Key files: `tests/annotation_test.py`, `tests/resolver_test.py`, `tests/factory_test.py`, `tests/init_test.py`, `tests/test_live_api.py`, `tests/.pylintrc`

**`examples/`:**

- Purpose: Samples that are not imported by the library.
- Contains: Ollama docker demo, a custom provider plugin package, a notebook.
- Key files: `examples/ollama/demo_ollama.py`, `examples/ollama/docker-compose.yml`, `examples/custom_provider_plugin/`, `examples/notebooks/romeo_juliet_extraction.ipynb`

**`docs/`:**

- Purpose: Long-form examples and static site assets referenced by `README.md`.
- Contains: Markdown walkthroughs and SVG/HTML concept art.
- Key files: `docs/examples/medication_examples.md`, `docs/examples/longer_text_example.md`, `docs/examples/output_schema.md`, `docs/examples/batch_api_example.md`, `docs/examples/japanese_extraction.md`, `docs/_static/logo.svg`

**`scripts/`:**

- Purpose: Maintainer tools run as `python scripts/...`, not as installed console scripts (`pyproject.toml` defines no `[project.scripts]`).
- Contains: Plugin scaffolder and community-provider validator.
- Key files: `scripts/create_provider_plugin.py`, `scripts/validate_community_providers.py`

**`benchmarks/`:**

- Purpose: Local performance and fuzzy-alignment measurements. Not part of pytest `testpaths`.
- Contains: Benchmark drivers and plotting helpers.
- Key files: `benchmarks/benchmark.py`, `benchmarks/fuzzy_benchmark.py`, `benchmarks/config.py`, `benchmarks/utils.py`, `benchmarks/plotting.py`

**`skills/langextract-usage/`:**

- Purpose: Agent-facing usage guide for calling `lx.extract`. Not imported by the package.
- Contains: `SKILL.md`, short examples, reference notes.
- Key files: `skills/langextract-usage/SKILL.md`, `skills/langextract-usage/examples/basic_extraction.py`, `skills/langextract-usage/references/providers.md`, `skills/langextract-usage/references/resolver-params.md`

**`.github/`:**

- Purpose: GitHub automation.
- Contains: Workflows, issue/PR templates, shell helpers.
- Key files: `.github/workflows/ci.yaml`, `.github/workflows/publish.yml`, `.github/workflows/validate-community-providers.yaml`, `.github/workflows/zenodo-publish.yml`

## Key File Locations

**Entry Points:**

- `langextract/__init__.py`: Public `extract` and `visualize`; lazy map for `annotation`, `data`, `providers`, `schema`, `inference`, `factory`, `resolver`, `prompting`, `io`, `core`, `plugins`, and others listed in `_LAZY_MODULES`.
- `langextract/extraction.py`: Implementation of `extract`. Change call order and parameter defaults here.
- `langextract/visualization.py`: Implementation of `visualize`.
- `pyproject.toml`: Entry-point group `langextract.providers` with keys `gemini`, `ollama`, `openai`. This is provider discovery, not a CLI.

**Configuration:**

- `pyproject.toml`: Package version, dependencies, optional extras `openai`, `all`, `dev`, `test`, `notebook`; pytest markers; pyink/isort; import-linter contracts.
- `tox.ini`: Test environments.
- `.pylintrc` and `tests/.pylintrc`: Pylint.
- `.pre-commit-config.yaml`: Pre-commit hooks.
- `autoformat.sh`: Format helper (pyink, 2-space indent, line length 80, matching `[tool.pyink]`).
- `Dockerfile`: Image build. `examples/ollama/Dockerfile` and `examples/ollama/docker-compose.yml` are the local-model demo, separate from the library image.

**Core Logic:**

- `langextract/core/data.py`: `AlignmentStatus`, `CharInterval`, `Extraction`, `Document`, `AnnotatedDocument`, `ExampleData`, `EXTRACTIONS_KEY`, `ATTRIBUTE_SUFFIX`.
- `langextract/core/types.py`: `FormatType` (`JSON`, `YAML`), `Constraint`, `ScoredOutput`, `JsonSchema`.
- `langextract/core/base_model.py`: `BaseLanguageModel` (`infer`, `apply_schema`, `apply_output_schema`, `requires_fence_output`).
- `langextract/core/tokenizer.py`: `RegexTokenizer`, `UnicodeTokenizer`, `tokenize`, `find_sentence_range`.
- `langextract/annotation.py`: `Annotator.annotate_text`, `annotate_documents`, single-pass streaming, multi-pass merge.
- `langextract/chunking.py`: `TextChunk`, `SentenceIterator`, `ChunkIterator`, `make_batches_of_textchunk`.
- `langextract/prompting.py`: `PromptTemplateStructured`, `QAPromptGenerator`, `ContextAwarePromptBuilder`, `read_prompt_template_structured_from_file`.
- `langextract/resolver.py`: `Resolver`, `WordAligner`, `ALIGNMENT_PARAM_KEYS`.
- `langextract/factory.py`: `ModelConfig`, `create_model`, `create_model_from_id`.
- `langextract/providers/router.py`: `register`, `register_lazy`, `resolve`, `resolve_provider`, `clear`.
- `langextract/io.py`: `save_annotated_documents`, `load_annotated_documents_jsonl`, `Dataset`, `is_url`, `download_text_from_url`.

**Testing:**

- `tests/`: One module per concern. Prefer `tests/<module>_test.py` (for example `tests/chunking_test.py`, `tests/resolver_test.py`) or `tests/test_<feature>.py` (for example `tests/test_gemini_batch_api.py`, `tests/test_live_api.py`).
- Live tests use pytest markers declared in `pyproject.toml`: `live_api`, `vertex_ai`, `requires_pip`, `integration`.

## Naming Conventions

**Files:**

- Package modules: `snake_case.py` (`prompt_validation.py`, `format_handler.py`, `gemini_batch.py`).
- Tests: `test_*.py` or `*_test.py`. Either form is collected (`python_files` in `pyproject.toml`).
- Provider class modules match the backend: `gemini.py`, `openai.py`, `ollama.py`.
- Shims keep the historical public module name (`data.py`, `tokenizer.py`, `inference.py`, `registry.py`, `schema.py`, `exceptions.py`) even when the implementation lives under `core/`.

**Directories:**

- Package subpackages: short lowercase names (`core`, `providers`, `providers/schemas`, `_compat`).
- `_compat` leading underscore marks non-public, deprecated support code.
- Repo-level folders are plural where they hold many artifacts (`tests`, `examples`, `docs`, `benchmarks`, `scripts`, `skills`).

**Python names:**

- Classes: `PascalCase` (`Annotator`, `GeminiLanguageModel`, `FormatHandler`, `AnnotatedDocument`).
- Functions and methods: `snake_case` (`create_model`, `annotate_text`, `load_plugins_once`).
- Module constants: `UPPER_SNAKE` (`EXTRACTIONS_KEY`, `ALIGNMENT_PARAM_KEYS`, `GEMINI_PATTERNS`, `BUILTIN_PROVIDERS`).
- Private helpers: leading underscore (`_annotate_documents_single_pass`, `_kwargs_with_environment_defaults`, `_entries`).
- Provider classes end with `LanguageModel` for built-ins (`GeminiLanguageModel`). Plugin examples may use a `Provider` suffix (`CustomGeminiProvider` in `examples/custom_provider_plugin/langextract_provider_example/provider.py`).
- Tests: classes `Test*`, functions `test_*`.

## Where to Add New Code

**New extraction behavior (chunking, prompting, parsing, alignment):**

- Primary code: the matching top-level module — `langextract/chunking.py`, `langextract/prompting.py`, `langextract/resolver.py`, or `langextract/annotation.py`. If the behavior is a new user-facing parameter, thread it through `extract` in `langextract/extraction.py` and document it on that function.
- Shared types that providers must not depend upward for: `langextract/core/data.py` or `langextract/core/types.py`.
- Tests: `tests/<module>_test.py` next to the existing file for that module.

**New built-in provider:**

- Implementation: `langextract/providers/<name>.py` subclassing `BaseLanguageModel`.
- Patterns and priority: `langextract/providers/patterns.py`, then a `ProviderConfig` row in `langextract/providers/builtin_registry.py`.
- Structured output: `langextract/providers/schemas/<name>.py` subclassing `BaseSchema`, and export it from `langextract/providers/schemas/__init__.py` when it should be public.
- Discovery: add an entry under `[project.entry-points."langextract.providers"]` in `pyproject.toml`.
- Tests: `tests/factory_test.py` / `tests/provider_schema_test.py` style, plus a focused `tests/test_<name>_*.py` if the backend has its own protocol.
- Keep the module free of imports from `langextract.inference`.

**New third-party provider (separate installable package):**

- Generate the skeleton with `python scripts/create_provider_plugin.py MyProvider` (optional `--with-schema`, `--patterns`).
- Follow the layout in `examples/custom_provider_plugin/`: package directory, `provider.py`, optional `schema.py`, `pyproject.toml` entry point group `langextract.providers`, and `test_example_provider.py`.
- Document the provider in `COMMUNITY_PROVIDERS.md`. The checker is `scripts/validate_community_providers.py`, run from `.github/workflows/validate-community-providers.yaml`.
- In-tree guide: `langextract/providers/README.md`.

**New public function on the package root:**

- Implementation: a top-level module under `langextract/`.
- Export: wrapper in `langextract/__init__.py` if it should be eager like `extract` and `visualize`; otherwise add the module name to `_LAZY_MODULES` and `__all__`.
- Tests: `tests/init_test.py` for the lazy attribute, plus a behavior test module.

**New JSON schema helper for callers:**

- Implementation: `langextract/core/output_schema.py`.
- Re-export: `langextract/schema.py` (this module is the public `lx.schema` surface). Do not put new helpers only on the `_compat` path.

**Persistence or visualization:**

- Serialization: `langextract/data_lib.py` for dict shape, `langextract/io.py` for files.
- HTML: `langextract/visualization.py`.
- Progress bars: `langextract/progress.py`.

**Utilities:**

- Pipeline-specific helpers stay in the module that uses them (private `_` functions).
- Cross-cutting debug redaction: `langextract/core/debug_utils.py`.
- Do not create a new `utils.py` grab bag.

**Tests for a completed behavior change:**

- Place them in `tests/` using the existing naming split (`*_test.py` or `test_*.py`).
- Mark network tests with `@pytest.mark.live_api` or `@pytest.mark.vertex_ai`.
- Mark tests that pip-install plugins with `@pytest.mark.requires_pip`.

**Docs and samples:**

- Short runnable snippets: `skills/langextract-usage/examples/` or `examples/`.
- Narrative walkthroughs: `docs/examples/*.md`.
- User-facing overview: `README.md`.

## Special Directories

**`langextract/_compat/`:**

- Purpose: Deprecated import forwarders listed in `langextract/_compat/README.md`.
- Generated: No
- Committed: Yes

**`langextract/core/`:**

- Purpose: Lowest layer. Safe to import from providers, plugins, and the pipeline.
- Generated: No
- Committed: Yes

**`langextract/providers/schemas/`:**

- Purpose: Provider-specific `BaseSchema` subclasses. Separate from `langextract/core/schema.py` so core stays provider-agnostic.
- Generated: No
- Committed: Yes

**`examples/custom_provider_plugin/`:**

- Purpose: Worked example of an out-of-tree plugin (`langextract_provider_example`). Its own `pyproject.toml` is not the library's `pyproject.toml`.
- Generated: No
- Committed: Yes

**`examples/ollama/`:**

- Purpose: Local Ollama demo (`demo_ollama.py`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`).
- Generated: No
- Committed: Yes

**`docs/_static/`:**

- Purpose: Logo and concept HTML/GIF assets linked from `README.md`.
- Generated: No
- Committed: Yes

**`.github/`:**

- Purpose: CI and repository automation. Workflow files live in `.github/workflows/`; PR helper shell/Python lives in `.github/scripts/`.
- Generated: No
- Committed: Yes

**`benchmarks/`:**

- Purpose: Manual performance scripts. They are not collected by pytest.
- Generated: No
- Committed: Yes

**`skills/`:**

- Purpose: Cursor/agent skill describing library usage. Runtime code must not import it.
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-10-09*

---
last_mapped_commit: a4c0aa4c1be98f441ffc7e1d0f85b1067748e1f3
last_mapped_at: 2026-10-09
---
# Coding Conventions

**Analysis Date:** 2026-10-09

## Naming Patterns

**Files:**

- Library modules are `snake_case.py` under `langextract/`. One module, one concern: `langextract/factory.py`, `langextract/resolver.py`, `langextract/providers/gemini.py`.
- Packages that are imported as APIs get an `__init__.py` with an explicit `__all__` (`langextract/__init__.py`, `langextract/core/__init__.py`, `langextract/providers/__init__.py`).
- Test modules live in `tests/` and are named after the module they cover. Prefer the Google suffix `*_test.py` (`tests/factory_test.py` for `langextract/factory.py`). `test_*.py` is also collected (`tests/test_live_api.py`) — use that prefix only for live or integration suites that are already named that way.
- Compatibility shims keep the old public path and delegate: `langextract/data.py`, `langextract/tokenizer.py`, `langextract/schema.py`, `langextract/exceptions.py`, `langextract/registry.py`. New implementation goes in `langextract/core/` or the owning module, not in the shim.

**Functions:**

- `snake_case` for functions and methods (`.pylintrc` `[BASIC]` `function-naming-style` / `method-naming-style`).
- Prefix module-private helpers with `_`: `_kwargs_with_environment_defaults` in `langextract/factory.py`, `_is_retryable_error` usage via `GeminiLanguageModel` in `langextract/providers/gemini.py`, `_safe_repr` in `langextract/core/debug_utils.py`.
- Public package entry points stay short verbs: `extract` and `visualize` in `langextract/__init__.py`.
- Test methods are `test_<behavior>` (`test_reasoning_model_key_precedence` in `tests/factory_test.py`). `tests/.pylintrc` also accepts `testCamelCase`, but new tests use `snake_case`.

**Variables:**

- `snake_case` for locals, arguments, and attributes.
- Module constants are `UPPER_SNAKE`. Public constants are exported (`EXTRACTIONS_KEY` in `langextract/core/data.py`). Private defaults use a leading underscore (`_DEFAULT_MODEL_ID`, `_RETRYABLE_API_CODES` in `langextract/providers/gemini.py`).
- Dummy / unused names match `.pylintrc` `dummy-variables-rgx`: `_`, `_unused_*`, `ignored_*`.
- `good-names` allows `i`, `j`, `k`, `ex`, `Run`, `_`, `id`, `ok`. Do not use `foo`, `bar`, `baz` (listed in `bad-names`).

**Types:**

- Classes are `PascalCase`: `ModelConfig`, `GeminiLanguageModel`, `AnnotatedDocument`.
- Enums are `PascalCase` classes with lowercase string values:

```python
class AlignmentStatus(enum.Enum):
  MATCH_EXACT = "match_exact"
```

  (`langextract/core/data.py`)
- Exception classes end in `Error` and subclass `LangExtractError` (`langextract/core/exceptions.py`).
- Type parameters and aliases stay `PascalCase` (`FormatType` re-exported from `langextract/core/types.py`).
- Protocol / ABC names describe the role: `BaseLanguageModel` (`langextract/core/base_model.py`), `AbstractResolver` (`langextract/resolver.py`), `BaseSchema` (`langextract/core/schema.py`).

## Code Style

**Formatting:**

- Formatter: `pyink==24.3.0` (Google's Black fork). Config in `pyproject.toml` `[tool.pyink]`:
  - `line-length = 80`
  - `pyink-indentation = 2` (two spaces, not four)
  - `pyink-use-majority-quotes = true` (quote style follows the majority already in the file; do not hand-convert a file to the other quote)
  - `unstable = true`
- Import sorter: `isort==5.13.2` with `[tool.isort]` `profile = "google"`, `line_length = 80`, `force_sort_within_sections = true`.
- `single_line_exclusions` allows one-line multi-imports only from `typing`, `typing_extensions`, and `collections.abc`. Every other import is one name per line.
- Line endings are LF (`.pylintrc` `expected-line-ending-format=LF`, `.pre-commit-config.yaml` `mixed-line-ending --fix=lf`).
- Pre-commit (`.pre-commit-config.yaml`) also enforces trailing-whitespace, end-of-file-fixer, check-yaml, check-merge-conflict, and a 1000 KB added-file cap.
- Run `./autoformat.sh` before submitting. It formats `langextract` and `tests` only. CI `format-check` in `.github/workflows/ci.yaml` runs `pyink --check --diff .` and `isort --check-only --diff .`.
- Pylint indent matches pyink: `indent-string="  "` and `indent-after-paren=2` in `.pylintrc`. `line-too-long` and `bad-indentation` are disabled because pyink owns them. URLs may exceed 80 columns (`ignore-long-lines`).

**Linting:**

- Pylint `>=3.0` with plugins `pylint.extensions.docparams` and `pylint.extensions.typing` (`.pylintrc` `[MASTER]`).
- Source: `pylint --rcfile=.pylintrc langextract`
- Tests: `pylint --rcfile=tests/.pylintrc tests` (inherits the parent rc and relaxes duplicate-code, missing docstrings, protected-access, and complexity limits).
- `tox -e lint-src` and `tox -e lint-tests` are what CI runs (`.github/workflows/ci.yaml` job `test`).
- Import boundaries are enforced by `import-linter` (`pyproject.toml` `[tool.importlinter]`, CI step `lint-imports --config pyproject.toml`):
  - `langextract.providers` must not import `langextract.inference`.
  - `langextract.core` must not import `langextract.providers`.
  - `langextract.core` must not import `langextract.annotation`, `langextract.chunking`, `langextract.prompting`, or `langextract.resolver`.
- Complexity messages (`too-many-arguments`, `too-many-branches`, `too-many-locals`, `too-many-statements`, `too-many-positional-arguments`, `too-many-nested-blocks`) are disabled in `.pylintrc`. Still split a function when it mixes policy and I/O. Configured ceilings if you re-enable them: `max-args=7`, `max-locals=15`, `max-branches=12`, `max-statements=50`, `max-returns=6`, `max-nested-blocks=5`, `max-module-lines=2000`.
- `pytype>=2024.10.11` is a `dev` extra in `pyproject.toml` and `# pytype: disable=...` comments exist (for example `langextract/visualization.py`), but tox and CI do not run pytype. Do not add a pytype job as part of an unrelated change.
- `# type: ignore[...]` is reserved for genuine checker gaps (`langextract/visualization.py`, `langextract/providers/openai_batch.py`). Do not blanket-ignore a module.

**Header and layout of every Python file:**

```python

# Copyright 2025 Google LLC.

#

# Licensed under the Apache License, Version 2.0 (the "License");

# ...

"""One-line summary of the module.

Optional longer explanation.
"""
from __future__ import annotations
```

Copy the header from `langextract/factory.py`. Put `from __future__ import annotations` immediately after the module docstring in library modules.

## Import Organization

**Order:**

1. `from __future__ import annotations`
2. Standard library (`import` and `from` mixed, isort-sorted). Multi-import only for `typing` / `collections.abc`.
3. Third party (`absl`, `google`, `openai`, `pydantic`, `yaml`, `regex`, …)
4. First party, always `from langextract... import ...` one module per line

Blank line between groups. Example from `langextract/providers/gemini.py`:

```python
from __future__ import annotations

import concurrent.futures
import dataclasses
from typing import Any, Final, Iterator, Sequence

from absl import logging
from google.genai import types as genai_types

from langextract.core import base_model
from langextract.core import exceptions
from langextract.providers import router
```

**Path Aliases:**

- No `src/` layout and no import aliases in `pyproject.toml`. Import the package as `langextract`.
- Short local aliases are used when a module name would collide or is verbose: `format_handler as fh` (`langextract/extraction.py`), `prompt_validation as pv`, `tokenizer as tokenizer_lib`, `types as core_types`, `output_schema as output_schema_lib`.
- Tests import the public package as `import langextract as lx` when they exercise the user API (`tests/init_test.py`, `tests/factory_test.py`). Import the module under test directly (`from langextract import factory`) when asserting private helpers.
- Lazy imports inside a function are allowed only to break a cycle or to keep an optional dependency off the import path, and they carry `# pylint: disable=import-outside-toplevel` (`langextract/extraction.py` imports `debug_utils` only when `debug=True`; `langextract/providers/openai.py` imports the OpenAI SDK inside the provider).

**Do not:**

- Wildcard-import except in a compatibility shim. `langextract/data.py` and `langextract/tokenizer.py` re-export `langextract.core.data` / `langextract.core.tokenizer` with `# pylint: disable=unused-wildcard-import`. New public modules use an explicit `__all__`.
- Import a provider from `langextract.core`, or import `langextract.inference` from `langextract.providers` (import-linter will fail CI).

## Error Handling

**Patterns:**

- Every library exception subclasses `LangExtractError` in `langextract/core/exceptions.py`. Users catch the base class to handle all LangExtract failures.
- Hierarchy to use:
  - `InferenceConfigError` — missing API key, bad model id, unsupported `output_schema`, import failure while loading a provider.
  - `InferenceRuntimeError` — provider call failed. Pass `original=` and `provider=` so callers can inspect the SDK exception.
  - `InferenceOutputError` — model returned no scored outputs.
  - `InvalidDocumentError` — duplicate ids or malformed documents.
  - `InternalError` — broken internal invariant (a bug, not user input).
  - `ProviderError`, `SchemaError`, `FormatError`, `FormatParseError` — backend, schema, and fence/JSON/YAML parse failures.
  - Domain errors subclass the base in the owning module (`ResolverParsingError` in `langextract/resolver.py`, `PromptAlignmentError` in `langextract/prompt_validation.py`, `TokenUtilError` in `langextract/chunking.py`).
- Repeated messages go through constructors in `langextract/core/exceptions.py`: `unsupported_output_schema_error`, `output_schema_fence_error`, `output_schema_format_error`, `output_schema_provider_kwargs_error`. Call those instead of inlining the same sentence.
- Chain with `raise ... from e`. `langextract/factory.py`:

```python
except (ModuleNotFoundError, ImportError) as e:
  raise exceptions.InferenceConfigError(
      "Failed to load provider. "
      "This may be due to missing dependencies. "
      f"Check that all required packages are installed. Error: {e}"
  ) from e
```

- Catch the narrow type (`ValueError`, `TypeError`, `requests.RequestException`, `google_exceptions.NotFound`). `.pylintrc` `[EXCEPTIONS]` flags `except Exception` and `except BaseException`. The cache path in `langextract/providers/gemini_batch.py` still uses broad handlers around GCS I/O; do not copy that into new code.
- Deprecations use `warnings.warn(..., FutureWarning, stacklevel=2)` and name the removal version. `langextract/extraction.py` warns that `language_model_type` and `gemini_schema` go away in v2.0.0. Shims such as `langextract/registry.py` warn on attribute access and forward to `langextract.plugins`.
- User-correctable misuse that should not fail the call uses `UserWarning` with `stacklevel=2` (batch_length vs max_workers in `langextract/extraction.py`, multiple API keys in `langextract/factory.py`).
- The public re-export `langextract/exceptions.py` only mirrors a subset (`LangExtractError`, `InferenceError`, `InferenceConfigError`, `InferenceRuntimeError`, `InferenceOutputError`, `ProviderError`, `SchemaError`). Add new types to `langextract/core/exceptions.py`. Import new code from `langextract.core.exceptions`, which is what `langextract/exceptions.py` tells callers to do.
- `InferenceRuntimeError.__init__` stores `original` and `provider` after `super().__init__(message)`. Follow that shape when an exception needs extra context.

## Logging

**Framework:** `absl.logging` for operational logs. The stdlib logger `"langextract"` is for debug tracing only.

**Patterns:**

- `from absl import logging` then old-style `%` formatting. `.pylintrc` sets `logging-format-style=old`. Write:

```python
logging.info("Batch job created successfully: %s", job.name)
logging.warning("Cache read error for %s: %s", key_hash, e)
```

  (`langextract/providers/gemini_batch.py`). Do not put an f-string in a logging call.
- Levels in use: `logging.debug` for plugin discovery (`langextract/plugins.py`), `logging.info` for batch/job progress (`langextract/annotation.py`, `langextract/providers/gemini.py`), `logging.warning` for skipped or degraded work.
- Call-level tracing uses `@debug_log_calls` and `configure_debug_logging()` in `langextract/core/debug_utils.py`. `extract(..., debug=True)` calls `configure_debug_logging()`. The decorator no-ops unless the `"langextract.debug"` logger is at DEBUG, redacts `api_key`, `apikey`, `token`, `secret`, `password`, `authorization`, `bearer`, and `jwt`, and truncates large values (`_MAX_STR = 500`, `_MAX_SEQ = 20`).
- `debug_utils` installs a `logging.NullHandler` on `"langextract"` so imports stay quiet. Do not call `logging.basicConfig` from library code.
- `configure_debug_logging()` sets absl verbosity to DEBUG inside `try/except` so a host without absl flags still works. Leave that best-effort block in place.

## Comments

**When to Comment:**

- Module docstring on every file, directly after the Apache header. Public modules explain the role and, for shims, where the implementation moved (`langextract/data.py`, `langextract/registry.py`, `langextract/_compat/README.md`).
- Google-style docstrings on public classes and functions: one-line summary, then `Args:`, `Returns:`, `Raises:`, `Attributes:` as applicable. See `ModelConfig` and `create_model` in `langextract/factory.py`, and `Extraction` in `langextract/core/data.py`.
- `.pylintrc` disables `missing-function-docstring`, `missing-class-docstring`, and `missing-raises-doc`, so a one-line private helper may omit a docstring. Still document public API and any helper whose name does not state the invariant (the retry phrase list in `langextract/providers/gemini.py` is commented because bare "quota" is intentionally not retryable).
- `# TODO(v2.0.0): ...` marks scheduled removals (`langextract/extraction.py`). `.pylintrc` disables the `fixme` check; `notes=FIXME,XXX,TODO` is informational only.
- File-level `# pylint: disable=duplicate-code` is used where two providers or schemas share a block (`langextract/providers/openai.py`, `langextract/providers/ollama.py`, `langextract/providers/schemas/gemini.py`, `langextract/exceptions.py`). Prefer a shared helper over a new disable.
- Inline `# pylint: disable=protected-access` belongs in tests that must touch `_` members (`tests/create_provider_plugin_test.py`), not in library code.

**JSDoc/TSDoc:**

- Not applicable. This is a Python library. Docstrings are Sphinx/Google style consumed by `pylint.extensions.docparams`, not JSDoc.

## Function Design

**Size:**

- Pylint complexity caps are disabled, so size is a review concern rather than a gate. `extract` in `langextract/extraction.py` is the orchestration function; new behavior should land in a helper (`prompt_validation`, `factory.create_model`) instead of growing `extract` further.
- Private helpers stay small and single-purpose: `_is_non_bool_integral` in `langextract/providers/gemini.py`, `_redact_value` in `langextract/core/debug_utils.py`.

**Parameters:**

- Annotate parameters and returns. With `from __future__ import annotations`, prefer `str | None` over `Optional[str]`.
- Use `collections.abc` (`Sequence`, `Mapping`, `Iterator`) for public container inputs (`langextract/core/base_model.py`). `typing.Any` is acceptable at provider boundaries.
- Put optional, easy-to-confuse arguments after `*` so they are keyword-only. `Extraction.__init__` and `Document.__init__` in `langextract/core/data.py` do this. `create_model_from_id` in `langextract/factory.py` does this for `provider`.
- Provider `**kwargs` are stored on the model (`BaseLanguageModel._extra_kwargs`) and merged at inference time via `merge_kwargs`, with runtime kwargs winning. Pass unknown provider options through that path instead of dropping them.
- Dataclass configs that are value objects use `@dataclasses.dataclass(slots=True, frozen=True)` (`ModelConfig` in `langextract/factory.py`, `BatchConfig` in `langextract/providers/gemini_batch.py`). Mutable documents use a plain `@dataclasses.dataclass` plus an explicit `__init__` when a field is a property (`Document`, `Extraction`).

**Return Values:**

- Return a concrete type. `create_model` returns `BaseLanguageModel` unless `return_fence_output=True`, in which case it returns `(model, bool)` — do not add a third shape.
- Generators are the inference contract: `infer` yields `Iterator[Sequence[ScoredOutput]]` (`langextract/core/base_model.py`). Batch helpers yield the same shape.
- Properties that lazily compute cache the private field and expose a getter/setter (`Document.tokenized_text`, `Extraction.token_interval`). Do not recompute tokenization on every read.

## Module Design

**Exports:**

- Public modules set `__all__`. `langextract/__init__.py` exports `extract`, `visualize`, and the lazy submodule names. `langextract/core/data.py` exports the data classes and `EXTRACTIONS_KEY`.
- Top-level attribute access is lazy (`_LAZY_MODULES` + `__getattr__` in `langextract/__init__.py`). Adding a heavy import at module top of `langextract/__init__.py` defeats that. Register a new public submodule in both `__all__` and `_LAZY_MODULES`.
- `langextract/__init__.py` currently eager-imports `visualization` and `extraction.extract`. Leave those two; do not add more eager imports.
- The supported user import is `import langextract as lx` then `lx.extract(...)`. The usage skill at `skills/langextract-usage/SKILL.md` is the contract for that surface: few-shot `ExampleData` is required, `extraction_text` is verbatim source text, and provider selection is `model_id` or `lx.factory.ModelConfig`. New public parameters on `extract` should match that calling style (keyword arguments, no new required positional args).
- Backward-compatible module paths stay as thin shims. `langextract/registry.py` forwards to `langextract.plugins` with a `FutureWarning`. `langextract/_compat/` holds the older inference/schema/exception/registry surfaces (`langextract/_compat/README.md`). Put removal-bound aliases there or in the shim, not new behavior.

**Barrel Files:**

- Do not add a barrel that re-exports every class from `langextract/__init__.py`. Callers use `lx.data.Extraction` via lazy submodule load.
- `langextract/providers/__init__.py` is the provider facade (`load_plugins_once`, `load_builtins_once`, `__getattr__`). Plugin registration uses the entry-point group `langextract.providers` declared in `pyproject.toml`.
- A new first-party provider implements `BaseLanguageModel`, lives in `langextract/providers/<name>.py`, registers with `@router.register` (`langextract/providers/router.py`), and is listed in the entry-point table. Prefer an external plugin (`scripts/create_provider_plugin.py`, `examples/custom_provider_plugin/`) over editing core. `langextract/providers/README.md` is the provider contract.
- `langextract/core/` stays dependency-light: types, exceptions, tokenizer, schema, format handler, base model. High-level pipeline code (`annotation.py`, `chunking.py`, `prompting.py`, `resolver.py`, `extraction.py`) sits above core and may import it. Core must not import those modules or `langextract.providers`.

---

*Convention analysis: 2026-10-09*

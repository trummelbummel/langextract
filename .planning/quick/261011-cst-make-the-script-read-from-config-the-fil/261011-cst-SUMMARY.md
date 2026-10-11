---
phase: 261011-cst
plan: 01
subsystem: tooling
tags: [trace_extract, config, ollama, chunking]

requires:
  - phase: 05-live-extract-ollama-preflight
    provides: scripts/trace_extract.py live path and offline stub tests
provides:
  - config.yaml document_path as source of truth for extract input text
  - max_char_buffer and context_window_chars forwarded into lx.extract kwargs
  - make trace with no positional document argument
affects: [live-trace, phase-05]

actuals:
  tokens: 1755
  tasks: 2
  commits: 2

plan_head_before: 395995da151cf07af4c59aa103070f0864c7f13e

tech-stack:
  added: []
  patterns:
    - "Repo-relative document_path resolved via _REPO_ROOT before UTF-8 read"
    - "Chunk call constants live in config.yaml and pass through _extract_kwargs"

key-files:
  created: []
  modified:
    - config.yaml
    - scripts/trace_extract.py
    - tests/trace_extract_test.py
    - Makefile

key-decisions:
  - "document_path replaces sample_text; relative paths resolve against repo root not cwd"
  - "Removed CLI document positional so config owns the file (plan assumed argparse was already catalog-only)"
  - "max_char_buffer: 1000 and context_window_chars: null match library defaults while staying editable"

patterns-established:
  - "Short temp document_path in TraceExtractLiveTest keeps stub one-/api/generate contract"

requirements-completed: [QUICK-DOC-01, QUICK-CHUNK-01]

coverage:
  - id: D1
    description: "config document_path file contents become text_or_documents"
    requirement: QUICK-DOC-01
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py::TraceExtractDocumentTest::test_extract_kwargs_text_from_document_path_not_sample_text"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py::TraceExtractDocumentTest::test_document_path_resolves_relative_to_repo_root_not_cwd"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py::TraceExtractDocumentTest::test_missing_document_exits_with_error_and_resolved_path"
        status: pass
    human_judgment: false
  - id: D2
    description: "max_char_buffer and context_window_chars from config reach lx.extract kwargs"
    requirement: QUICK-CHUNK-01
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py::TraceExtractDocumentTest::test_extract_kwargs_includes_chunk_buffer_from_config"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py::TraceExtractDocumentTest::test_extract_kwargs_passes_null_context_window_chars"
        status: pass
    human_judgment: false
  - id: D3
    description: "make trace runs without a positional document; stub live path still one generate"
    requirement: QUICK-DOC-01
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py::TraceExtractLiveTest::test_run_live_walks_one_extract_against_stub"
        status: pass
      - kind: other
        ref: "Makefile trace target invokes scripts/trace_extract.py with no args"
        status: pass
    human_judgment: false

duration: 2min
completed: 2026-10-11
status: complete
---

# Phase 261011-cst Plan 01: Config document & chunk kwargs Summary

**Live `trace_extract` now loads document text and chunk sizes from `config.yaml`; `make trace` no longer takes a document path.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-10-11T07:15:34Z
- **Completed:** 2026-10-11T07:17:34Z
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments

- `document_path: data/example_document.md` replaces `sample_text`; `_load_document_text` resolves relative paths against `_REPO_ROOT` and fails closed on missing files
- `_extract_kwargs` forwards `max_char_buffer` and `context_window_chars` (YAML `null` → Python `None`)
- Makefile `trace` drops `TRACE_DOCUMENT`; offline suite 71 passed

## Task Commits

1. **Task 1: Config document_path → text_or_documents** - `adaba08` (feat)
2. **Task 2: Config-driven max_char_buffer and context_window_chars** - `d70aa60` (feat)

**Plan metadata:** skipped (commit_docs handled by orchestrator for quick tasks)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Removed CLI document positional**
- **Found during:** Task 1
- **Issue:** Plan assumed `main()` already had only `--catalog-only`, but the script still accepted an optional document path that overwrote `sample_text`. Keeping that path after removing `sample_text` would break or reintroduce a second source of truth.
- **Fix:** Dropped the positional `document` argparse entry and its override branch; document selection is config-only. Updated module usage docstring. Makefile already aligned in the same task.
- **Files modified:** `scripts/trace_extract.py`, `Makefile`
- **Commit:** `adaba08`

## Auth Gates

None.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: config.yaml document_path, max_char_buffer, context_window_chars; no sample_text
- FOUND: scripts/trace_extract.py `_load_document_text` and chunk kwargs
- FOUND: Makefile trace without TRACE_DOCUMENT / positional
- FOUND: commits adaba08, d70aa60
- FOUND: tests/trace_extract_test.py TraceExtractDocumentTest + LiveTest short temp doc

---
phase: quick-261014-g6y
plan: 01
subsystem: observability
tags: [on_event, TokenUsage, chunk_events, ollama]
requires: []
provides:
  - "extract(..., on_event=) with ChunkStarted/ChunkFinished/ParseFailed events"
  - "ScoredOutput.usage TokenUsage filled by Ollama"
affects: [dashboards, provider-usage]
actuals:
  tokens: 12000
  tasks: 3
  commits: 4
tech-stack:
  added: []
  patterns: [per-run safe event dispatcher, resolve-unsuppressed-then-apply-user-setting]
key-files:
  created:
    - langextract/core/events.py
    - tests/chunk_events_test.py
  modified:
    - langextract/annotation.py
    - langextract/extraction.py
    - langextract/core/types.py
    - langextract/providers/ollama.py
    - tests/inference_test.py
key-decisions:
  - "error_type is the underlying cause class name (FormatError/ValueError) when present"
  - "ScoredOutput.usage uses compare=False so existing equality tests stay green"
  - "TokenUsage shipped in RED stub (Task 1) because ChunkFinished.usage needs it"
patterns-established:
  - "Observer exceptions: catch Exception, log warning once per run via Dispatcher"
  - "When on_event is set, resolve with suppress_parse_errors=False, emit, then apply user setting"
requirements-completed: [OBS-AC1, OBS-AC2, OBS-AC3, OBS-AC4, OBS-AC6, OBS-AC7, OBS-AC8, OBS-AC9]
duration: 45min
completed: 2026-10-14
status: complete
---

# Quick 261014-g6y: Per-chunk observability Summary

`lx.extract(..., on_event=cb)` now delivers per-chunk start/finish/parse-failure
events on the calling thread, and Ollama fills `ScoredOutput.usage`.

## Commits

| Task | Hash | Message |
|------|------|---------|
| RED | d074017 | test(261014-g6y): RED for per-chunk observability events |
| RED approve | c120c14 | docs(261014-g6y): RED checkpoint approved |
| 1 | 06de1b6 | feat(261014-g6y): per-chunk chunk_started/chunk_finished events via on_event |
| 2 | 5c13a85 | feat(261014-g6y): emit parse_failed per chunk even when suppressed |
| 3 | 0d79f88 | feat(261014-g6y): TokenUsage on ScoredOutput, filled by Ollama |

## Tests

- `tests/chunk_events_test.py` — 18 passed
- Ollama usage tests in `tests/inference_test.py` — passed
- `annotation_test` / `resolver_test` / `extract_precedence_test` — passed
- OpenAI / factory collection failures are pre-existing (`openai` package missing); unrelated

## Deferred follow-ups

- Slice 2: `LoggingObserver` + docs OpenTelemetry example
- Slice 4: `model_call_failed` (AC5)
- Slice 5b/5c: OpenAI / Gemini usage mapping

## Open questions (recorded, not blocking)

- `error_type` value: underlying cause class name (chosen)
- Non-callable `on_event` is not validated (spec defines no rejection)
- `ScoredOutput.usage` uses `compare=False`

---
id: 261014-g6y
commits: d074017..e391ae0
timestamp: 2026-10-14T10:40:00Z
coverage: "413/413 cells, 0 invalid entries"
---

# Style review — 261014-g6y

## Review guide

1. **What changed in behavior** — none from style refactors (rename helpers, `_ChunkEmitMeta`, outcome constants, test parametrization). Production behavior of `on_event` unchanged.
2. **Read in this order** — `core/events.py` → `annotation.py` emit/resolve helpers → `providers/ollama.py` `_usage_from_response` → `tests/chunk_events_test.py`.
3. **Look closely at** — `Dispatcher.emit` broad `except Exception` (R15-PENDING); parse-error `continue` path; public event field shape (R39).
4. **Safe to skim** — outcome constants, short renames, oracle NamedTuple, usage test parametrization.

## R15 — Swallowed exceptions (deferred / PENDING)

| File | Line | Except | Verdict | Action taken |
|------|------|--------|---------|--------------|
| langextract/core/events.py | 101 | Exception | R15-PENDING | Gate decides; AC6 locked soft path |
| langextract/annotation.py | 458 | ResolverParsingError | R15-PENDING | Gate decides; suppress contract |

## Fixed (this review)

| File | Rule | Change |
|------|------|--------|
| core/events.py | R37 | Removed `make_dispatcher` middle-man; callers use `Dispatcher(on_event)` |
| core/events.py | R60 | Trimmed `__all__` to event types + `EventCallback` |
| annotation.py | R39 | Replaced `chunk_meta` 4-tuple with private `_ChunkEmitMeta` |
| annotation.py | R03/R05/R38 | Emit/resolve helpers; `OUTCOME_OK` / `OUTCOME_PARSE_ERROR` |
| annotation.py | R06 | `scored_outputs[0].usage` (no defensive getattr) |
| ollama.py | R05/R38 | `_optional_number` + `_NANOSECONDS_PER_SECOND` |
| chunk_events_test.py | R18/R22/R27 | Parametrized usage twins; tighter assertions; `_ExpectedChunk` |

## Reported (needs human / separate task)

| File | Line | Rule | Finding | Suggested fix | Verdict | Signals | Risk |
|------|------|------|---------|---------------|---------|---------|------|
| core/events.py | 38 | R39 data-clump | Three events repeat six chunk identity fields | Compose frozen `ChunkRef` into each event | ⚠️ complex | H1 public constructors; locked flat fields in spec | breaking / locked-conflict |
| inference_test.py | 164 | R18 parametrize-twins | Ollama generate vs gpt-oss usage tests near-twins | `named_parameters` over patch target / response | ✅ simple | — | safe |
| chunk_events_test.py | 267 | R19 one-behavior | Multi-behavior tests (pass_index, extract str/docs, parse suppress) | Split into named single-behavior methods | ✅ simple | — | safe |
| (6 files) | — | R65 separate-moves | RED commit mixed production stubs with tests | Historical only; do not rewrite without ask | ⚠️ complex | H5 rewrite strategy | held: historical |

**Summary:** 2 simple / 2 complex out of 4 open findings (+ 2 R15-PENDING).

### Steering (complex)

**R39 ChunkRef:** Spec lists flat fields on each event and says fields are only added, never renamed. Composing `ChunkRef` changes constructors.
1. Prefer flat fields forever (waive R39), or add `ChunkRef` as an *additional* nested field while keeping flat aliases?
2. If nested only: break `ChunkStarted(...)` kwargs compatibility — OK before first release?

**R65 RED/prod mix:** Commits already on branch.
1. Leave history; enforce split on future quick tasks only?
2. Interactive rebase to split `d074017` (rewrites shared history)?

## Coverage

`coverage: 413/413 cells, 0 invalid entries` (hitl + design + contracts + data + readability + conventions + review + tests + errors).

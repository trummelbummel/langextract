# LangExtract pipeline trace

## What This Is

A developer-facing walkthrough of the existing LangExtract library. The first milestone is a small script that runs one `lx.extract()` call against a local Ollama model (`gemma3:4b`) and prints each pipeline stage: the function and file that owns it, and the data going in and out. The library stays the product. The script is how you see which stage a later change would touch.

## Core Value

You can follow one `lx.extract()` call from the prompt through to an `AnnotatedDocument` and see which function owns each stage.

## Requirements

### Validated

- ✓ `lx.extract` turns unstructured text into a grounded `AnnotatedDocument` — existing (`langextract/extraction.py`, `langextract/__init__.py`)
- ✓ Few-shot prompt text is built per chunk — existing (`langextract/prompting.py`)
- ✓ Long documents are split into sentence-aware chunks — existing (`langextract/chunking.py`)
- ✓ A pluggable provider, including Ollama over local HTTP, runs the model call — existing (`langextract/providers/ollama.py`, `langextract/factory.py`)
- ✓ Model text is parsed into `Extraction` objects — existing (`langextract/resolver.py`, `langextract/core/format_handler.py`)
- ✓ Extractions are aligned back to character spans in the source — existing (`Resolver.align` / `WordAligner` in `langextract/resolver.py`)
- ✓ The public result is an `AnnotatedDocument` — existing (`langextract/core/data.py`)
- ✓ Stage catalog prints ordered labels plus owning function/file and a static call header from `config.yaml` — Phase 1 (`scripts/trace_extract.py`, repo-root `config.yaml`)
- ✓ Call-scoped probes install and restore five class wraps — Phase 3
- ✓ Stage wrappers record live in/out for chunk → prompt → model → parse → align (offline), with raw model text, empty-parse callouts, and format flags — Phase 4

### Active

- [ ] A small script runs one `lx.extract()` call using local Ollama `gemma3:4b`
- [ ] The script prints a walkthrough through `AnnotatedDocument` on a live call (Phases 5–6)
- [ ] Production path installs stage wrappers via `trace_probes` for the live extract

### Out of Scope

- Library or API changes — later feature work waits until a specific change is named
- A reusable tracer that can be turned on for arbitrary later `extract()` calls — this milestone is one printed walkthrough of one call
- Cloud providers (Gemini, OpenAI, Vertex) for the script — the run uses local Ollama only
- Replacing `examples/ollama/demo_ollama.py` — that demo shows extraction results and HTML visualization, not a stage trace

## Context

LangExtract (`langextract`, public alias `lx`) is an existing Python library. One public function, `extract` in `langextract/extraction.py`, owns call order: prompt, chunk, provider `infer`, parse, align, then `AnnotatedDocument`. Grounding is separate from parsing. `Resolver.resolve` yields unaligned extractions; `Resolver.align` writes source spans.

Ollama is already a built-in provider. `langextract/providers/ollama.py` POSTs to the local server (default `http://localhost:11434`). `examples/ollama/demo_ollama.py` already runs extractions against Ollama, defaulting to `gemma2:2b`. This project does not extend that demo. It adds a trace of the stages inside one call, using `gemma3:4b`, which is already available locally.

The codebase map in `.planning/codebase/` (refreshed 2026-10-09) is the reference for which file owns each stage.

## Constraints

- **Compatibility**: The script calls the existing public pipeline. It does not change `lx.extract` behavior or provider contracts.
- **Runtime**: Local Ollama must already be serving `gemma3:4b`. No new cloud credentials.
- **Stack**: Python `>=3.10`, the installed `langextract` package, and the existing Ollama HTTP client (`requests` in `langextract/providers/ollama.py`).
- **Scope**: First milestone is the script only. Unnamed library changes stay out until they are named.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Script first, then later LangExtract changes | Feature requests tend to touch one stage; the trace shows which stage before any library edit | Confirmed — Phase 1 touches only `scripts/` + `config.yaml` |
| Printed stage dump, not a result-only demo and not a reusable tracer | Each stage must show owning function, file, and data in/out for a single call | Phase 1: owners/files + call header; live payloads deferred |
| First milestone is only the script | Later library changes wait until one is named | — Pending |
| Local Ollama `gemma3:4b` | The model is already available locally; the existing Ollama demo targets a different model and a different output | Configured in `config.yaml` (Phase 1); live call in later phase |
| Repo-root `config.yaml` for call constants / empty-parse / redact keys | Keeps script knobs out of the library and demo | Shipped Phase 1 |
| Call-scoped `trace_probes()` with class-attribute assign/restore (no `mock.patch` in script) | Observation must not leak across calls; `finally` restore is the hard gate before live Ollama | Shipped Phase 3 |
| Chunk identity returns the iterator object; model/align use `yield from` | `ChunkIterator.__iter__` returns `self` — yield-from would recurse | Shipped Phase 3 |
| Optional `wrappers=` map keyed by catalog labels; unknown keys → `ValueError` | Phase 4 `make_stage_wrappers` contract; partial maps fill with identity | Shipped Phase 3 |
| In-script restore self-check after catalog (silent / stderr + exit 1) | Proves exception-path restore on every catalog run without calling `lx.extract` | Shipped Phase 3 |
| Offline `_patch_stages` / `lx.extract` for Phase 4 verification; live install in Phase 5 | Phase 4 goal is warm-model-free; probes land in Phase 3 | Shipped Phase 4 (UAT 15/15) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-11 after Phase 4*

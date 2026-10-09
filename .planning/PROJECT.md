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

### Active

- [ ] A small script runs one `lx.extract()` call using local Ollama `gemma3:4b`
- [ ] The script prints a walkthrough of prompting, chunking, the model call, parsing, alignment (source grounding), and `AnnotatedDocument`
- [ ] Each stage in that walkthrough names the owning function and file, and shows the data going in and out

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
| Script first, then later LangExtract changes | Feature requests tend to touch one stage; the trace shows which stage before any library edit | — Pending |
| Printed stage dump, not a result-only demo and not a reusable tracer | Each stage must show owning function, file, and data in/out for a single call | — Pending |
| First milestone is only the script | Later library changes wait until one is named | — Pending |
| Local Ollama `gemma3:4b` | The model is already available locally; the existing Ollama demo targets a different model and a different output | — Pending |

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
*Last updated: 2026-10-09 after initialization*

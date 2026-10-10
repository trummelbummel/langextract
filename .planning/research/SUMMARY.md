# Project Research Summary

**Project:** LangExtract pipeline trace
**Domain:** Developer walkthrough of one source-grounded `lx.extract()` call through local Ollama
**Researched:** 2026-10-10
**Confidence:** HIGH

## Executive Summary

This milestone is not a new extraction product. LangExtract (`langextract` 1.7.1, alias `lx`) stays the library; the deliverable is `scripts/trace_extract.py` — a one-call printed walkthrough of prompting, chunking, model inference, parse, alignment (source grounding), and the returned `AnnotatedDocument`, each naming the owning function and file with live data in/out. The locked path is local Ollama `gemma3:4b` via the built-in provider; no cloud providers, no reusable tracer, no library API changes, and no replacement of `examples/ollama/demo_ollama.py`.

Experts observing pipelines like this either instrument inside the framework or rebuild stages beside the public entry. Research rejects both for this milestone: intermediates are locals inside `extract`, and a parallel Annotator/Resolver path drifts on format defaults (YAML vs JSON) and risks a second model call. The recommended approach is call-scoped class-attribute probes on five methods `extract` already invokes (`ChunkIterator.__iter__`, `ContextAwarePromptBuilder.build_prompt`, `OllamaLanguageModel.infer`, `Resolver.resolve`, `Resolver.align`), with field snapshots (especially at parse, before align mutates the same `Extraction` objects), then one `lx.extract(...)` and print of its return value. Stack is thin: CPython 3.12, editable `langextract`, existing `requests`, stdlib `inspect`/`pprint` — no OpenTelemetry, LangSmith, wrapt, or PyPI `ollama` client.

Key risks are collapsing parse into align by printing live objects after mutation; monkeypatch leaks / bound-method restore failures; wrong Ollama call shape (`OLLAMA_BASE_URL` ignored for `gemma3:4b`, `num_ctx=2048` vs 128k card, 120s cold-load timeout); wrapping `WordAligner` and capturing prompt-validation as grounding; and reading `suppress_parse_errors` empty lists as “no entities.” Mitigate with snapshot-before-align, `finally` restore of class attributes, explicit `model_url` + preflight `GET /api/tags`, probe `Resolver.align` only, and empty-parse callouts beside raw model text. Keep `extraction_passes=1`, short single-chunk sample, `debug=False`.

## Key Findings

### Recommended Stack

Details: [STACK.md](./STACK.md). Stay on the existing library and provider; add no frameworks.

**Core technologies:**
- **CPython 3.12** — script runtime (library floor stays `>=3.10`; do not raise `requires-python`) — matches newest CI interpreter; 3.10 EOL
- **langextract 1.7.1 (editable)** — pipeline under observation — `lx.extract` already owns prompt → chunk → infer → parse → align → `AnnotatedDocument`
- **Ollama ≥0.6 + `gemma3:4b`** — local model host and the one model call — model card requires 0.6+; `^gemma` routes to `OllamaLanguageModel`
- **`requests` (existing floor)** — HTTP inside the provider — script may preflight `/api/tags` with the same client; do not add PyPI `ollama`
- **stdlib `inspect` / `pprint`** — stage ownership and payload printing — `debug=True` truncates and does not cover these stages

**Critical call shape:** `model_id="gemma3:4b"`, explicit `model_url`, `extraction_passes=1`, leave fence/schema flags unset, pass `OLLAMA_FORMAT_HANDLER` via `resolver_params`, no `model=`, no `output_schema`. Provider defaults: `format: "json"`, `think: false`, `num_ctx=2048`, timeout 120s.

### Expected Features

Details: [FEATURES.md](./FEATURES.md). MVP is one printout, not a phased product surface.

**Must have (table stakes):**
- Header naming `lx.extract`, `gemma3:4b`, `OllamaLanguageModel`, host; Ollama preflight before stages
- Six stages in runtime order with stable labels, owning function + file, full live in/out for a short sample
- Shared prompt template, then chunk (text + char/token intervals), then rendered prompt
- Raw model string separate from parse; parse with grounding fields still null; align with spans/status/offsets
- Final `AnnotatedDocument` from the same single `extract()` / one `infer`
- Empty-parse called out in words; secrets redacted if kwargs printed

**Should have (competitive):**
- Before/after grounding pair (resolve record vs align record)
- Source slice beside span (or `ungrounded`)
- Format fence/wrapper key next to parse; `WordAligner` named under align (not its own stage)
- Offsets labeled even when zero on a one-chunk run

**Defer (v2+ / named change):**
- Reusable tracer / OpenTelemetry / library hooks on `extract`
- Multi-chunk / multi-pass / schema / cloud-provider walkthroughs
- HTML, JSONL, eval harness, persisted trace store (covered elsewhere)

### Architecture Approach

Details: [ARCHITECTURE.md](./ARCHITECTURE.md). External observer only — one file under `scripts/`, not installed, not under `langextract/`.

**Major components:**
1. **Stage catalog** — labels, owners, files; no I/O
2. **Stage printer** — stdout records (copies, not live objects)
3. **Extraction snapshot** — field copy at resolve return and align yield (align mutates in place)
4. **Call-scoped probes** — wrap five class methods for one call; restore in `finally`
5. **One `lx.extract` invocation** — factory builds Ollama model; script does not rebuild Annotator/Resolver
6. **Document printer** — print return value; no probe on private emit path

**Patterns to follow:** call-scoped observer on the live path; snapshot before alignment mutates; generator-transparent wrappers for `infer` and `align` (yield same items; forward kwargs). Do not wrap `WordAligner`, pass `model=`, or reassemble the pipeline beside `extract`.

### Critical Pitfalls

Details: [PITFALLS.md](./PITFALLS.md). Top risks for roadmap and execution:

1. **Parse/align collapse via live `Extraction` mutation** — snapshot fields at resolve return; never print the list after align as “parse”
2. **Parallel pipeline or `model=` path** — one `lx.extract` with `model_id`; class-wrap `OllamaLanguageModel.infer`; pass `OLLAMA_FORMAT_HANDLER`
3. **Monkeypatch leak / bound-method restore** — save/restore class attributes in `finally`; probe manager before any live call
4. **Wrong Ollama shape / empty-parse misread** — explicit `model_url`, preflight tags, short prompt under `num_ctx=2048`, empty-parse sentence + raw model text
5. **Wrong probe targets** — wrap `Resolver.align` not `WordAligner`; call `build_prompt` exactly once; keep generators transparent

## Implications for Roadmap

Based on research, suggested phase structure follows architecture build order (printer and probes before live Ollama). Keep each phase within CLAUDE.md diff budget (~150 non-test lines / ≤3 source files); the whole script is one small file, so phases are incremental slices of that file plus verification, not new packages.

### Phase 1: Catalog, printer, and contracts
**Rationale:** Record shape and “one call / one infer” rules must exist before wrappers, or parse vs align and empty-parse copy will be wrong later.
**Delivers:** `scripts/trace_extract.py` skeleton with stage catalog (stable labels, function, file), printer for data in/out, header fields, empty-parse sentence copy; no `extract` call required yet.
**Addresses:** Stable stage labels; owning function/file contract; empty-parse wording; secret-redaction rule (FEATURES table stakes + differentiators).
**Avoids:** Using `debug=True` or drifting into `demo_ollama.py` HTML/JSONL (Pitfalls 8, 10).

### Phase 2: Extraction snapshot helpers
**Rationale:** Align mutates the same objects resolve returns; without snapshots, later wrappers cannot show grounding as a separate stage.
**Delivers:** Snapshot helpers for ungrounded vs grounded `Extraction` fields (class, text, attributes, index, intervals, status).
**Addresses:** Before/after grounding pair; parse vs align distinguishability (FEATURES P1).
**Avoids:** Live-mutation collapse of parse/align (Pitfall 1).

### Phase 3: Call-scoped probe manager
**Rationale:** Restore discipline must land before any live call; failed restore leaks process-global patches.
**Delivers:** Context manager that installs and restores the five class attributes in `finally` (success and exception); no `extract` yet.
**Addresses:** Observation without library hooks (FEATURES anti-feature avoidance).
**Avoids:** Monkeypatch leak / bound restore (Pitfall 7); sets up class wrap for `infer` (Pitfall 3).

### Phase 4: Stage wrappers (chunk → prompt → infer → resolve → align)
**Rationale:** Wrappers encode pipeline order and generator transparency; they are testable against record rules before depending on a warm model.
**Delivers:** Probes for the five methods; prompt fidelity (single `build_prompt`); parse snapshot + align snapshot; format fence/wrapper inputs on parse; WordAligner named under align only.
**Addresses:** Six stages with live in/out; raw model vs parse; offsets even when zero; format flags (FEATURES P1).
**Avoids:** Double `build_prompt`, generator consume/replace, wrapping `WordAligner` (Pitfalls 4–6).

### Phase 5: Live one-call `lx.extract` + Ollama preflight
**Rationale:** First gate that needs local `gemma3:4b`; arguments must match the researched call shape so probes see the real factory path.
**Delivers:** Preflight `GET /api/tags`; one `lx.extract` with short sample, `model_id="gemma3:4b"`, `model_url`, `OLLAMA_FORMAT_HANDLER`, `extraction_passes=1`, `debug=False`, `show_progress=False`, `fetch_urls=False`; optional cold-load `timeout` via `language_model_params`.
**Uses:** Stack call shape; existing `requests` / provider HTTP.
**Implements:** Live path under probes; no second infer, no `model=`.
**Avoids:** Parallel pipeline, wrong host/env, multi-pass/multi-chunk story break, demo drift (Pitfalls 2, 3, 9, 11).

### Phase 6: AnnotatedDocument print and walkthrough verification
**Rationale:** Document must match the last align snapshots for that call; checklist closes “looks done but isn’t.”
**Delivers:** Print of returned `AnnotatedDocument`; source slice / `ungrounded`; end-to-end verification against PITFALLS checklist (one generate, parse null grounding, prompt == `batch_prompts`, restore after success/failure).
**Addresses:** Final document + source slice (FEATURES P1).
**Avoids:** Document/probe mismatch; silent empty success when Ollama is down (already preflighted in Phase 5).

### Phase Ordering Rationale

- Printer and snapshot rules before wrappers — record contract is the feature; wrappers only capture it.
- Probe manager before live call — restore-on-exception is a hard prerequisite (Pitfall 7).
- Wrappers before Ollama — generator and prompt-fidelity bugs are cheaper to catch without cold-load latency.
- Live `extract` is one phase after probes — the call is unreadable without them; probes are not a walkthrough without the printer’s snapshot rules.
- No phase rebuilds Annotator/Resolver or adds a tracer package — architecture anti-patterns and PROJECT.md out-of-scope.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (wrappers):** Confirm exact public method signatures and generator contracts against the live tree when implementing (`infer` kwargs, `align` offset names). Pipeline map is documented; edge cases around empty scored-output lists still deserve a quick code read at plan time.
- **Phase 5 (live Ollama):** Operational — cold-load timeout and `num_ctx` fit for the chosen few-shot sample should be validated on this machine (`timeout=300` is MEDIUM confidence).

Phases with standard patterns (skip research-phase):
- **Phase 1 (catalog/printer):** Stdlib stdout sections; stage map already locked in research.
- **Phase 2 (snapshot):** Plain field copies; mutation rule is well documented in ARCHITECTURE/PITFALLS.
- **Phase 3 (probe manager):** Stdlib try/finally class-attribute wrap; wrapt not needed.
- **Phase 6 (document print + checklist):** Verification against existing return type and pitfalls checklist.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Local tree + PyPI + Ollama model card + generate API docs; versions pinned to this repo |
| Features | MEDIUM | Local stage map HIGH; competitor/trace comparisons capped at MEDIUM (gsd-core websearch policy) |
| Architecture | HIGH | Mapped against local `extraction.py` / `annotation.py` / resolver / ollama provider |
| Pitfalls | HIGH | Library-path pitfalls HIGH; Ollama ops and monkeypatch ecosystem claims MEDIUM |

**Overall confidence:** HIGH

### Gaps to Address

- **Cold-load timeout on this machine:** 300s is example-README practice, not a measurement — validate during Phase 5 execution; keep as call arg only.
- **`gemma3:4b` vs thinking/format quirks:** Community reports cited for other Gemma lines; keep provider `think=False` and watch parse `[]` + raw text if JSON looks ignored.
- **No maintainer interview:** Stage owners come from codebase map; if a public method is renamed before implementation, re-check probe targets in Phase 4 planning.
- **How probes read intermediates without editing the library:** Resolved in ARCHITECTURE (call-scoped class wraps); treat as locked for roadmap — do not reopen as a library-hook design.

## Sources

### Primary (HIGH confidence)
- Local tree: `langextract/extraction.py`, `annotation.py`, `chunking.py`, `prompting.py`, `resolver.py`, `providers/ollama.py`, `factory.py`, `core/data.py`, `core/debug_utils.py`, `examples/ollama/demo_ollama.py`
- `.planning/PROJECT.md`, `.planning/codebase/` map (refreshed 2026-10-09)
- [STACK.md](./STACK.md), [FEATURES.md](./FEATURES.md), [ARCHITECTURE.md](./ARCHITECTURE.md), [PITFALLS.md](./PITFALLS.md)
- Ollama generate API / `gemma3:4b` model card; LangExtract README Ollama quickstart
- PyPI metadata for `langextract` 1.7.1 and dependency floors

### Secondary (MEDIUM confidence)
- OpenTelemetry GenAI spans (content Opt-In); DSPy `inspect_history`; LangSmith run format; LlamaIndex callbacks; spaCy `analyze_pipes` — used only to define anti-features
- wrapt transient-wrapper docs — pattern reference; package not adopted
- Example README 300s timeout; community thinking/format reports on adjacent Gemma lines

### Tertiary (LOW confidence)
- None material to roadmap shape; remaining uncertainty is operational (local cold load), not product direction

---
*Research completed: 2026-10-10*
*Ready for roadmap: yes*

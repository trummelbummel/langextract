# Pitfalls Research

**Domain:** Stage-trace of one source-grounded `lx.extract()` call through local Ollama `gemma3:4b`
**Researched:** 2026-10-10
**Confidence:** HIGH for library-path pitfalls (local tree + prior research); MEDIUM for Ollama server / monkeypatch ecosystem claims

This document covers mistakes people make when adding a **developer stage-trace** to the existing LangExtract pipeline — not greenfield LLM-app advice. The product stays `langextract`. The milestone is `scripts/trace_extract.py`: one printed walkthrough of one call.

Phase names below match the architecture research build order: **Catalog/printer → Snapshot → Probe manager → Wrappers → Live `extract` → Document print**.

## Critical Pitfalls

### Pitfall 1: Treating parse and align as one stage (live `Extraction` mutation)

**What goes wrong:**
The parse section shows `char_interval` and `alignment_status` already filled. Developers cannot tell whether grounding happened in `Resolver.resolve` or `Resolver.align`. A later “fix alignment” change looks like a parse bug.

**Why it happens:**
`Resolver.resolve` returns new `Extraction` objects with grounding unset. `WordAligner.align_extractions` (via `Resolver.align`) assigns `char_interval`, `token_interval`, and `alignment_status` **on those same objects**. `Annotator` keeps that list. Storing the list reference and printing it after `extract` returns shows post-align state under the parse label.

**How to avoid:**
Snapshot field copies at the resolve return boundary (class, text, attributes, index, and explicit `char_interval is None` / `alignment_status is None`). Return the original sequence to the annotator. Snapshot again on each align yield. Never deep-copy objects into align — that desyncs the document from the parse.

**Warning signs:**
- Parse and align sections print identical grounding fields.
- Print-after-return of “parse” objects matches the `AnnotatedDocument` extractions bit-for-bit on spans.

**Phase to address:**
Snapshot (phase 2), before Wrappers that touch resolve/align (phase 4).

---

### Pitfall 2: Rebuilding the pipeline beside `lx.extract`

**What goes wrong:**
The script constructs `FormatHandler` / `Resolver` / `Annotator` (or re-chunks and re-prompts) and either skips `extract` or runs a second unrelated path. Printed stages do not match the call that produced the document. Format defaults diverge: `Annotator.__init__` defaults YAML and `fence_output=False` when no handler is passed; `extract` defaults JSON and derives fences from the schema.

**Why it happens:**
Intermediates (prompt string, chunks, raw model text) are locals inside `extract` / `Annotator`. Reassembling the stack feels easier than observing the live call.

**How to avoid:**
One `lx.extract(...)` only. Observe the five methods that call already uses (`ChunkIterator.__iter__`, `ContextAwarePromptBuilder.build_prompt`, `OllamaLanguageModel.infer`, `Resolver.resolve`, `Resolver.align`). Pass `resolver_params={"format_handler": OLLAMA_FORMAT_HANDLER}` so the same handler reaches both sides — do not hand-build a parallel annotator.

**Warning signs:**
- Two HTTP hits to Ollama for “one” walkthrough.
- Parse failures that disappear when the same text goes through bare `extract`.
- YAML fences or fence flags that disagree with the Ollama README path.

**Phase to address:**
Catalog/printer (phase 1) locks the “one call” contract; Live `extract` (phase 5) must not add a second pipeline.

---

### Pitfall 3: Passing `model=` to “instrument” inference

**What goes wrong:**
The script builds `OllamaLanguageModel`, wraps the instance, and passes `model=`. Schema constraints from examples are skipped; `use_schema_constraints` is ignored. The trace is a different call than `model_id="gemma3:4b"` through `factory.create_model`.

**Why it happens:**
Instance wrapping looks cleaner than a class-attribute probe. `extract` documents `model=` as a supported alternate entry.

**How to avoid:**
Let `extract` call `factory.create_model`. Wrap `OllamaLanguageModel.infer` on the **class** so whichever instance `extract` builds is recorded. Keep `model_id="gemma3:4b"` and `model_url`.

**Warning signs:**
- Warning that a pre-built model was passed / schema constraints skipped.
- Request body missing `format: "json"` that `FormatModeSchema` normally enables.

**Phase to address:**
Live `extract` arguments (phase 5); Probe manager must target the class (phase 3).

---

### Pitfall 4: Wrapping `WordAligner` as the alignment stage

**What goes wrong:**
Example prompt-validation alignment is printed as source grounding. Or grounding appears twice — once before the model exists, once after parse.

**Why it happens:**
`prompt_validation.validate_prompt_alignment` runs a separate `WordAligner` over few-shot examples before the model is created. `Resolver.align` is the grounding stage for chunk extractions.

**How to avoid:**
Wrap `Resolver.align` only. Leave `WordAligner.align_extractions` alone. Optionally note prompt-validation failure later (FEATURES P2); never label it `align`.

**Warning signs:**
- An “align” record appears before any model stage.
- Align input is example text, not `chunk_text`.

**Phase to address:**
Wrappers (phase 4) probe target list.

---

### Pitfall 5: Calling `build_prompt` twice inside the probe

**What goes wrong:**
The next chunk’s prompt gains a wrong previous-chunk suffix (or the same call’s printed prompt is not what `infer` received). Cross-chunk context drifts.

**Why it happens:**
`ContextAwarePromptBuilder.build_prompt` updates `_prev_chunk_by_doc_id` after each render. A probe that re-invokes the builder “to capture the string” mutates that state. `Annotator` also deletes `prompts` after `infer`, so you cannot read them back later.

**How to avoid:**
Call the original `build_prompt` exactly once. Record the returned string. That same string must appear as `infer`’s `batch_prompts` entry for the chunk.

**Warning signs:**
- Prompt-stage text ≠ model-stage `batch_prompts[i]`.
- Multi-chunk runs show duplicated or missing previous-chunk prefixes.

**Phase to address:**
Wrappers — prompting probe (phase 4).

---

### Pitfall 6: Consuming or replacing generator results from `infer` / `align`

**What goes wrong:**
Empty scored-output lists are swallowed (hiding `InferenceOutputError`), or align yields different objects than the ones the aligner mutated, so the document misses spans the align stage printed.

**Why it happens:**
`OllamaLanguageModel.infer` and `Resolver.align` are generators. Probes naturally want `list(original(...))`. Rebuilding `ScoredOutput` or new `Extraction`s looks harmless.

**How to avoid:**
Generator-transparent wrappers: snapshot copies on the side, yield the **same** items. Forward `**kwargs` on `infer`. Forward token/char offsets and alignment kwargs on `align`. Let exceptions propagate after `finally` restores probes.

**Warning signs:**
- Align printout has spans; `AnnotatedDocument.extractions` has `char_interval is None`.
- `InferenceOutputError` never appears when Ollama returns an empty batch item.

**Phase to address:**
Wrappers for model and align (phase 4); Probe manager restore-on-exception (phase 3).

---

### Pitfall 7: Leaking class monkeypatches (bound-method restore / missing `finally`)

**What goes wrong:**
After the script exits (or after a failed Ollama call), `ChunkIterator.__iter__`, `Resolver.resolve`, or `OllamaLanguageModel.infer` stay wrapped for the rest of the process. Later imports in the same interpreter see tracing side effects. Or restore “succeeds” but leaves a bound method that breaks later calls (`self` passed twice / wrong descriptor).

**Why it happens:**
Saving `instance.method` or a descriptor-bound object from naive `getattr` on the class, then writing that back, is a known Python monkeypatch failure mode (wrapt docs; pytest `MonkeyPatch` restores `__dict__` entries for the same reason). Exception paths that skip restore leave process-global patches.

**How to avoid:**
Save each target from the class attribute used for assignment (`ChunkIterator.__iter__ = ...`), wrap for one `extract`, restore in `finally` on success and failure. Prefer a small context manager. Do not leave patches installed while debugging an exception without restoring.

**Warning signs:**
- Second `extract` in the same REPL still prints stages.
- `TypeError` about unexpected `self` after the script “finished”.

**Phase to address:**
Probe manager (phase 3) — must land before any live call.

---

### Pitfall 8: Reading `[]` from parse as “model found nothing”

**What goes wrong:**
The walkthrough shows an empty parse list and an empty document. The developer debugs alignment or the prompt, but the failure was a format/schema parse error swallowed by default.

**Why it happens:**
`extract` forces `suppress_parse_errors=True` unless `resolver_params` overrides it. `Resolver.resolve` logs and returns `[]` on `FormatError` / extraction `ValueError`. Small local models (`gemma3:4b`) often emit almost-JSON that fails the wrapper key or fence rules.

**How to avoid:**
Always print the raw model string above parse. When resolve returns `[]`, print an explicit line that the chunk was omitted on a parse/schema error (not “no entities”). Print `format_type`, `use_fences`, and wrapper key as parse inputs. For diagnosis runs only, `resolver_params={"suppress_parse_errors": False}` (and still keep `OLLAMA_FORMAT_HANDLER`).

**Warning signs:**
- Model stage shows non-empty JSON-ish text; parse is `[]`; document has zero extractions.
- absl warnings about parse errors that the stage dump never mentions.

**Phase to address:**
Catalog/printer empty-parse copy (phase 1); Wrappers — resolve (phase 4).

---

### Pitfall 9: Wrong Ollama call shape for `gemma3:4b` (`OLLAMA_BASE_URL`, `num_ctx`, timeout, `think`, fences)

**What goes wrong:**
Connection to the wrong host; silent context truncation; cold-load timeout mistaken for a pipeline hang; empty `response` with a thinking trace raised as `InferenceRuntimeError`; or fence/schema flags that fight `FormatModeSchema`.

**Why it happens:**
- `factory._kwargs_with_environment_defaults` applies `OLLAMA_BASE_URL` only when `"ollama"` appears in `model_id`. `gemma3:4b` does not contain that substring. `demo_ollama.py` reads `OLLAMA_HOST`, which the factory ignores.
- Provider default `options.num_ctx` is **2048** even though the model card advertises 128k. Oversized prompts truncate under that pin.
- Default HTTP timeout is **120s**; cold-loading ~3.4GB `gemma3:4b` can exceed it.
- Provider defaults `think=False`. `think=True` (or model thinking with empty `response`) raises in `ollama.py`.
- `output_schema=` and `fence_output=True` are wrong for this provider path; Ollama expects `format: "json"` and fences off (`OLLAMA_FORMAT_HANDLER`).

**How to avoid:**
Pass `model_url` explicitly. Keep samples inside the default 2048-token budget (or pass `language_model_params={"num_ctx": ...}` for that call only — do not change library `_DEFAULT_NUM_CTX` in this milestone). Raise timeout on cold start (`language_model_params={"timeout": 300}`). Leave `think` at default false. Leave fence/schema flags unset; pass `OLLAMA_FORMAT_HANDLER`. Preflight `GET /api/tags` for `gemma3:4b` before `extract`.

**Warning signs:**
- Script talks to localhost while Ollama runs elsewhere (env vars “set” but ignored).
- Prompt looks complete in the printer but model output is truncated / incoherent mid-JSON.
- Failures near 120s on first request after `ollama stop`.
- Error text mentioning empty response with a thinking trace.

**Phase to address:**
Live `extract` (phase 5); Catalog header + preflight (phase 1).

---

### Pitfall 10: Using `debug=True` or `demo_ollama.py` as the walkthrough

**What goes wrong:**
Logs truncate strings at 500 characters and sequences at 20 items; debug logging stays process-wide; owning function/file/data-in/out contract is missing. Or the script drifts into JSONL/HTML/`gemma2:2b` result demo behavior.

**Why it happens:**
`debug=True` and `examples/ollama/demo_ollama.py` already exist and look adjacent. `debug_log_calls` only wraps tokenizer methods.

**How to avoid:**
`debug=False`, `show_progress=False`. Stdlib `inspect` + `pprint` around the five probes. Copy only the availability check pattern from the demo, not its model default, multi-example loop, or HTML path.

**Warning signs:**
- Stage dump cuts mid-prompt at ~500 chars.
- Output directory / HTML files appear from the “trace” script.
- Default model string is `gemma2:2b`.

**Phase to address:**
Catalog/printer (phase 1); Live `extract` flags (phase 5).

---

### Pitfall 11: Multi-pass or multi-chunk volume that breaks the one-pass story

**What goes wrong:**
Printed probe records no longer match the single `AnnotatedDocument` story. With `extraction_passes > 1`, the return value is a first-pass-wins merge; only pass 0 records debug alignment today. Long text multiplies chunk→prompt→infer→resolve→align cycles and hides the stage contract.

**Why it happens:**
Raising passes “for recall” or using a long article “to show offsets” seems helpful.

**How to avoid:**
`extraction_passes=1`. Keep source under default `max_char_buffer` (1000) for v1 so one chunk runs. Still print `token_offset` / `char_offset` (even when 0) and chunk intervals. Add a second chunk only when a named chunking/offset change needs it (FEATURES P2).

**Warning signs:**
- More model-stage records than documents returned.
- Document extractions that do not appear in any single pass’s align records.

**Phase to address:**
Live `extract` sample and args (phase 5); Document print expectations (phase 6).

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Class monkeypatch probes in the script | Sees live locals without library hooks | Coupled to five method names; leaks if restore fails | This milestone only — never as a library feature |
| Printing full prompts for one short call | Matches “data in/out” goal | Unusable noise if sample grows | Short single-chunk sample only |
| Relying on `suppress_parse_errors=True` in the demo script | Call “completes” with a document | Empty docs look successful | Acceptable if empty-parse is called out in words |
| Reusing `demo_ollama.py` helpers wholesale | Faster first run | Wrong model, HTML/JSONL, `OLLAMA_HOST` semantics | Availability check only |
| Raising `num_ctx` globally in the library | Fits longer prompts | Changes every Ollama caller’s memory profile | Never in this milestone — per-call `language_model_params` only |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Local Ollama host | Rely on `OLLAMA_BASE_URL` / `OLLAMA_HOST` with `model_id="gemma3:4b"` | Pass `model_url=` on `lx.extract` |
| Model availability | Call `extract` then interpret empty extractions as a pipeline miss | `GET /api/tags` (or demo’s check) for `gemma3:4b` first |
| Generate API | Second client (`ollama` PyPI) or `/api/chat` “to show the request” | Observe `OllamaLanguageModel.infer` → `/api/generate` via `requests` |
| Format handler | Hand-rolled JSON fences / YAML | `OLLAMA_FORMAT_HANDLER` through `resolver_params` |
| Schema | `output_schema=` for structured output | Unsupported on this provider; few-shot examples + `FormatModeSchema` JSON mode |
| Thinking models | Flip `think=True` to “see reasoning” in the trace | Keep default `think=False`; empty `response` becomes `InferenceRuntimeError` |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Expecting `max_workers` to speed Ollama | Trace still ~N× single latency | Leave workers alone; Ollama `infer` is sequential | Any multi-prompt batch on Ollama |
| Default `num_ctx=2048` with a long few-shot prompt | Truncated / broken JSON; parse `[]` | Short examples + short source; or per-call `num_ctx` | Prompt tokens > 2048 under provider default |
| Cold-load inside 120s timeout | Hang then timeout error | Pre-pull/load model; raise `timeout` on first call | First request after unload of 3.4GB model |
| Fuzzy alignment on huge chunks | Align stage dominates wall time | Keep `max_char_buffer` near 1000 for the script | Callers who raise buffer for “one big chunk” |
| Printing every chunk of a long doc | Terminal flood; hard to review owners | One-chunk v1 sample | Multi-chunk without truncation policy in the printer |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Enabling `debug=True` and pasting logs | Process-wide logging; secrets in kwargs/prompts only partially redacted | Keep `debug=False`; redact `api_key`-like keys if any kwargs are printed |
| Forwarding `LANGEXTRACT_API_KEY` into Ollama `base_url` | Key posted to whatever host `model_url` names | No API key for local Ollama; treat `model_url` as a trust boundary |
| `fetch_urls=True` in the trace script | SSRF-style fetch of caller-controlled URLs | Literal string input; leave `fetch_urls` off |
| Committing trace stdout with proprietary source text | Accidental disclosure of document contents | Local-only sample text for the milestone script |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Stage labels without function + file | Cannot name the file a later change must touch | Header line: label, callable, repo-relative path |
| Omitting raw model text | Parse `[]` is unexplainable | Model stage prints `ScoredOutput.output` fully for this short call |
| Align without source slice | Fuzzy/miss spans look fine until someone greps offsets | Print `document_text[start:end]` or `ungrounded` |
| Progress bars / HTML as the “trace” | Payloads replaced by tqdm or a finished highlight | Sectioned stdout only |
| Silent success when Ollama is down | Empty walkthrough blamed on resolve/align | Fail loud at preflight |

## "Looks Done But Isn't" Checklist

- [ ] **One call:** Exactly one `lx.extract`; one Ollama generate for a one-chunk sample — verify no second client or rebuilt annotator.
- [ ] **Parse vs align:** Parse snapshot has null grounding; align snapshot has spans/status — verify before/after pair on the same extraction_text.
- [ ] **Prompt fidelity:** Printed prompt string equals `infer`’s `batch_prompts` entry — verify no double `build_prompt`.
- [ ] **Probe restore:** After success and after forced exception, class attributes equal the saved originals — verify in the same process.
- [ ] **Ollama host:** `model_url` set; not relying on `OLLAMA_BASE_URL` for `gemma3:4b` — verify against a non-default port once.
- [ ] **Empty parse callout:** Forced bad model JSON (or `suppress_parse_errors` left on with bad output) prints the omission sentence — verify `[]` is not labeled “no entities”.
- [ ] **Preflight:** Missing `gemma3:4b` stops before stage sections that look like a successful empty extract.
- [ ] **Flags:** `extraction_passes=1`, `debug=False`, `show_progress=False`, `fetch_urls=False`, no `output_schema`, no `model=`.
- [ ] **WordAligner:** No align-stage records before the model stage from prompt validation.
- [ ] **Document match:** Final `AnnotatedDocument.extractions` match the last align snapshots for that call (same objects’ field values).

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Leaked class patches | LOW | Restore saved callables; restart interpreter if identity unknown |
| Parse/align records collapsed | MEDIUM | Add snapshot at resolve return; re-run one call; do not trust prior stdout |
| Second pipeline / `model=` path | MEDIUM | Delete parallel wiring; switch to `model_id` + class probes; compare one new run |
| Wrong host / missing model | LOW | Fix `model_url`; `ollama pull gemma3:4b`; preflight; re-run |
| Timeout on cold load | LOW | Warm model once; pass higher `timeout`; re-run |
| `think` / empty response errors | LOW | Remove `think=True`; keep provider defaults; re-run |
| Multi-pass confusion | LOW | Set `extraction_passes=1`; discard merged-document interpretation of probe logs |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|--------|------------------|--------------|
| Live `Extraction` mutation collapses parse/align | Phase 2 Snapshot | Parse record shows null grounding; align shows spans |
| Parallel pipeline / Annotator YAML defaults | Phase 1 + Phase 5 | Single `extract`; no second HTTP generate |
| `model=` skips factory schema path | Phase 3 + Phase 5 | Class wrap on `OllamaLanguageModel.infer`; no `model=` kwarg |
| `WordAligner` mistaken for grounding | Phase 4 Wrappers | No align section before model; probe list excludes `WordAligner` |
| Double `build_prompt` mutates context | Phase 4 Wrappers | Prompt text == `batch_prompts` entry |
| Generator consume/replace | Phase 4 Wrappers | Document spans match align snapshots; errors still raise |
| Monkeypatch leak / bound restore | Phase 3 Probe manager | `finally` restore test after success and failure |
| `[]` misread as miss | Phase 1 + Phase 4 | Empty-parse sentence + raw model text present |
| Ollama host / `num_ctx` / timeout / think / fences | Phase 1 + Phase 5 | Preflight; explicit `model_url`; defaults documented in header |
| `debug=True` / demo drift | Phase 1 + Phase 5 | Full payloads; `gemma3:4b`; no HTML/JSONL side effects |
| Multi-pass / multi-chunk story break | Phase 5 + Phase 6 | One chunk, one pass; document matches probe set |

## Sources

- Local pipeline and concerns (HIGH): `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONCERNS.md`, `.planning/PROJECT.md`; `langextract/extraction.py` (`suppress_parse_errors` default), `langextract/annotation.py` (`zip(batch, outputs)`, `del prompts`, resolve→align), `langextract/resolver.py` (align mutates `Extraction`s), `langextract/providers/ollama.py` (`OLLAMA_FORMAT_HANDLER`, `think`, `num_ctx=2048`, timeout 120, empty+thinking error), `langextract/factory.py` (`OLLAMA_BASE_URL` only if `"ollama" in model_id`), `examples/ollama/demo_ollama.py` (`OLLAMA_HOST`, `gemma2:2b`, availability check). Cross-checked with `.planning/research/STACK.md` and `.planning/research/ARCHITECTURE.md` (2026-10-09).
- Ollama generate API (HIGH for field names via docs fetch; MEDIUM for operational bugs): https://docs.ollama.com/api/generate — `format`, `stream`, `think`, `response`/`thinking`, `options.num_ctx`. Community reports of empty `format:json` output and thinking/format interactions on newer Gemma lines — treat as operational risk, not a reason to change this repo’s `think=False` default without a local repro on `gemma3:4b`.
- Monkeypatch restore discipline (MEDIUM): https://wrapt.readthedocs.io/en/master/monkey.html (descriptor/`getattr` restore failure); pytest `MonkeyPatch` undo semantics.
- Prior feature anti-patterns (MEDIUM/HIGH local): `.planning/research/FEATURES.md` — second infer, reusable tracer, `debug=True`, demo replacement.

**Gaps:** No maintainer interview. No timed cold-load measurement on this machine (300s timeout remains MEDIUM, from example README practice). `think=false` vs structured-format bugs were reported against **gemma4** / other thinking models — not verified against local `gemma3:4b`; keep provider defaults and watch parse `[]` + raw text if format looks ignored.

---
*Pitfalls research for: stage-trace of source-grounded LangExtract extract() via local Ollama gemma3:4b*
*Researched: 2026-10-10*

# Phase 4: Stage wrappers - Research

**Researched:** 2026-10-10
**Domain:** Call-scoped class-attribute wrappers (generators/iterators) over the LangExtract `extract()` pipeline, plus stage-record printing — all inside `scripts/trace_extract.py`
**Confidence:** HIGH (every signature, call site and wrapper shape below was read in the local tree and exercised offline this session)

## User Constraints

No phase `04-CONTEXT.md` exists (user continued without discuss-phase). Constraints below come from the invocation, REQUIREMENTS/ROADMAP, root `CLAUDE.md`, and the Phase 1 decisions that still bind this phase. Phase 3 is only partially discussed (`03-DISCUSS-CHECKPOINT.json`), so its decisions are listed as *partial*.

### Locked Decisions
- **Observation-only, script-only (CTR-01/CTR-02):** no `langextract/` library API changes; `examples/ollama/demo_ollama.py` untouched. [CITED: REQUIREMENTS.md CTR-01, CTR-02]
- **Diff budget (hard):** ≤ ~150 changed non-test lines and ≤ 3 source files per task/commit; ≤ ~400 non-test lines per plan; tests excluded but in the same commit; no unrelated refactors/reformatting. [CITED: /CLAUDE.md, .claude/skills/diff-budget/SKILL.md]
- **Phase 1 D-10:** every constant (incl. messages/labels) lives in repo-root `config.yaml`, not Python literals. D-13: the empty-parse sentence lives in config. D-14/D-15: `redact_keys` in config + `redact()` helper for printed payloads. D-05: stage header form stays `[label] function — path`. [CITED: 01-CONTEXT.md]
- **Phase 2 decisions:** snapshots are duck-typed field copies (`ExtractionSnapshot`), parse record copied at `resolve` return; `print_grounding_pair(parse, align, ungrounded_label)` is the before/after printer; helpers were deliberately *not* wired into `main()` until Phase 4. [CITED: 02-01-SUMMARY.md, 02-02-SUMMARY.md, STATE.md]
- **Phase 3 (partial, from `03-DISCUSS-CHECKPOINT.json`):** entry is a context manager `trace_probes()`; optional `wrappers={...}` argument; when omitted every one of the five targets gets an **identity passthrough**; wrap bodies are pure identity by default; generators are **transparent yields (never `list()`)**. Areas still undecided: "Phase-3 wrap bodies" (in progress), "Prove restore", "Install failure / re-entry". [CITED: 03-DISCUSS-CHECKPOINT.json]
- **Mode `mvp`, goal:** live data in/out for chunk → align, raw model text separate from parsed extractions, empty-parse callout in words, format/fence/wrapper flags on parse inputs — **without requiring a warm model**. [CITED: ROADMAP.md Phase 4]

### Claude's Discretion
- Record shape/names, printer layout, how wrappers are handed to `trace_probes(wrappers=...)` (see Open Questions — depends on Phase 3), how to disambiguate an empty parse, how to split the work into plans.

### Deferred Ideas (OUT OF SCOPE)
- Real `lx.extract()` call, Ollama preflight, prompt/examples in config (Phase 5); printing the returned `AnnotatedDocument` (Phase 6, STG-07); the `prompt-template` stage's live data (its content arrives with the config prompt in Phase 5 — D-11); two-chunk input (STG-10), prompt-validation line (STG-11), `WordAligner` parameter echo (STG-12).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STG-03 | Each stage prints live data in and data out for that call (full payloads) | Per-stage `StageRecord` captured by the five wrappers; exact in/out fields per stage in *Data captured per wrapper*; offline proof via real `lx.extract` with `_ollama_query` patched (Pattern 6) |
| STG-04 | Model stage shows raw model text separate from parsed extractions | `infer` wrapper records `ScoredOutput.output` verbatim; parse stage owns the parsed list; printer never prints extractions under `[model]` |
| STG-06 | Align stage shows spans, status, chunk offsets (even when 0), source slice or `ungrounded` | Offsets come from the bound args of `Resolver.align` (`token_offset`, `char_offset`); spans/status from an align-time snapshot; slice = `source_text[start-char_offset:end-char_offset]` (verified); `ungrounded_label` already in config |
| STG-09 | Empty parse called out in words next to raw model text; parse inputs include format/fence/wrapper flags | Parse record's `in` holds raw text + `FormatHandler` flags read from `self.format_handler`; callout via config `empty_parse_message`, disambiguated by re-running the *original* `resolve` with `suppress_parse_errors=False` (Pattern 5) |
</phase_requirements>

## Summary

All five wrap targets live in their classes' own `__dict__` and are called by `Annotator._annotate_documents_single_pass` with a call shape that matters: `infer(batch_prompts=prompts, **kwargs)` is called with **`batch_prompts` as a keyword only** and extra `max_workers`; `resolve(raw, debug=..., suppress_parse_errors=..., **kwargs)` and `align(extractions, chunk_text, token_offset, char_offset, tokenizer_inst=..., **kwargs)` also receive `max_workers`. Wrappers must therefore be `(self, *args, **kwargs)` pass-throughs that use `inspect.signature(original).bind(...)` only to *read* arguments. `infer` and `align` are generator functions and must stay lazily consumed by the Annotator; `ChunkIterator.__iter__` is **not** a generator — it returns `self` and the work is in `__next__`.

**One finding contradicts earlier research:** the generator example in `.planning/research/ARCHITECTURE.md` Pattern 1 (`for chunk in original(self): … yield chunk`) raises `RecursionError` against this class, because `original(self)` returns the `ChunkIterator` itself and the `for` statement calls `iter()` on it, which re-enters the patched `__iter__`. The wrapper has to drive the instance with `next(it)` instead (verified working end-to-end below).

Everything needed for STG-03/04/06/09 can be proven offline by running the **real** `lx.extract(model_id="gemma3:4b", …)` with only `OllamaLanguageModel._ollama_query` patched in the test — no network, the real factory/annotator/resolver/aligner, all five wrappers fire once, exactly one (fake) HTTP call. Estimated non-test size of the whole phase is ~250 lines in `scripts/trace_extract.py` + ~5 lines in `config.yaml`, so it must be **three plans** (not one).

**Primary recommendation:** Build `StageRecord` + five `make_*_wrapper(sink)` factories (each `original -> replacement`, `(self, *args, **kwargs)`, generator-transparent, bound-arg reads only), snapshot at `resolve` return and at `align` exhaustion, collect-then-print, and prove it with one offline real-`extract` test plus per-wrapper unit tests; split into chunk/prompt/model → parse/align → printers.

## Architectural Responsibility Map

(There are no web tiers here; "tiers" are the layers inside the one script, plus the library boundary.)

| Capability | Primary Layer | Secondary Layer | Rationale |
|------------|---------------|-----------------|-----------|
| Reading live values at stage boundaries | Wrapper functions in `scripts/trace_extract.py` | — | Values exist only as locals inside `Annotator`; only class-method wrappers see them |
| Keeping parse ungrounded / align grounded | Snapshot helpers (Phase 2, existing) | Wrappers call them at the right moment | Align mutates resolve's objects in place (verified) |
| Install / restore of the five targets | Phase 3 `trace_probes()` | Phase 4 supplies the wrapper callables | Restore discipline is Phase 3's hard gate; Phase 4 must not install anything itself |
| Stage records (copies, no live objects) | Script `StageRecord` list owned by the caller | — | No global state; no persisted store (out of scope) |
| Presentation (in/out blocks, callout, slice) | Printer functions in the script | `config.yaml` for all strings | D-10: constants/messages in config |
| Model call / parse / align execution | Library, unchanged | — | Observation only |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.12 (`.venv/bin/python`) | Script runtime | [VERIFIED: `.venv/bin/python --version` this session] Bare `python` (Homebrew 3.14) lacks PyYAML — pre-existing, use `.venv/bin/python` |
| langextract (editable) | local tree | The five wrap targets, `Resolver`, `OLLAMA_FORMAT_HANDLER` | [VERIFIED: `.venv/bin/python -c "import langextract"` → local `langextract/__init__.py`] |
| stdlib `inspect`, `dataclasses`, `textwrap`, `pprint`, `unittest.mock` | stdlib | Signature binding, records, block printing, test patching | No new dependencies (see audit below) |
| PyYAML | already in `.venv` | `config.yaml` loading (existing `load_config`) | Already used by Phase 1/2 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.1 | Test runner | [VERIFIED: `.venv/bin/python -m pytest --version`] Existing tests are `absltest` classes; pytest runs them (`tests/trace_extract_test.py` → 11 passed this session) |
| absl-py (`absltest`) | existing | Test style used by `tests/trace_extract_test.py` | Keep the file's current style |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Stdlib class-attribute wrappers | `wrapt` | Rejected in project research (no new deps) |
| Real `lx.extract` + patched `_ollama_query` in tests | Fake `BaseLanguageModel` / `model=` | `model=` changes the call path (skips factory); the target is `OllamaLanguageModel.infer` so a fake model would not exercise the wrapper |

**Installation:** none — no packages are added.

## Package Legitimacy Audit

No external packages are installed or added by this phase (stdlib + packages already in `.venv`). Audit not applicable. **Packages removed due to [SLOP]:** none. **Flagged [SUS]:** none.

## Architecture Patterns

### Data flow (what each wrapper sees; arrows = the order `Annotator` calls them)

```
lx.extract(...)  [Phase 5 will call it; Phase 4 tests call it with _ollama_query patched]
   │ prompt validation (WordAligner on few-shot examples)   ← NOT wrapped, no Resolver.align here
   ▼
Annotator._annotate_documents_single_pass
   │ iter(ChunkIterator)  ──► [chunk wrapper]  in: max_char_buffer, doc text │ out per chunk: chunk_text, char/token interval, document_id
   │ build_prompt(chunk_text, document_id, additional_context) ─► [prompt wrapper]  in: those 3 + context_window_chars │ out: prompt str
   │ infer(batch_prompts=[...], max_workers=..)  ─► [model wrapper]  in: batch_prompts │ out (per yield): [(score, raw text)]
   │ resolve(raw, debug=, suppress_parse_errors=, max_workers=) ─► [parse wrapper]  in: raw + format flags │ out: snapshot_extractions(result) taken BEFORE return
   │ align(extractions, chunk_text, token_offset, char_offset, tokenizer_inst=, max_workers=) ─► [align wrapper] in: chunk_text, offsets, n │ out: snapshot at generator exhaustion (+ slices)
   ▼
StageRecords in caller-owned list  ──►  (after call, in finally)  print_stage_records(...)
```

### Recommended structure (all in the existing files)
```
scripts/trace_extract.py   # + StageRecord, make_*_wrapper factories, printers (≈250 lines over 3 plans)
config.yaml                # + empty_list_message (valid empty list), small display labels if needed
tests/trace_extract_test.py# + wrapper tests; one offline real-extract test
```
No new files in `langextract/`, none in `examples/`.

### Wrap targets — exact signatures and call shapes [VERIFIED by reading source this session]

| Stage | Target (all in the class's own `__dict__`) | Signature as defined | How `Annotator` calls it | Behaviour that constrains the wrapper |
|-------|-----------------------------------------------|----------------------|--------------------------|----------------------------------------|
| chunk | `ChunkIterator.__iter__` (`langextract/chunking.py:422-423`) | `def __iter__(self) -> Iterator[TextChunk]:` / `    return self` | `yield from chunk_iter` in `_document_chunk_iterator` (`annotation.py:160`), constructed at `annotation.py:152` | **Not a generator.** Returns `self`; chunks come from `__next__` (`chunking.py:441`). Naive `for c in original(self)` recurses (see Pitfall 1) |
| prompt | `ContextAwarePromptBuilder.build_prompt` (`prompting.py:215-220`) | `def build_prompt(self, chunk_text: str, document_id: str, additional_context: str \| None = None) -> str:` | `prompt_builder.build_prompt(chunk.chunk_text, chunk.document_id, chunk.additional_context)` (`annotation.py:371-373`), positional | Calls `self._update_state(document_id, chunk_text)` after render (`prompting.py:~240`) → call original **exactly once** |
| model | `OllamaLanguageModel.infer` (`providers/ollama.py:266-268`) | `def infer(self, batch_prompts: Sequence[str], **kwargs) -> Iterator[Sequence[core_types.ScoredOutput]]:` | `self._language_model.infer(batch_prompts=prompts, **kwargs)` (`annotation.py:392`) — **keyword**, plus `max_workers` | Generator; `yield [core_types.ScoredOutput(score=1.0, output=output)]` (`ollama.py:310`); Annotator then `list()`s it and `del prompts` (`annotation.py:~394-396`) |
| parse | `Resolver.resolve` (`resolver.py:276-281`) | `def resolve(self, input_text: str, suppress_parse_errors: bool = False, **kwargs) -> Sequence[data.Extraction]:` | `resolver.resolve(scored_outputs[0].output, debug=debug, suppress_parse_errors=suppress_parse_errors, **kwargs)` (`annotation.py:406-410`) | Returns `[]` on `FormatError`/`ValueError` when suppressed (`resolver.py:310-330`); returns *new* `Extraction`s each call |
| align | `Resolver.align` (`resolver.py:337-352`) | `def align(self, extractions, source_text, token_offset, char_offset=None, enable_fuzzy_alignment=True, …, tokenizer_inst=None, *, fuzzy_alignment_algorithm=…, …, **kwargs) -> Iterator[data.Extraction]:` | `resolver.align(resolved_extractions, text_chunk.chunk_text, token_offset, char_offset, tokenizer_inst=tokenizer, **kwargs)` (`annotation.py:424-431`) — 4 positional + `tokenizer_inst` + `max_workers` | Generator; bare `return` (yields nothing) when `extractions` is empty (`resolver.py:377-384`); aligner runs fully on first `next()`, then `yield`s each object (`resolver.py:~407`) |

Verbatim evidence for the key facts:
- chunking.py:422-423 — `def __iter__(self) -> Iterator[TextChunk]:` / `    return self`
- annotation.py:392 — `outputs = self._language_model.infer(batch_prompts=prompts, **kwargs)`
- extraction.py:372 — `alignment_kwargs.setdefault("suppress_parse_errors", True)`
- extraction.py:57 / :53 — `batch_length: int = 10,` / `max_char_buffer: int = 1000,`
- resolver.py:~992-993 — `start_pos=char_offset + start_token.char_interval.start_pos,` / `end_pos=char_offset + end_token.char_interval.end_pos,` (spans are **document** coordinates)

**Runtime kwargs seen by the wrappers in the offline run** [VERIFIED: /tmp/exp_wrap.py output]:
- `build_prompt`: positional `('<chunk text>', 'doc_aff38874', None)`, no kwargs.
- `infer`: positional `()`; kwargs `{'batch_prompts': [...], 'max_workers': 10}`.
- `resolve`: positional `('<raw text>',)`; kwargs `{'debug': False, 'suppress_parse_errors': True, 'max_workers': 10}`.
- `align`: kwargs names `['tokenizer_inst', 'max_workers']`; bound `source_text`/`token_offset`/`char_offset` = chunk text / `0` / `0`.

### Pattern 1: Wrapper factory = `original -> replacement` (decorator shape, identity-compatible)
**What:** `make_X_wrapper(sink)` returns `lambda original: replacement`. A default of `lambda original: original` is exactly Phase 3's "identity passthrough". Replacement signature is always `(self, *args, **kwargs)`.
**When:** all five targets. **Why:** forwards whatever `extract` passes today and tomorrow (`max_workers`, `tokenizer_inst`, future kwargs).
**Reading args without changing the call:**
```python
# Source: stdlib inspect; shape verified against the real call sites this session
bound = inspect.signature(original).bind(self, *args, **kwargs)
bound.apply_defaults()          # defaults give char_offset=None etc. when absent
source_text = bound.arguments['source_text']
```
Always forward the **original** `*args, **kwargs` to the original — never the bound copy.

### Pattern 2: Chunk wrapper (iterator, NOT generator-over-original)
```python
# VERIFIED end-to-end offline (/tmp/exp_wrap.py "canned" mode)
def make_chunk_wrapper(sink):
  def wrap(original):
    def traced_iter(self):
      it = original(self)                  # returns self for ChunkIterator
      while True:
        try:
          chunk = next(it)                 # next(), never `for ... in it` / `yield from it`
        except StopIteration:
          return                           # PEP 479: do not let StopIteration escape a generator
        sink.append(StageRecord('chunk', {...}, {...}))   # primitives only
        yield chunk                        # same object back to the caller
    return traced_iter
  return wrap
```
Chunk `out` fields to copy to primitives: `chunk.chunk_text`, `(char_interval.start_pos, .end_pos)`, `(token_interval.start_index, .end_index)`, `chunk.document_id`. Reading `chunk_text`/`char_interval` is safe — both are cached properties the Annotator reads anyway (`chunking.py:100-140`; Annotator reads them at `annotation.py:372, 417-420`). `in`: `self.max_char_buffer`, source text `self.tokenized_text.text`.

### Pattern 3: Model wrapper (outer function records `in`, returns a transparent generator)
```python
# VERIFIED: infer-in recorded at call time, infer-out per yield, 1 HTTP call, document unchanged
def traced_infer(self, *args, **kwargs):
  bound = inspect.signature(original).bind(self, *args, **kwargs)
  prompts = tuple(bound.arguments['batch_prompts'])
  in_data = {'batch_prompts': prompts, 'kwargs': redact(extra_kwargs, keys)}
  def gen():
    for item in original(self, *args, **kwargs):     # lazy, same items out
      sink.append(StageRecord('model', in_data, {'outputs': tuple((s.score, s.output) for s in item)}))
      yield item                                      # SAME list object
  return gen()
```
Do not catch `InferenceRuntimeError`/`InferenceOutputError`; Ollama failures must still propagate (and Phase 3's `finally` restores). Do **not** wrap `BaseLanguageModel.infer`, do not pass `model=`.

### Pattern 4: Parse wrapper — snapshot at return, flags from the handler, never mutate
```python
def traced_resolve(self, *args, **kwargs):
  out = original(self, *args, **kwargs)
  raw = args[0] if args else kwargs['input_text']
  fh = getattr(self, 'format_handler', None)
  flags = {name: getattr(fh, name, None) for name in
           ('format_type', 'use_fences', 'strict_fences', 'use_wrapper', 'wrapper_key')}
  sink.append(StageRecord('parse', {'raw_model_text': raw, 'flags': flags,
                                     'suppress_parse_errors': kwargs.get('suppress_parse_errors')},
                          {'extractions': snapshot_extractions(out), ...}))   # BEFORE returning
  return out                                                                    # original objects, untouched
```
Flag values on the Ollama handler [VERIFIED: `vars(OLLAMA_FORMAT_HANDLER)` run this session]: `{'format_type': <FormatType.JSON: 'json'>, 'use_wrapper': True, 'wrapper_key': 'extractions', 'use_fences': False, 'attribute_suffix': '_attributes', 'strict_fences': False, 'allow_top_level_list': True}`. `format_type` is an enum — store `.value`/`str`, not the enum (records hold primitives). `wrapper_key=None` in `OLLAMA_FORMAT_HANDLER` becomes `'extractions'` at construction (`format_handler.py:113-118`, verified in the vars output).

### Pattern 5: Empty-parse callout that is *true*
`[]` from `resolve` is ambiguous: a model reply of `{"extractions": []}` returns `[]` with **no error**, while bad JSON / wrong shape returns `[]` **because the chunk was omitted** [VERIFIED: /tmp/exp2.py and /tmp/exp_wrap.py "bad"/"emptylist"/"badshape" modes]. The Phase 1 config sentence (`empty_parse_message`: "Chunk omitted on parse or schema error; raw model text is kept above.") is only true in the second case.

Recommended disambiguation (~8 lines, no model call, `resolve` is pure — returns fresh objects every call [VERIFIED: /tmp/exp2.py "fresh objects each call: True"]): when the result is empty, re-run the **original** (unwrapped) resolve with `suppress_parse_errors=False` inside `try/except Exception as e`:

| Raw model text | Suppressed result | Re-run with `suppress_parse_errors=False` | Callout |
|----------------|-------------------|--------------------------------------------|---------|
| `{"extractions": []}` | `[]` | no error | new config line `empty_list_message` (valid empty list, nothing omitted) |
| `not json` | `[]` | `ResolverParsingError: Failed to parse JSON content: Expecting value…` | `empty_parse_message` + the error text |
| `{"extractions": [{"symptom": 1}, "x"]}` | `[]` | `ResolverParsingError: Each item in the sequence must be a mapping.` | `empty_parse_message` + the error text |
| ` ```json\n{…}\n``` ` with `use_fences=False` | `[]` | `ResolverParsingError: Failed to parse JSON content: Expecting value…` | `empty_parse_message` + error text — **the fence flag in the parse inputs explains it** (`use_fences=False` ⇒ `_extract_content` returns `text.strip()` unchanged, `format_handler.py:309-310`) |

If the plan prefers the smallest possible change, printing `empty_parse_message` for every `[]` satisfies STG-09 literally but mislabels the valid-empty-list case; flag this as a planner decision (see Open Questions / A3).

### Pattern 6: Align wrapper — in at call time, snapshot at exhaustion, same objects out
```python
def traced_align(self, *args, **kwargs):
  b = inspect.signature(original).bind(self, *args, **kwargs); b.apply_defaults()
  src, tok_off, chr_off = b.arguments['source_text'], b.arguments['token_offset'], b.arguments['char_offset']
  in_data = {'source_text': src, 'token_offset': tok_off, 'char_offset': chr_off or 0,
             'n_extractions': len(b.arguments['extractions'])}
  def gen():
    seen = []
    try:
      for e in original(self, *args, **kwargs):
        seen.append(e)
        yield e                                   # same object the aligner mutated
    finally:
      sink.append(StageRecord('align', in_data, {'extractions': snapshot_extractions(seen)}))
  return gen()
```
- `char_offset` defaults to `None` in the signature and `align` does `char_offset or 0` (`resolver.py:~392`) — print `chr_off or 0` so "0" is shown, not `None`.
- The aligner finishes all grounding on the **first** `next()` (before the first `yield`), so snapshotting at exhaustion equals snapshotting per yield; exhaustion also covers the empty case where nothing is ever yielded (verified: empty parse still produces an `align` record with `[]`).
- Source slice (STG-06): spans are document coordinates, so `slice = source_text[start - char_offset : end - char_offset]`; `None` interval → `config['ungrounded_label']`. [VERIFIED with a non-zero offset: `align(…, token_offset=5, char_offset=100)` gave `CharInterval(118, 126)` and `chunk[18:26]=='headache'`.]
- Do **not** snapshot at align call time — those are the same live objects as the parse snapshot and would add nothing (and would be the pre-align state anyway).

### Pattern 7: Offline proof with the real pipeline (no warm model)
```python
# VERIFIED: runs with no network; 1 fake HTTP call; wrappers on all 5 targets fire in order
with mock.patch.object(ollama.OllamaLanguageModel, '_ollama_query',
                       lambda self, prompt, **kw: {'response': CANNED}):
  doc = lx.extract(TEXT, prompt_description='Extract symptoms.', examples=EXAMPLES,
                   model_id='gemma3:4b', model_url='http://localhost:11434',
                   resolver_params={'format_handler': ollama.OLLAMA_FORMAT_HANDLER},
                   extraction_passes=1, debug=False, show_progress=False)
```
- Reuse the existing test constants: `_SOURCE_TEXT = "Patient reports a headache since Monday."`, `_CANNED = '{"extractions": [{"symptom": "headache"}, {"symptom": "purple elephant"}]}'` (tests/trace_extract_test.py) → one `MATCH_EXACT` `[18, 26)` and one ungrounded extraction, so one run covers the grounded and ungrounded align paths. Examples that align cleanly: `ExampleData(text="He has a cough.", extractions=[Extraction("symptom","cough")])`.
- Variants for STG-09: canned `"not json at all"` (parse error → `[]`), `'{"extractions": []}'` (valid empty), a fenced reply (flag explanation).
- `_ollama_query` is patched **in the test only**; the script gains no mock path. Phase 5 owns the real call.
- Real `lx.extract` here is a test device, not the script's `main()`; keep `main()` unchanged in Phase 4 (RUN-03 / "one extract" belongs to Phase 5).

### Pattern 8: Collect, then print (do not print from inside wrappers)
Wrappers only append `StageRecord`s to a caller-owned list; a separate `print_stage_records(records, config)` prints in catalog order with the existing `[label] function — path` headers (Phase 1 D-05/D-06) plus `in:`/`out:` blocks (the Phase 1 "header-only" rule D-02 applied to Phase 1 only). Reasons: parse/align print as a pair (`print_grounding_pair` needs both snapshots); on exception the caller prints whatever was captured in `finally` (ARCHITECTURE.md build step 6); nothing prints while a generator is half-consumed.

### Data captured per wrapper (STG-03 field list)

| Stage | `in` (live, from this call) | `out` (live, from this call) |
|-------|-----------------------------|------------------------------|
| chunk | `max_char_buffer`, source text | per chunk: `chunk_text`, `char_interval`, `token_interval`, `document_id` |
| prompt | `chunk_text`, `document_id`, `additional_context`, `context_window_chars` | full prompt string (same string must equal the `infer` `batch_prompts` entry) |
| model | `batch_prompts` (full), forwarded kwargs (redacted) | **raw model text** per `ScoredOutput` (+ score) — nothing parsed |
| parse | raw model text, format/fence/wrapper flags, `suppress_parse_errors` | `snapshot_extractions(result)` (grounding fields `None`), empty-parse callout when `[]` |
| align | `source_text` (chunk), `token_offset`, `char_offset` (print even when 0; label "chunk start in the document"), extraction count | `snapshot_extractions(yielded)`, per-extraction source slice or `ungrounded`; use `print_grounding_pair` for the before/after |

`WordAligner.align_extractions` stays a helper line under `[align]` (already printed by the catalog) — never a wrapped stage.

### Anti-Patterns to Avoid
- **`for c in original(self)` / `yield from original(self)` for `ChunkIterator.__iter__`:** infinite recursion (Pitfall 1).
- **`list()` inside `infer`/`align` wrappers, rebuilding `ScoredOutput`/`Extraction`:** changes what the Annotator sees; yield the original items.
- **Calling `build_prompt` twice to "capture" the string:** mutates `_prev_chunk_by_doc_id`.
- **Printing live `Extraction`s after align under the parse label:** mutated in place (Phase 2 hazard; the offline run printed post-mutation spans in the "resolve-out" record).
- **Reading `self.format_handler` flags from `extract` arguments instead of the Resolver instance:** the handler `extract` actually built is the only truth.
- **Wrapping `WordAligner`, passing `model=`, a second `infer`, `debug=True`.**

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Copying extractions at a boundary | A new copier | `snapshot_extractions` / `ExtractionSnapshot` (Phase 2) | Already tested incl. attribute aliasing and later mutation |
| Before/after grounding output | New pair printer | `print_grounding_pair(parse, align, ungrounded_label)` | Includes positional pairing guards (`TypeError`/`ValueError`) |
| Secret redaction of printed kwargs | New key list | `redact(mapping, keys=…)` (pass `keys` explicitly — default re-reads `config.yaml` on every call) | Keys already in config (D-14) |
| Reading call arguments by name | Manual `args[2]`/`kwargs.get` ladders | `inspect.signature(original).bind(...)` | `align`/`infer` are called both positionally and by keyword |
| Diagnosing why parse was empty | A parallel parser | Re-run the original `resolve(..., suppress_parse_errors=False)` | Same strictness/constraint logic as the real call |
| Restoring class attributes in tests | Manual try/finally per test | `mock.patch.object(cls, name, wrapper(original))` | Auto-restores, even on failure; independent of Phase 3 landing |
| Multi-line payload layout | Custom column logic | `textwrap.indent` + `pprint.pformat` | Stdlib, deterministic |

**Key insight:** the wrappers are thin read-only taps. Anything that re-computes pipeline behavior (second parse path, re-render of the prompt, second `infer`) is a second pipeline and breaks the "printed stages are the call's stages" contract.

## Common Pitfalls

### Pitfall 1: `RecursionError` from a generator wrapper on `ChunkIterator.__iter__`
**What goes wrong:** `maximum recursion depth exceeded` on the first chunk. **Verified** by running ARCHITECTURE.md's Pattern 1 shape (`for chunk in original(self): … yield chunk`) through `lx.extract`.
**Why:** `ChunkIterator.__iter__` returns `self` (`chunking.py:422-423`); `for … in <ChunkIterator>` calls `iter()` → the patched class attribute → a new generator → same line again.
**How to avoid:** Pattern 2 (`it = original(self)` then `next(it)` in a `while True` with `except StopIteration: return`).
**Warning signs:** traceback with repeating `traced_iter` frames; hang-less immediate failure.

### Pitfall 2: Forgetting `batch_prompts` is passed by keyword
**What goes wrong:** a wrapper declared `def infer(self, batch_prompts)` works, but `def infer(self, prompts_positional_only…)` or `args[0]` indexing raises `IndexError`. **Verified:** positional args are `()` and `batch_prompts` is only in kwargs.
**How to avoid:** `(self, *args, **kwargs)` + `inspect.signature(...).bind`.

### Pitfall 3: Dropping `max_workers` / `tokenizer_inst` / `debug`
**What goes wrong:** `TypeError`/behaviour change. `infer`, `resolve`, `align` all receive `max_workers`; `resolve` also `debug`, `align` also `tokenizer_inst` (verified runtime kwargs above).
**How to avoid:** forward `*args, **kwargs` verbatim to the original.

### Pitfall 4: Snapshotting `align` too early or per call instead of at exhaustion
**What goes wrong:** snapshot at call time shows the ungrounded state (identical to parse); an `align` record is never written for an empty parse because nothing is yielded.
**How to avoid:** `try/finally` around the `for` loop inside the generator (Pattern 6).

### Pitfall 5: "Empty parse" printed for a valid empty list
**What goes wrong:** developer reads "chunk omitted on parse error" when the model legitimately returned `{"extractions": []}`.
**How to avoid:** Pattern 5 disambiguation; keep raw text and the flags adjacent.

### Pitfall 6: Fenced model output with `use_fences=False`
**What goes wrong:** gemma-style ```` ```json ```` reply makes `parse_output` raise and the chunk silently disappears (suppressed). **Verified** (`'```json\n{"extractions": …}\n```'` → `ResolverParsingError … Expecting value`).
**How to avoid:** print `use_fences`/`strict_fences`/`use_wrapper`/`wrapper_key` in parse `in` (STG-09) next to the raw text.

### Pitfall 7: Spans are document coordinates, not chunk coordinates
**What goes wrong:** slicing the chunk text with `char_interval` directly is only correct when `char_offset == 0`; it silently shows the wrong text for later chunks.
**How to avoid:** subtract `char_offset` (Pattern 6; verified with offset 100).

### Pitfall 8: Test pollution from patched class attributes
**What goes wrong:** one failing test leaves `Resolver.align` wrapped for the rest of the pytest process.
**How to avoid:** `mock.patch.object` context managers in tests (auto-restore); never assign class attributes in test bodies without `finally`.

### Pitfall 9: Terminal escape injection via raw model text
**What goes wrong:** the raw model string is untrusted LLM output printed verbatim to the developer's terminal (ANSI/OSC sequences).
**How to avoid:** print raw text through a tiny helper that escapes non-printable characters except `\n`/`\t` (≈4 lines).

### Pitfall 10: Importing `langextract` at script top changes the Phase 1 catalog path
**What goes wrong:** Phase 2 deliberately had **no** `langextract` import in the script (02-01 acceptance). Wrapping needs class references (`ChunkIterator`, …) — that import belongs to Phase 3's `trace_probes`; Phase 4 wrapper factories take `original` as an argument and need **no** `langextract` import at all.
**How to avoid:** keep wrapper factories import-free (they receive `original`); let Phase 3 decide lazy vs top-level import for class references.

## Code Examples

See Patterns 1–7 above. Offline verification harness used for this research: `/tmp/exp_wrap.py` (all five wrappers, real `lx.extract`, `_ollama_query` patched) and `/tmp/exp2.py` (offset slice + empty-parse matrix). Both run in < 3 s under `.venv/bin/python`.

## State of the Art

| Old Approach (in project research) | Current Approach (verified) | Impact |
|------------------------------------|-----------------------------|--------|
| ARCHITECTURE.md Pattern 1: generator `for chunk in original(self)` | `next(it)` loop | Avoids `RecursionError` on `ChunkIterator.__iter__` |
| FEATURES/PITFALLS: empty list ⇒ "omitted on parse/schema error" | Disambiguate valid-empty vs error | Callout is truthful |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 3's `wrappers={...}` values are `original -> replacement` callables keyed by the catalog labels `chunk/prompt/model/parse/align` | Pattern 1, Open Questions | Low: a one-line adapter in Phase 4 if Phase 3 chooses differently; blocks Phase 4 *integration* tests, not unit tests |
| A2 | Collect-then-print (not streaming print from inside wrappers) is the desired UX | Pattern 8 | Low/medium: streaming would help when Ollama hangs, but breaks the parse↔align pair printing |
| A3 | A truthful empty-parse callout (two messages, re-run diagnosis) is preferred over printing `empty_parse_message` for every `[]` | Pattern 5 | Low: smaller change (always print the existing sentence) satisfies STG-09 literally but can mislead |
| A4 | The `prompt-template` stage gets its live data in Phase 5 (prompt in config, D-11), not from Phase 4 | User Constraints | Low: if wanted now, a ≈8-line read of `self._generator.template` inside the prompt wrapper (attributes `description`, `examples`; `prompting.py:41-49, 85-87`) |
| A5 | Importing `langextract` in the script (for class references) is acceptable for Phase 3/4 | Pitfall 10 | Low: Phase 2's "no import" criterion was plan-local; Phase 3 must still choose lazy vs top-level |
| A6 | Single-chunk v1: chunk records for a batch appear before that batch's prompts (extract default `batch_length=10`); correlating multi-chunk records is out of scope (STG-10) | Data flow | Low for v1; revisit with STG-10 |

## Open Questions (RESOLVED)

1. **Phase 3 wrapper-callable contract** — RESOLVED for Phase 4 planning (A1): keys = catalog labels `chunk/prompt/model/parse/align`; values = `original -> replacement`. Plans 04-01–04-02 and 04-03 Task 1 unit/integration-test via `mock.patch.object`; only 04-03 Task 2 needs `trace_probes` and may add a ≤10-line adapter if Phase 3 differs.
2. **Does Phase 3 import `langextract` at module top?** — RESOLVED for Phase 4 script: wrappers stay in `scripts/trace_extract.py` with **no** top-level `langextract` import (Phase 2 assertion preserved). Lazy import inside `trace_probes` remains Phase 3's call.
3. **Empty-parse wording (A3).** — RESOLVED in 04-02: truthful two-message callout; add `empty_list_message` to `config.yaml`; keep `empty_parse_message` for swallowed-error case; re-run original `resolve` with `suppress_parse_errors=False` when result is `[]`.
4. **How much of `kwargs` to print on `[model]`.** — RESOLVED in 04-01: print redacted kwargs via existing `redact(..., keys=)` (forwarding proof); sampling kwargs remain out of FEATURES scope.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `.venv/bin/python` | all tests/script runs | ✓ | 3.12.12 | — (bare `python` lacks PyYAML) |
| pytest | test runs | ✓ | 9.1.1 | `absltest` main |
| langextract (editable) | wrappers' targets, tests | ✓ | local tree | — |
| Ollama server + `gemma3:4b` | **not needed in Phase 4** | ✓ (server up, models include `gemma3:4b`; `ollama` 0.34.0) | — | Phase 4 is fully offline via patched `_ollama_query` |
| Network | none | n/a | — | — |

**Missing dependencies with no fallback:** none. **Phase 3 (`trace_probes`) is not implemented yet** — a planning/ordering dependency, not an environment gap.

## Test Strategy (tdd_mode is on; Nyquist section skipped per `workflow.nyquist_validation: false`)

| Req | Behavior | Test type | Command | File |
|-----|----------|-----------|---------|------|
| STG-03 | Each of the five stages produces a record with non-empty `in`/`out` from one real `lx.extract` (patched `_ollama_query`) | integration (offline) | `.venv/bin/python -m pytest tests/trace_extract_test.py -k wrappers -q` | `tests/trace_extract_test.py` (exists; add tests) |
| STG-03 | Prompt record string == `infer` `batch_prompts[0]`; exactly 1 fake HTTP call; wrapper yields same objects (document spans equal align snapshot) | integration | same | same |
| STG-04 | Model record `out` is raw text only; parsed extractions appear only in the parse record | unit | same | same |
| STG-06 | Align record: offsets `0/0`, `[18, 26)` + `match_exact` + slice `'headache'`; ungrounded entry shows `ungrounded`; non-zero-offset slice case via direct `Resolver.align(..., 5, 100)` | unit | same | same |
| STG-09 | Empty parse (`not json`) → callout text present beside raw text + flags; `{"extractions": []}` → valid-empty message; fenced reply → `use_fences=False` visible | unit | same | same |
| — | Chunk wrapper does not recurse and yields the same `TextChunk`s; `ChunkIterator.__iter__` original restored after test | unit | same | same |

**Sampling:** per task `.venv/bin/python -m pytest tests/trace_extract_test.py -q` (0.3 s today); full suite `.venv/bin/python -m pytest tests -m "not live_api and not integration" -q` before phase close. **Wave 0 gaps:** none — test file and loader (`_load_script_module`, `sys.modules` registration) already exist.

## Security Domain

`security_enforcement` is on (ASVS level 1, block on high).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2/V3/V4 Auth, session, access | no | local script, no auth |
| V5 Input validation / output encoding | yes (low) | Raw model text is untrusted: escape control characters before printing (Pitfall 9) |
| V7 Logging / V8 Data protection | yes | Redact printed kwargs with the existing `redact()` + config `redact_keys`; print no environment values; stdout only (no persisted store) |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| ANSI/OSC escape sequences in LLM output reach the terminal | Tampering/Spoofing | Escape non-printable chars except newline/tab in the raw-text printer |
| `api_key`-like kwargs printed in `[model]` `in` | Information disclosure | `redact(kwargs, keys=config['redact_keys'])` before storing in the record |
| Live objects held in records mutate later | Tampering (integrity of trace) | Records hold only primitives/`ExtractionSnapshot`; printers reject live objects (existing `TypeError` guard) |

## Project Constraints (from CLAUDE.md)

- Root `/CLAUDE.md`: per task/commit ≤ ~150 changed non-test lines and ≤ 3 source files; per plan ≤ ~400 non-test lines; tests in the same commit; build incrementally; no unrelated refactors or whole-file reformatting; planners state `Estimated diff: ~N lines` per task.
- `.claude/skills/diff-budget/SKILL.md`: executors verify with `git diff --cached --numstat -- . ':(exclude)tests'`; plan-checkers flag tasks without an estimate.
- `.planning/config.json` points `claude_md_path` at `./.claude/CLAUDE.md`, which does **not exist**; only the root `CLAUDE.md` applies. [VERIFIED: glob of `.claude/CLAUDE.md` returned 0 files]
- Style (existing script): 2-space indent, Apache header, `from __future__ import annotations`, reST-style `:param:` docstrings as in Phase 2.

### Size estimate and recommended split (non-test lines; per CLAUDE.md the phase must be ≥ 2 plans)

| Plan | Task | Content | Est. lines | Files |
|------|------|---------|-----------|-------|
| 04-01 | 1 | `StageRecord` dataclass + chunk wrapper factory + unit test (offline `ChunkIterator`) | ~40 | script |
| 04-01 | 2 | prompt wrapper (single call, record in/out) | ~20 | script |
| 04-01 | 3 | model wrapper (generator-transparent, raw text, redacted kwargs) + offline `lx.extract` integration test through chunk→prompt→model | ~35 | script |
| 04-02 | 1 | parse wrapper (snapshot at return, flags, raw text) | ~35 | script |
| 04-02 | 2 | empty-parse diagnosis + `empty_list_message` | ~20 | script, config |
| 04-02 | 3 | align wrapper (bound args, snapshot at exhaustion, slice) | ~40 | script |
| 04-03 | 1 | `print_stage_records`: headers + in/out blocks, safe raw-text printing, model vs parse separation | ~55 | script |
| 04-03 | 2 | parse callout + align detail (offsets, slice/`ungrounded`, reuse `print_grounding_pair`) | ~40 | script |
| 04-03 | 3 | full offline end-to-end test via `trace_probes` (needs Phase 3) | tests only | tests |

Total ≈ 285 lines across three plans (each < 400; each task < 150). Tasks touching `config.yaml` stay within 2 source files. Plans 04-01/04-02 wrapper unit tests use `mock.patch.object`, so they can be executed even before `trace_probes` merges; only 04-03 task 3 needs Phase 3.

## Sources

### Primary (HIGH confidence — read or executed this session)
- `langextract/chunking.py` (`TextChunk` 40-140, `ChunkIterator` 343-440, `__iter__` 422-423, `__next__` 441)
- `langextract/prompting.py` (`PromptTemplateStructured` 40-49, `QAPromptGenerator` 85-139, `ContextAwarePromptBuilder.build_prompt` 215-240)
- `langextract/providers/ollama.py` (`OLLAMA_FORMAT_HANDLER` 133-139, `infer` 266-316, `_ollama_query` 540-)
- `langextract/resolver.py` (`resolve` 276-335, `align` 337-410, aligner coordinates ~984-1016)
- `langextract/annotation.py` (`_document_chunk_iterator` 118-160, single pass 285-445, call sites 371/392/406/424)
- `langextract/extraction.py` (call construction 255-435: `alignment_kwargs.setdefault("suppress_parse_errors", True)`, `batch_length=10`, `max_char_buffer=1000`)
- `langextract/core/format_handler.py` (`FormatHandler` attributes 111-121, `parse_output` 169-262, `_extract_content` 296-350)
- Local scripts run: `/tmp/exp_wrap.py` (modes naive/canned/bad/emptylist/badshape), `/tmp/exp2.py`; `.venv/bin/python -m pytest tests/trace_extract_test.py` → 11 passed
- `scripts/trace_extract.py` (Phase 1–2 surface), `config.yaml`, `tests/trace_extract_test.py`, `.planning/{REQUIREMENTS,ROADMAP,STATE}.md`, `.planning/research/{ARCHITECTURE,PITFALLS,FEATURES,SUMMARY}.md`, Phase 1 CONTEXT/PATTERNS, Phase 2 SUMMARYs, `03-DISCUSS-CHECKPOINT.json`

### Secondary / Tertiary
- None — no web sources needed; this phase is entirely a local-tree question (no external libraries introduced).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib + existing env, nothing new.
- Architecture/wrapper shapes: HIGH — each shape executed against the real pipeline offline; one prior research example proven wrong and corrected.
- Pitfalls: HIGH — 1, 2, 3, 5, 6, 7 reproduced; 9 is reasoning on untrusted output (standard, unreproduced).
- Phase 3 interface: LOW/ASSUMED (A1) — Phase 3 undecided.

**Research date:** 2026-10-10
**Valid until:** 30 days, or until any of the five target signatures in `langextract/` changes (re-run `/tmp/exp_wrap.py`-style check).

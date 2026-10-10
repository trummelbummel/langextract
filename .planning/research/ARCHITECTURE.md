# Architecture Research

**Domain:** One-call stage trace attached to LangExtract's existing `lx.extract` pipeline
**Researched:** 2026-10-09
**Confidence:** HIGH

## Standard Architecture

This milestone does not add an application. LangExtract stays a library. One public function, `extract` in `langextract/extraction.py`, already owns call order. It returns only an `AnnotatedDocument` (string input) or a `list[AnnotatedDocument]` (document iterable). Prompt text, `TextChunk`s, raw model text, and unaligned `Extraction`s are locals inside that call. Nothing in the signature is a callback, sink, or stage result.

The script is an external observer. It calls `lx.extract` once. For that call only, it wraps the public methods `extract` already invokes, copies their inputs and outputs into stage records, and returns each original result unchanged. It does not subclass `Annotator`, does not pass `model=`, and does not reassemble `FormatHandler`, `Resolver`, or `Annotator` beside `extract`.

```
┌──────────────────────────────────────────────────────────────┐
│  scripts/trace_extract.py  (not installed, not a library)   │
│  catalog → printer → call-scoped probes → one lx.extract()  │
└────────────┬───────────────────────────────▲────────────────┘
             │ wraps these methods            │ return value
             │ for this call, then restores   │ AnnotatedDocument
             ▼                                │
┌──────────────────────────────────────────────────────────────┐
│  lx.extract  (langextract/extraction.py)  — unchanged        │
│  validate examples → create_model → FormatHandler → Resolver │
│  → Annotator.annotate_text                                   │
├──────────────┬────────────────┬──────────────────────────────┤
│ ChunkIterator│ ContextAware   │ Resolver.resolve             │
│ chunking.py  │ PromptBuilder  │ then Resolver.align          │
│              │ prompting.py   │ resolver.py                  │
├──────────────┴────────────────┴──────────────────────────────┤
│  OllamaLanguageModel.infer   providers/ollama.py             │
│  gemma3:4b via model_id (pattern ^gemma), local HTTP         │
├──────────────────────────────────────────────────────────────┤
│  AnnotatedDocument   core/data.py                            │
│  assembled inside Annotator, returned by extract             │
└──────────────────────────────────────────────────────────────┘
```

`prompt_validation.validate_prompt_alignment` also runs inside `extract`, before the model exists. It uses a separate `WordAligner` on the few-shot examples. That preflight is not the source-grounding stage. The script must not wrap `WordAligner.align_extractions`, or example checks will be printed as alignment.

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Stage catalog | Names the six printed stages and the function and file that own each one. No I/O. | A tuple in the script. Not a registry in `langextract/`. |
| Stage printer | Writes one record: stage name, owning function, file, data in, data out. | Plain stdout. Records are copies, not live objects. |
| Extraction snapshot | Copies `extraction_class`, `extraction_text`, `attributes`, `extraction_index`, and grounding fields at a boundary. | A small function in the script. Required because align writes onto the objects resolve just returned. |
| Call-scoped probes | Around one `lx.extract` call, wrap the five methods below, delegate, and restore the originals in `finally`, including on exception. | Stdlib `try`/`finally` assigning the class attribute. No `wrapt`, no library hook, no `debug=True`. |
| `lx.extract` invocation | The only run of the pipeline. Builds the Ollama model, format handler, resolver, and annotator itself. | `model_id="gemma3:4b"`, `model_url` for local Ollama, `extraction_passes=1`, `debug=False`, `show_progress=False`, `fetch_urls=False`. |
| Document printer | Prints the `AnnotatedDocument` `extract` returned. | Uses the return value. Does not probe the nested emitter inside `Annotator`. |

Probe targets, and only these:

| Stage | Wrap this | File | Leave alone |
|-------|-----------|------|-------------|
| Chunking | `ChunkIterator.__iter__` | `langextract/chunking.py` | `SentenceIterator`, private `_document_chunk_iterator` |
| Prompting | `ContextAwarePromptBuilder.build_prompt` | `langextract/prompting.py` | `QAPromptGenerator.render` (it does not see cross-chunk context) |
| Model call | `OllamaLanguageModel.infer` | `langextract/providers/ollama.py` | Do not pass `model=`. Do not wrap `BaseLanguageModel.infer` on the ABC. |
| Parsing | `Resolver.resolve` | `langextract/resolver.py` | `FormatHandler.parse_output` is inside resolve; it is not its own printed stage |
| Alignment | `Resolver.align` | `langextract/resolver.py` | `WordAligner.align_extractions` (also used by prompt validation) |
| AnnotatedDocument | none | return of `extract` in `langextract/extraction.py` | private `_emit_docs_iter` |

`Annotator` always constructs `ContextAwarePromptBuilder`, even when `context_window_chars` is `None`. Wrapping that method sees the prompt the model actually receives.

## Recommended Project Structure

```
scripts/
└── trace_extract.py     # one-call walkthrough; python scripts/trace_extract.py
```

Do not add a module under `langextract/`, a console script in `pyproject.toml`, or a file under `examples/ollama/`. `examples/ollama/demo_ollama.py` stays the result-and-HTML demo. `scripts/` is already the place for tools run as `python scripts/...` and excluded from the wheel. One file is the whole script. A tracer package, a callback argument on `extract`, or a pytest plugin would be a reusable tracer, which this milestone is not.

### Structure Rationale

- **`scripts/trace_extract.py`:** It imports the installed package and the stage classes it wraps. Import-linter contracts apply inside the package, not to this script. The script may import `langextract.chunking`, `langextract.prompting`, `langextract.resolver`, and `langextract.providers.ollama` to install probes. It must not add code to `langextract/core/` or `langextract/_compat/`.
- **No new package:** Stage records die when the process exits. There is no store, server, or second pipeline.

## Architectural Patterns

### Pattern 1: Call-scoped observer on the live path

**What:** Save each target from the class (`ChunkIterator.__iter__`, not an instance attribute), assign a wrapper for the duration of one `lx.extract(...)`, call the original once, return or yield what it returned, then put the original back in `finally`.

**When to use:** The value to print exists only as a local inside `extract`, and the printed stages must be the stages that call actually ran.

**Trade-offs:** The script is coupled to those five method names. That coupling is acceptable for one printed walkthrough. It is not acceptable as a library feature. A new dependency such as `wrapt` is unnecessary; its transient-wrapper docs describe the same try/finally shape, and this repo does not depend on it.

**Example:**
```python
original = ChunkIterator.__iter__

def _traced_iter(self):
  for chunk in original(self):
    print_stage("chunking", "ChunkIterator.__iter__", "langextract/chunking.py",
                data_in={"max_char_buffer": self.max_char_buffer},
                data_out=_chunk_record(chunk))
    yield chunk

ChunkIterator.__iter__ = _traced_iter
try:
  document = lx.extract(...)  # one call
finally:
  ChunkIterator.__iter__ = original
```

Save and restore the function on the class. Reading a method from an instance binds it; writing that bound object back does not restore the class attribute.

### Pattern 2: Snapshot before alignment mutates

**What:** `Resolver.resolve` returns new `Extraction` objects with `char_interval` and `alignment_status` unset. `WordAligner.align_extractions`, called by `Resolver.align`, then assigns `char_interval`, `token_interval`, and `alignment_status` on those same objects. `Annotator` appends those objects to the document.

**When to use:** The parse record and the alignment record must both be visible.

**Trade-offs:** The probe copies fields at the resolve return. It does not deepcopy the objects the pipeline keeps. Copying the live objects and handing the copies to `align` would desynchronize the document from the parse.

### Pattern 3: Generator-transparent wrappers

**What:** `OllamaLanguageModel.infer` yields one `[ScoredOutput]` per prompt. `Resolver.align` yields aligned extractions (or yields nothing when the parse list is empty). `Annotator` does `list(infer(...))` and then iterates `align`.

**When to use:** Every probe on `infer` and `align`.

**Trade-offs:** The wrapper must be a generator that records each item as the caller pulls it, then yields that same item. Listing the generator inside the probe, dropping an item, or catching `InferenceRuntimeError` / `ResolverParsingError` changes `extract`. `infer` must forward `**kwargs` (`max_workers` and any provider kwargs `extract` passes through). `align` must forward token and char offsets and alignment kwargs.

Call `build_prompt` exactly once inside its wrapper. The builder stores the previous chunk per `document_id` after each render. A second call would change the next prompt.

## Data Flow

### Request Flow

```
script installs probes
    ↓
lx.extract(text, prompt_description, examples,
           model_id="gemma3:4b", model_url=...,
           resolver_params={"format_handler": OLLAMA_FORMAT_HANDLER},
           extraction_passes=1, debug=False, show_progress=False)
    ↓
prompt validation on examples only  (not a printed stage)
    ↓
factory.create_model  →  OllamaLanguageModel   (script does not build this)
    ↓
FormatHandler + Resolver + Annotator           (script does not build these)
    ↓
Document(text)  →  ChunkIterator  →  TextChunk
    ↓
build_prompt(chunk_text, document_id, additional_context)  →  str
    ↓
infer(batch_prompts)  →  [ScoredOutput(score=1.0, output=str)]
    ↓
resolve(scored_outputs[0].output)  →  Sequence[Extraction]  (grounding unset)
    ↓
align(extractions, chunk_text, token_offset, char_offset)
    →  same Extraction objects, spans and AlignmentStatus filled in
    ↓
AnnotatedDocument(document_id, extractions, text)
    ↓
script prints that return value, then restores the five methods
```

Direction is one way. Lower layers do not call `extract`. Probes do not feed data back into the next stage. The next stage receives the original return value.

For a string shorter than `max_char_buffer` (default 1000) and `extraction_passes=1`, that path runs once and `extract` returns one `AnnotatedDocument`. The milestone sample should stay in that shape so the printed document is the single pass the probes saw. Probes still record per chunk: if the text is longer, chunk → prompt → infer → resolve → align repeats, and the document is printed once at the end. `Annotator` emits a document only after later chunks cannot belong to it. Do not expect a document record between chunks.

### State Management

```
per extract() call (library, unchanged)
    prompt template, Ollama instance, FormatHandler, Resolver
    Annotator per-document extraction lists
    ContextAwarePromptBuilder._prev_chunk_by_doc_id
    Document.tokenized_text cache

per script process (probes only)
    five saved callables
    stage records (copies)
    restored in finally; nothing left on the classes
```

Do not enable `debug=True`. `configure_debug_logging` attaches a process-wide handler and leaves it on. `debug_log_calls` is only on tokenizer methods, so it does not print these stages. Ollama `infer` is a sequential loop, not a thread pool. These probes do not need locks. Do not generalize them to Gemini or OpenAI, where `infer` fans out with `ThreadPoolExecutor`.

`Document.document_id` is generated on first access (`doc_` plus eight hex chars) inside `annotate_text`. A chunker the script ran itself would mint a different id. That is one reason the chunk record must come from the live `ChunkIterator`, not from a preview pass.

### Key Data Flows

1. **Chunking:** In: document text, `max_char_buffer`, the tokenizer `extract` passed (or `RegexTokenizer`). Out: each `TextChunk`'s `chunk_text`, `document_id`, `token_interval` (`start_index`, `end_index`), `char_interval` (`start_pos`, `end_pos`). `token_offset` for align is `token_interval.start_index`. `char_offset` is `char_interval.start_pos`. Reading `chunk_text` and `char_interval` is safe; both are cached properties.

2. **Prompting:** In: `chunk_text`, `document_id`, `additional_context`, plus the template already on the generator (description and `ExampleData`s) and any previous-chunk suffix the builder holds. Out: one prompt string. After `infer` returns, `Annotator` does `del prompts`. Record the prompt strings at `build_prompt` return and again as `infer`'s `batch_prompts`. Do not read them back from the annotator afterward.

3. **Model call:** In: `batch_prompts: Sequence[str]` and forwarded kwargs. Out: each yielded `[ScoredOutput]`. The annotator keeps `scored_outputs[0]` only (`score`, `output`). Ollama yields score `1.0` and the generate-response text. The probe records that text and yields the same list.

4. **Parsing:** In: `scored_outputs[0].output` (string) and `suppress_parse_errors` (extract sets this `True` unless `resolver_params` overrides it). Out: a sequence of `Extraction` with class, text, attributes, and index. Grounding fields are unset. On a suppressed parse error the out record is `[]`. Snapshot this sequence before returning it.

5. **Alignment:** In: that sequence, `chunk_text`, `token_offset`, `char_offset`. Out: the same objects after align, now with `char_interval`, `token_interval`, and `alignment_status` (`MATCH_EXACT`, `MATCH_GREATER`, `MATCH_LESSER`, `MATCH_FUZZY`). Unaligned extractions keep a null `char_interval` and are still appended. Snapshot at each yield.

6. **AnnotatedDocument:** In: the aligned extractions and the source text held by the annotator. Out: the object `extract` returns (`document_id`, `text`, `extractions`). For this script's string input that object is not wrapped in a list.

`resolver_params={"format_handler": OLLAMA_FORMAT_HANDLER}` is the Ollama module's documented caller argument. `extract` pops that handler and passes the same instance to both `Annotator` and `Resolver`. `wrapper_key=None` on that handler still becomes `"extractions"` when `use_wrapper=True`. Passing it does not add a second pipeline. Do not also pass `model=`: `extract` then skips `factory.create_model`, ignores `use_schema_constraints`, and warns. `gemma3:4b` already matches `OLLAMA_PATTERNS` (`^gemma`), so `model_id` selects `OllamaLanguageModel` and `FormatModeSchema` (JSON, raw output, fences off) through the normal path.

## Scaling Considerations

Scale here is chunks and passes, not users. The script is one process and one call.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| One short text, one pass | This milestone. One chunk, sequential Ollama `infer`, one `AnnotatedDocument`. Probes stay as thin wrappers. |
| Several chunks, one pass | Same probes. Records repeat per chunk. Print the document once from the return value. Do not buffer a second copy of the source text in the script. |
| `extraction_passes > 1` | Out of this milestone. The annotator materializes every document and reruns infer. The return value is the first-pass-wins merge, not pass 0. A single printed document would no longer match one pass of probe records. Keep `extraction_passes=1`. |

### Scaling Priorities

1. **First bottleneck:** Ollama latency on `infer`. The script waits on the same HTTP call `extract` makes. Do not add a second infer to "show" the model stage.
2. **Second bottleneck:** Printing full prompt text for many chunks. Keep the sample under `max_char_buffer`. Truncation belongs in the printer, not in the wrapper's return path.

## Anti-Patterns

### Anti-Pattern 1: Rebuilding the pipeline beside `extract`

**What people do:** Construct `PromptTemplateStructured`, `FormatHandler`, `Resolver`, and `Annotator` in the script, call them, and skip `lx.extract` or call it as a second unrelated run.

**Why it's wrong:** `Annotator.__init__` defaults format to YAML and fences off when no handler is passed. `extract` defaults JSON and derives fences from the schema. Two wiring paths drift, and a second `infer` is a second model call. The printed stages are then not the call the milestone asked for.

**Do this instead:** One `lx.extract` call. Observe the methods that call already uses.

### Anti-Pattern 2: Passing `model=` to log inference

**What people do:** Build `OllamaLanguageModel` in the script, wrap that instance, and pass `model=`.

**Why it's wrong:** `extract` treats a passed model as already configured. Schema constraints from examples are not applied. The trace is a different call than `model_id="gemma3:4b"`.

**Do this instead:** Let `extract` call `factory.create_model`. Wrap `OllamaLanguageModel.infer` on the class so whichever instance `extract` builds is the one recorded.

### Anti-Pattern 3: Holding live `Extraction`s as the parse record

**What people do:** Store the list `resolve` returned and print it after `extract` returns.

**Why it's wrong:** Align fills `char_interval` and `alignment_status` on those objects. The parse record then looks grounded. The document and the parse stage are no longer distinguishable.

**Do this instead:** Copy fields when `resolve` returns, before the wrapper returns the original sequence.

### Anti-Pattern 4: `debug=True` or a private-method patch as the walkthrough

**What people do:** Turn on library debug logging, or wrap `_annotate_documents_single_pass`.

**Why it's wrong:** Debug logging stays on for the process and does not emit owning function, file, and data in/out for these stages. The private annotator method is the reusable-tracer shape, and it hides the stage boundaries inside one function.

**Do this instead:** Probe the five public methods above, print the `extract` return value, and leave `debug=False`.

### Anti-Pattern 5: Consuming or replacing generator results

**What people do:** `outputs = list(original_infer(...))` inside the probe and return that list, or return a freshly built `ScoredOutput`.

**Why it's wrong:** A rebuilt output is a different object than the provider yielded. Swallowing an empty scored-output list hides `InferenceOutputError`. Listing is what the annotator already does for `infer`; doing it in the probe is harmless only if the wrapper still returns those same objects and still raises. `align` must keep yielding the same objects the aligner mutated.

**Do this instead:** Yield the original items. Snapshot copies on the side.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Local Ollama | Only through `OllamaLanguageModel.infer`, which `extract` calls after `model_id="gemma3:4b"` resolves. Default base URL `http://localhost:11434`, overridable with `model_url` (`extract` also forwards that as `base_url`). | The script does not POST itself. `gemma3:4b` must already be served. No cloud provider, no API key. A connection error must still hit `finally` and restore probes. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Script → `lx.extract` | One direct call | Sole pipeline entry. Arguments only. No monkeypatch of `extract` itself. |
| Script → stage classes | Class-attribute wrap, restored in `finally` | Chunk iterator, prompt builder, Ollama `infer`, `Resolver.resolve`, `Resolver.align`. |
| `extract` → factory / annotator | Direct, unchanged | Script does not sit between them. |
| Annotator → `infer` | `batch_prompts` in, iterator of `Sequence[ScoredOutput]` out | Probe records and yields. Annotator keeps index 0. |
| Annotator → `resolve` then `align` | Raw string in, unaligned `Extraction`s out, then chunk text plus offsets in, mutated `Extraction`s out | Parse snapshot is a copy. Align snapshot is taken per yield. |
| `extract` → script | Return value | One `AnnotatedDocument` for a string. Printer reads it after probes have run. |
| Prompt validation → `WordAligner` | Direct, before inference | Not wrapped. Not printed as alignment. |

## Suggested Build Order

Build the script in this order. Each step can exist before Ollama is contacted. Later steps depend on earlier ones.

1. **Catalog and printer.** Static stage names, owning function, owning file, and the field lists in the data-flow section. No `extract` call. This fixes the record shape before any wrapper exists, including the rule that grounding fields are absent on the parse record and present on the alignment record.

2. **Extraction snapshot.** Depends on the printer's field list. Used by the parse and align probes. Without it, step 4 cannot show parsing and alignment as different stages.

3. **Probe context manager.** Install and restore the five class attributes in `finally`. Depends on the printer and the snapshot. Does not call `extract` yet. A failed restore is a script bug that would leak into any later import in the same process.

4. **Wrappers, in pipeline order.** Chunk iterator, then `build_prompt`, then `infer`, then `resolve`, then `align`. Each wrapper depends on step 3. `infer`'s wrapper depends on nothing about HTTP; it only records arguments and yields the original iterator. Order of installation can be one block. Order of *records* must follow the flow above, which falls out of `extract` calling them in that order.

5. **One `lx.extract` call.** Depends on steps 3 and 4 being active. This is the first step that needs local `gemma3:4b`. Arguments: source text under `max_char_buffer`, prompt, examples, `model_id="gemma3:4b"`, `model_url`, documented `OLLAMA_FORMAT_HANDLER`, `extraction_passes=1`, `debug=False`, `show_progress=False`. Do not add `model=`, `fetch_urls=True`, or a second infer.

6. **Print the returned `AnnotatedDocument`.** Depends on step 5 returning. No probe. If step 5 raises, print the stage records already captured, restore probes, and let the exception propagate.

Roadmap implication: a phase that only pretty-prints canned records can land before a phase that runs Ollama. A phase that re-chunks or re-prompts outside `extract` should not exist. The live call is one phase, after the printer and the probes, because the call is unreadable without them and the probes are untestable as a walkthrough without the printer's snapshot rules.

## Sources

- Local pipeline, read 2026-10-09 at the mapped tree: `langextract/extraction.py` (`extract` wires model, handler, resolver, annotator and returns the annotator result), `langextract/annotation.py` (`ContextAwarePromptBuilder`, `infer`, `resolve`, `align`, `del prompts`), `langextract/chunking.py` (`ChunkIterator`, `TextChunk`), `langextract/prompting.py` (`build_prompt` updates per-document context), `langextract/resolver.py` (`resolve` returns ungrounded `Extraction`s; `align_extractions` assigns `char_interval` and `alignment_status` on those objects), `langextract/providers/ollama.py` (`infer` yields `ScoredOutput`; `OLLAMA_FORMAT_HANDLER`), `langextract/core/data.py` (`AnnotatedDocument`, `AlignmentStatus`), `langextract/core/format_handler.py` (`from_resolver_params` uses a passed `format_handler` for both sides), `langextract/providers/patterns.py` (`^gemma`). Confidence HIGH.
- Same call order on the public GitHub tree for `extraction.py`, `annotation.py`, and `providers/ollama.py` (no stage callback; `model=` documented as an alternate entry that skips factory). Confidence MEDIUM, cross-checked with the local tree.
- Observer shape: a wrapper that calls the original, returns that result, and is removed when the guarded call ends, including on exception. [wrapt transient function wrapper](https://wrapt.readthedocs.io/en/master/monkey.html). Confidence MEDIUM. Use the stdlib form in the script; do not add the package.

---
*Architecture research for: one-call stage trace on the existing LangExtract extract pipeline*
*Researched: 2026-10-09*

# Feature Research

**Domain:** Developer walkthrough of one source-grounded `lx.extract()` call
**Researched:** 2026-10-09
**Confidence:** MEDIUM

The audience is a developer who already has LangExtract and wants to see which function owns each stage of one local call. The script is a printed walkthrough. It is not a second extraction product, and it is not a tracer you turn on later.

Stage shapes below come from the mapped pipeline (`extract` → chunk → prompt → `infer` → `resolve` → `align` → `AnnotatedDocument`). What other tools treat as a “trace” comes from current official docs (OpenTelemetry GenAI spans v1.41.0, DSPy `inspect_history`, LangSmith run format, LlamaIndex callbacks, spaCy `analyze_pipes`, the LangExtract README). `gsd-core` classifies verified websearch findings as MEDIUM; that is the ceiling on the comparison claims.

## Feature Landscape

### Table Stakes (Users Expect These)

Missing any of these and the printout fails the job: you cannot point at a stage and see who owns it and what it consumed.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| One call, named model | A walkthrough that hides which model ran cannot be repeated. OpenTelemetry requires the operation and provider on an inference span, and the request model when it is known. | LOW | Header prints `lx.extract`, `model_id=gemma3:4b`, provider `OllamaLanguageModel`, and the local base URL host. One input string. |
| Six stages in runtime order | LangSmith separates `prompt`, `llm`, and `parser`. LlamaIndex separates `CHUNKING` from `LLM`. This pipeline’s order is fixed: prompt template, chunk, rendered prompt, model call, parse, align, then the document. | LOW | Print the shared template once, then one block per chunk: chunk → rendered prompt → raw model text → parsed extractions → aligned extractions. End with the `AnnotatedDocument` the call returned. |
| Owning function and file on every stage | The milestone exists so a later change can name the stage it touches. A component name alone (spaCy `pipe_names`) does not locate the code. | LOW | Use the function that performs the step, plus the repo-relative file. See the stage map under Dependency Notes. |
| Live data in and data out | DSPy’s useful part is the prompt and response that were actually sent. spaCy `analyze_pipes` is static and, per its own docs, will not catch a component that does not do what it declares. | MEDIUM | Each stage prints the values from this call. Payloads are full for this short input. `debug_log_calls` truncates strings at 500 characters and sequences at 20 items, so those logs are the wrong surface. |
| Shared prompt template, then the rendered prompt | Few-shot text is the contract the model sees. The rendered string also depends on the chunk. | LOW | In: `prompt_description`, `ExampleData` (example text, `extraction_class`, `extraction_text`, attributes). Out: the string from `ContextAwarePromptBuilder.build_prompt` (`langextract/prompting.py`), which calls `QAPromptGenerator.render`. |
| Chunk text plus its intervals | LlamaIndex chunk events show text in and chunks out. Alignment later adds `token_offset` and `char_offset` from this chunk, so the intervals are part of the chunk’s output. | LOW | Owner: `ChunkIterator` in `langextract/chunking.py`, driven by `_document_chunk_iterator` in `langextract/annotation.py`. Out: `chunk_text`, `char_interval` (`start_pos`, `end_pos`), `token_interval` (`start_index`, `end_index`). Print the chunk even when the input yields one window. |
| Raw model string, separate from parsed objects | The model stage’s output is text. LangSmith’s `llm` run holds that text; the `parser` run is a later type. Ollama’s `infer` yields `ScoredOutput(score=1.0, output=text)`. | MEDIUM | Owner: `OllamaLanguageModel.infer` in `langextract/providers/ollama.py`. In: the prompt string. Out: `output` only. Leave the HTTP body, sampling kwargs, and `thinking` trace out of the print. |
| Parse result with grounding fields still empty | `Resolver.resolve` returns `Extraction` objects before `Resolver.align` writes spans. `extract` sets `suppress_parse_errors=True`, so a bad chunk becomes `[]` and the document can look like “nothing found.” | LOW | Owner: `Resolver.resolve` in `langextract/resolver.py` (it calls `FormatHandler.parse_output`). In: raw model string, plus format type, fence flag, and wrapper key. Out: `extraction_class`, `extraction_text`, `attributes`. Show `char_interval is None` and `alignment_status is None`. An empty list stays on screen. |
| Aligned spans and status | Grounding is this library’s result, and the README only shows it on the finished document. Status is `match_exact`, `match_greater`, `match_lesser`, or `match_fuzzy`. A miss stays `char_interval is None`. | LOW | Owner: `Resolver.align` in `langextract/resolver.py`. In: the unaligned list, `chunk_text`, `token_offset`, `char_offset`. Out: `char_interval`, `alignment_status`, and `document_text[start:end]` when the interval is present. |
| The `AnnotatedDocument` the call returned | The public return is the thing later code consumes. The stage dump has to meet it. | LOW | `document_id`, `text`, and the extraction list from that `extract()` return (`langextract/core/data.py`, assembled in `Annotator.annotate_text`). |
| Same call, one inference | A second `infer` to “illustrate” the model can disagree with the document just printed. Chunking and prompt rendering are deterministic; the model string is not. | MEDIUM | Prompt, raw output, parse list, aligned list, and final document are one `lx.extract()` execution. Recomputing a prompt for display is acceptable only when it is the same builder and the same chunk the call used. |
| Short input, every byte of that call | Production traces omit prompt content by default because of volume and privacy (OpenTelemetry Opt-In). This script is one local call; the text is the point. | LOW | Keep the source under the default `max_char_buffer` (1000) so the run is one chunk and the prompt fits a terminal. Print that chunk’s intervals anyway. |
| Fail before a fake empty trace | If Ollama is down or `gemma3:4b` is missing, an empty extraction list looks like a parse or alignment result. | LOW | One availability check, then a clear stop. `examples/ollama/demo_ollama.py` already does this for a different model and a different output; copy the check, not the demo. |
| No credentials in the print | `debug_utils` redacts `api_key` and similar names. A local Ollama call usually has none. | LOW | If any provider kwargs are printed, redact those keys. Do not print environment values. |

### Differentiators (Competitive Advantage)

These are why this printout is more useful than `inspect_history`, a span export, or the existing HTML demo. Ship the first three with the script. They are small and they are the core value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Before/after grounding pair | A generic LM dump ends at the response string. The README ends at highlighted entities. The pair shows that parse did not ground anything and align did. | LOW | For each extraction, print the resolve record and the align record together. This is the line a later change to `resolver.py` has to keep true. |
| Source slice beside the span | The usage notes already tell callers to read `result.text[start:end]` and to drop `char_interval is None`. Doing it in the trace makes `match_fuzzy` and a total miss visible without a debugger. | LOW | Print the slice only when both ends are set. Print `ungrounded` when `char_interval` is missing. |
| Stable stage labels | A later request can say “the parse stage” and mean one function. | LOW | Labels: `prompt-template`, `chunk`, `prompt`, `model`, `parse`, `align`, `annotated-document`. Put the label, the function, and the file on the same header line. |
| Empty-parse called out in words | `[]` from `suppress_parse_errors` is easy to read as “the model found nothing.” | LOW | When resolve returns an empty list, print one line that the chunk was omitted on a parse or schema error, and keep the raw model text above it. |
| Offsets named on a one-chunk run | Align’s document coordinates are chunk start plus a local match. On a single chunk those offsets are often 0, which hides the parameter. | LOW | Print `token_offset` and `char_offset` with the words “chunk start in the document,” including when the value is 0. |
| Helper named inside align | `Resolver.align` delegates to `WordAligner.align_extractions`. Readers who grep for the algorithm need that name. | LOW | One line under the align header. Do not make `WordAligner` its own stage. |
| Format fence and wrapper next to parse | Parse failures are usually a fence or the `extractions` wrapper, not the aligner. | LOW | Print `format_type`, `use_fences`, and the wrapper key as parse inputs. `extract` builds one `FormatHandler` and shares it with the resolver and the annotator. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Reusable tracer, callback manager, or OpenTelemetry exporter | Production tools are built this way, and content capture is a flag you can leave on. | The milestone is one printed call. An exporter adds span trees, sampling, and a content opt-in whose default is off. That default removes the payloads this script exists to show. | `print` sections from this script only. |
| Hooks or new parameters on `lx.extract` | The clean way to observe intermediates. | Library changes are out of scope until one is named. `extract` deletes each prompt batch after `infer`, so the script cannot read them off the return value. | Observe this one call from the script. Leave `extraction.py` unchanged. |
| A second pipeline beside `extract()` that calls the model again | Easy to print stages if you reimplement the loop. | Two inferences can diverge, and the printed document may not be the one the stages describe. | One `lx.extract()` call. Stage values belong to that call. |
| Cloud providers, model switch, or a provider tour | Demos often accept `--model` and show Gemini or OpenAI. | Locked: local Ollama `gemma3:4b` only. Another provider changes auth, schema, and batch behavior. | Hard-code this model. Mention the provider class and host in the header. |
| Replacing `examples/ollama/demo_ollama.py` | That file already runs Ollama and prints a summary. | It targets `gemma2:2b`, several examples, JSONL, and HTML. It does not name stage owners or show parse versus align. | Leave that demo in place. This script prints stages. |
| `debug=True` as the walkthrough | The library already logs resolver input, parsed content, and alignment. | Logs are unstructured, process-wide once configured, and truncated (`_MAX_STR` 500, `_MAX_SEQ` 20). They do not carry a function-and-file contract. | Explicit stage sections with full text for this short input. |
| LM-history only (DSPy `inspect_history`) | The prompt and the response feel like the whole story. | Official DSPy docs say this history omits every non-LM step. Here that drops chunking, parse, and align. | Print all six stages. The model section is one of them. |
| Static file map (`analyze_pipes` style) | A table of modules would satisfy “which file.” | spaCy documents that this analysis does not run the pipeline, so it cannot show data in or out. | Run the call. Print live values under each file name. |
| Token counts, latency, cost, eval scores | LangSmith runs expose all of these. | They do not say which function owns a stage. Ollama locally has no price. Timing belongs in a benchmark. | Omit metrics. A failed call prints the exception and stops. |
| HTML visualization, JSONL save, progress bars | The README and the Ollama demo already teach this path. | Those outputs are the finished document, not the stages. tqdm replaces payloads with a counter. | Stdout sections. Callers who want HTML already have `lx.visualize`. |
| Multi-pass, batch APIs, `context_window_chars`, `output_schema`, URL fetch | All of these exist on `extract`. | They add passes, merges, GCS or OpenAI batch jobs, or a schema path Ollama does not implement. The default path is one pass and examples. | `extraction_passes=1`, no schema, a literal string, `fetch_urls` left off. |
| Multi-chunk or full-document trace in v1 | Offset shifting is easier to see with two windows. | The default buffer is 1000 characters. A long text multiplies prompts and hides the stage contract in volume. | One chunk in v1. Print offsets even when they are 0. Add a second chunk only when a chunking change is the question. |
| Interactive debugger, breakpoints, or token streaming | Stepping feels more precise. | The deliverable is a readable log of one call, shareable as terminal output. | Sectioned stdout. |
| Full tokenizer token dump | Alignment is token-based, so dumping tokens seems thorough. | The token list dwarfs the stage contract. Endpoints are what `align` receives. | Print `token_interval` start and end only. |
| Golden-set diff or pass/fail on the extractions | Traces often grow an eval column. | That is a second product. Grounding quality here is “does the slice match the extraction text.” | The source slice next to each span. |
| Persisted trace store | A JSON file of the walkthrough can be diffed later. | A store is the start of a tracer. | Stdout only. |
| Hand-written prompt text | Faster than calling the builder. | Fences, the `extractions` wrapper, and example rendering drift from `FormatHandler`. | Call `ContextAwarePromptBuilder.build_prompt` / `QAPromptGenerator.render`. |

## Feature Dependencies

```
Call header (model, provider, one document)
    └──requires──> Prompt template (description + examples)
                       └──requires──> Chunk (text + char/token intervals)
                                          └──requires──> Rendered prompt
                                                             └──requires──> Model call (raw ScoredOutput)
                                                                                └──requires──> Parse (ungrounded Extraction list)
                                                                                                   └──requires──> Align (spans, status, offsets)
                                                                                                                      └──requires──> AnnotatedDocument

Source slice ──enhances──> Align
Before/after grounding pair ──enhances──> Parse + Align
Empty-parse note ──enhances──> Parse
Format fence and wrapper ──enhances──> Parse
Stable stage labels ──enhances──> every stage

Second infer ──conflicts──> One extract() call
Reusable tracer / library hooks ──conflicts──> Script-only milestone
HTML / JSONL demo ──conflicts──> Stage walkthrough
debug=True log capture ──conflicts──> Full live payloads
Multi-pass / schema / cloud provider ──conflicts──> Default Ollama path
```

### Dependency Notes

- **Rendered prompt requires the chunk:** `ContextAwarePromptBuilder.build_prompt` takes `chunk_text`. The shared template (description and examples) can print first; the prompt string cannot.
- **Parse requires the raw model string from this call:** `Resolver.resolve` does not see the prompt. Re-running `infer` produces a different string, so the parse list would describe a different call than the document.
- **Align requires parse output and chunk offsets:** `Resolver.align` takes the unaligned sequence, `chunk_text`, `token_offset` (`token_interval.start_index` or 0), and `char_offset` (`char_interval.start_pos` or 0).
- **The document requires align:** `Annotator.annotate_text` returns one `AnnotatedDocument` whose extractions are the aligned ones. Unaligned objects never become the return value.
- **Source slice enhances align:** It needs `AnnotatedDocument.text` (or the input string) plus `CharInterval`. It does not change align.
- **Empty-parse note enhances parse:** It is only meaningful next to the raw string and the `[]` result. `extract` swallows `FormatError` and schema `ValueError` when `suppress_parse_errors` is true.
- **Second infer conflicts with one call:** The locked decision is a single `lx.extract()`. Deterministic stages may be shown from the same inputs; the model string may not be regenerated.
- **Library hooks conflict with the script-only milestone:** Observation has to live in the script. Designing that observation is an architecture task; the feature requirement is that the printed bytes match the call.
- **`debug=True` conflicts with full payloads:** Truncation and unstructured absl lines cannot satisfy “data in and data out.”

**Stage map (print these owners):**

| Stage label | Function | File |
|-------------|----------|------|
| `prompt-template` | `PromptTemplateStructured` / examples passed into `extract` | `langextract/prompting.py`, `langextract/extraction.py` |
| `chunk` | `ChunkIterator` via `_document_chunk_iterator` | `langextract/chunking.py`, `langextract/annotation.py` |
| `prompt` | `ContextAwarePromptBuilder.build_prompt` | `langextract/prompting.py` |
| `model` | `OllamaLanguageModel.infer` | `langextract/providers/ollama.py` |
| `parse` | `Resolver.resolve` | `langextract/resolver.py` |
| `align` | `Resolver.align` | `langextract/resolver.py` |
| `annotated-document` | return of `extract` / `Annotator.annotate_text` | `langextract/extraction.py`, `langextract/annotation.py`, `langextract/core/data.py` |

## MVP Definition

### Launch With (v1)

The first milestone is the script. These are one printout, not a phased product.

- [ ] Header — `gemma3:4b`, Ollama, one short document, availability check before any stage
- [ ] Prompt template — description and examples, full text
- [ ] Chunk — text, character interval, token interval, even for a single window
- [ ] Rendered prompt — the string `build_prompt` produced for that chunk
- [ ] Model — raw `ScoredOutput.output` from the one `infer` inside that `extract()`
- [ ] Parse — class, text, attributes, grounding fields still empty; empty list visible
- [ ] Align — offsets, `char_interval`, `alignment_status`, source slice or `ungrounded`
- [ ] `AnnotatedDocument` — the object `extract()` returned
- [ ] Before/after pair and stable labels — same headers a later change request can cite
- [ ] Fence, wrapper key, and the empty-parse sentence — so a bad generation is not read as a miss

### Add After Validation (v1.x)

Add only when a named change needs them.

- [ ] Two-chunk input — when someone is changing `ChunkIterator` or offset math and a 0 offset is no longer enough
- [ ] Prompt-validation line — `validate_prompt_alignment` already runs before the model unless level is `OFF`. Print it only when an example fails alignment and the script must show that the later stages never ran
- [ ] `WordAligner` parameter echo — threshold and algorithm, when alignment quality is the change under discussion

### Future Consideration (v2+)

- [ ] Reusable tracer — after a specific library change is named and needs to be observed on more than one call
- [ ] Multi-pass merge trace — only with a named recall change; pass 0 is the only pass that records debug alignment today
- [ ] Schema or cloud-provider walkthrough — different code path (`output_schema` is Gemini and OpenAI)
- [ ] HTML, JSONL, eval harness — already covered by `lx.visualize`, `io.save_annotated_documents`, and the Ollama demo

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Six stages with function, file, and live in/out | HIGH | MEDIUM | P1 |
| One `extract()` and one `infer` | HIGH | MEDIUM | P1 |
| Raw model text separate from parse | HIGH | LOW | P1 |
| Align spans, status, and source slice | HIGH | LOW | P1 |
| Before/after grounding pair | HIGH | LOW | P1 |
| Empty-parse sentence and format flags | HIGH | LOW | P1 |
| Short single-chunk input, full payloads | HIGH | LOW | P1 |
| Ollama preflight and secret redaction | MEDIUM | LOW | P1 |
| Stable stage labels | MEDIUM | LOW | P1 |
| Two-chunk offset demonstration | MEDIUM | MEDIUM | P2 |
| Prompt-validation line | LOW | LOW | P2 |
| WordAligner parameter echo | LOW | LOW | P3 |
| Reusable tracer or exporter | LOW | HIGH | P3 |

**Priority key:**

- P1: Must have for the script to do its job
- P2: Add when a named change needs it
- P3: Defer until a later milestone names it

## Competitor Feature Analysis

| Feature | DSPy `inspect_history` | OTel GenAI spans (v1.41.0) | LangSmith runs | LlamaIndex callbacks | spaCy `analyze_pipes` | LangExtract README and `demo_ollama.py` | This script |
|---------|------------------------|----------------------------|----------------|----------------------|-----------------------|------------------------------------------|-------------|
| What the developer sees | Last LM prompt and raw response | Span name, provider, model; content only if opted in | Named runs with inputs and outputs; separate `prompt`, `llm`, `parser` types | Chunk text before/after; prompt and completion | Component names and declared assigns/requires | Final extractions, `char_interval`, HTML | Live in/out for prompt, chunk, model, parse, align, document |
| Runs the pipeline | Yes, LM calls only | Yes, if instrumented | Yes, if instrumented | Yes | No | Yes, results only | Yes, one `extract()` |
| Shows grounding | No | No | No | No | No | On the finished document and in HTML | Parse record, then align record, plus the source slice |
| Names the owning file | No | Span name only | Run name only | Event type only | Component name only | No | Function and repo path on each section |
| Fit for this milestone | Shows the wrong subset | Content is off by default; it is an exporter | A trace product, with cost and latency | A callback framework | A static map | A results demo (`gemma2:2b`, JSONL, HTML) | The printout |

## Sources

- Local pipeline map, 2026-10-09: `.planning/codebase/ARCHITECTURE.md`; `langextract/extraction.py`, `annotation.py`, `chunking.py`, `prompting.py`, `resolver.py`, `providers/ollama.py`, `core/data.py`, `core/debug_utils.py`; `examples/ollama/demo_ollama.py`. Primary for stage owners and payloads.
- OpenTelemetry GenAI spans, document v1.41.0 (status Development): https://github.com/open-telemetry/semantic-conventions/blob/v1.41.0/docs/gen-ai/gen-ai-spans.md — required operation and provider; model when available; `gen_ai.input.messages` and `gen_ai.output.messages` are Opt-In. Confidence MEDIUM (verified websearch).
- OpenTelemetry Python OpenAI instrumentation: content capture is off unless `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` is set. https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation-genai/openai.html — MEDIUM.
- DSPy `inspect_history` and observability limits: https://dspy.ai/current/api/utils/inspect_history/ and https://dspy.ai/tutorials/observability/ — MEDIUM.
- LangSmith run data format (`prompt` / `llm` / `parser` run types, inputs and outputs): https://docs.langchain.com/langsmith/run-data-format — MEDIUM.
- LlamaIndex `CBEventType.CHUNKING` and `LLM`: https://developers.llamaindex.ai/python/framework-api-reference/callbacks/ — MEDIUM.
- spaCy pipeline analysis is static: https://spacy.io/usage/processing-pipelines/ and https://spacy.io/api/language — MEDIUM.
- LangExtract public surface (grounding, JSONL, HTML; no internal stages): https://github.com/google/langextract/blob/main/README.md — MEDIUM, consistent with the local tree.

**Gaps:** No maintainer interview. Instructor and Guardrails traces were left out on purpose; they center on repair retries, and this default path does not retry a chunk. How the script reads intermediates out of one `extract()` without editing the library is unresolved here and belongs to architecture research. OpenTelemetry attribute names are still Development status and are not a build target.

---
*Feature research for: developer walkthrough of one source-grounded extract() call*
*Researched: 2026-10-09*

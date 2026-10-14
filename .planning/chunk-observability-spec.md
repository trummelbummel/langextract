# Per-chunk observability for extraction

## Problem

`lx.extract()` splits documents into chunks (`chunking.py:343`) and groups them
into batches of `batch_length`. Each batch goes to `infer()` (`annotation.py:392`),
which sends up to `max_workers` requests in parallel. Nothing is visible per chunk:

- **Latency:** one total, printed only with `debug=True` (`annotation.py:577`). The
  printed chunk count is `len(text) / max_char_buffer`, which is wrong.
- **Parse errors:** `extract()` suppresses them by default (`extraction.py:398`). A
  broken chunk gives a log warning and `[]`, which looks like "nothing found".
- **Model failures:** the first failed request ends the run. No result is kept and
  nothing says which batch failed.
- **Tokens:** every provider receives token counts and drops them. `ScoredOutput`
  (`core/types.py:70`) has only `score` and `output`.

## Spec

`extract(..., on_event=None)`: a callable `Callable[[ExtractionEvent], None]`,
passed through `Annotator.annotate_text` and `annotate_documents`. Events are
frozen dataclasses with a stable `name`.

| Event | Fields |
|---|---|
| `chunk_started` | `document_id`, `chunk_index`, `char_start`, `char_end`, `pass_index`, `batch_index` |
| `chunk_finished` | the fields above + `duration_s`, `num_extractions`, `outcome` (`ok` / `parse_error`), `usage` |
| `parse_failed` | the chunk fields + `error_type`, `message`; emitted even when suppressed |
| `model_call_failed` | `batch_index`, `chunk_indices`, `document_ids`, `provider`, `error_type`, `message` |

`TokenUsage`: `input_tokens`, `output_tokens`, `reasoning_tokens`,
`provider_latency_s`, each `None` when the provider doesn't report it.

Rules:

1. Events are emitted only from the calling thread. Providers return data on
   `ScoredOutput`, so the observer is never called concurrently.
2. `duration_s` is measured in the annotator, so it includes the wait for the
   whole batch: OpenAI and Gemini yield only after all requests finish. Request
   latency comes from `usage.provider_latency_s`.
3. `model_call_failed` is per batch, because the failing chunk is unknown. The
   original exception is re-raised unchanged.
4. `ScoredOutput.usage` is optional and added at the end, so existing providers
   keep working.
5. Exceptions from the observer are caught and logged once per run.
6. Durations use `time.perf_counter()`.

Ready-made: `LoggingObserver(logger=None, level=logging.INFO)`.

Out of scope: cost in currency, per-chunk inference failures (needs an `infer()`
contract change), retry counts, an OpenTelemetry dependency (docs example only).

## Acceptance criteria

1. Input with several chunks and documents, run on a fake model, gives exactly
   one `chunk_started` and one `chunk_finished` per chunk.
2. Chunk indices and character ranges match `ChunkIterator`.
3. Every `duration_s >= 0`.
4. Broken JSON in one chunk gives `parse_failed` and
   `chunk_finished(outcome="parse_error")`, and the other chunks finish `ok`.
   With suppression off, the event is emitted and then `ResolverParsingError` is
   raised.
5. If the model raises, `model_call_failed` is emitted and the same exception
   reaches the caller.
6. An observer that always raises doesn't change the result.
7. With `max_workers > 1` and a provider that uses threads, every event arrives on
   the caller's thread.
8. Without `on_event`, behavior and output don't change.
9. At least one provider fills `usage`.

## Vertical slices

Budget per slice: ≤150 non-test lines, ≤3 source files.

| # | Slice | Files | ACs | Lines |
|---|---|---|---|---|
| 1 | Event types, safe dispatch, `on_event` plumbing, chunk start and finish | new `core/events.py`, `annotation.py`, `extraction.py` | 1, 2, 3, 6, 7, 8 | ~110 |
| 2 | `LoggingObserver` + docs with OpenTelemetry example | `core/events.py`, docs | — | ~40 |
| 3 | Parse failures: resolve without suppression, emit, then apply the user's setting | `annotation.py` | 4 | ~35 |
| 4 | Model call failures: emit, then re-raise | `annotation.py` | 5 | ~30 |
| 5 | `ScoredOutput.usage` + Ollama mapping (`prompt_eval_count`, `eval_count`, `total_duration`) | `core/types.py`, `providers/ollama.py`, `annotation.py` | 9 | ~50 |
| 5b, 5c | OpenAI `response.usage`, Gemini `usage_metadata` | one provider file each | — | ~25 each |

Slice 1 comes first; the others depend only on 1. For 90 minutes: 1 → 3 → 5,
with 2, 4 and 5b/c named as follow-ups.

## Decisions

| Question | Choice |
|---|---|
| Callable or Protocol class? | Callable |
| Is `chunk_index` per document or per run? | Per document, plus `document_id` |
| Does `parse_failed` fire when suppressed? | Yes |
| Where is `on_event` accepted? | `extract()` and `Annotator` |

## Discussion points

- **Stable names:** dashboards and alerts match on them, so fields are only added,
  never renamed.
- **A broken observer must not fail the run:** monitoring must not make extraction
  less reliable.
- **Dashboards and alerts:** p50/p95 `duration_s` per model and `max_char_buffer`;
  tokens per document (cost is calculated outside the library); alerts on the
  parse-failure rate and on `model_call_failed` by `error_type`. Compare batch
  duration with `provider_latency_s` to tune `batch_length` and `max_workers`.

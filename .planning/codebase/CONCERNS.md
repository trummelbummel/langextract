---
last_mapped_commit: a4c0aa4c1be98f441ffc7e1d0f85b1067748e1f3
last_mapped_at: 2026-10-09
---
<!-- refreshed: 2026-10-09 -->

# Codebase Concerns

**Analysis Date:** 2026-10-09

## Tech Debt

**v2.0.0 compatibility surface still on the public import path:**

- Issue: Deprecated modules remain importable and emit `FutureWarning` / `DeprecationWarning`, but new code can still land on the shims. `.pylintrc` disables the `fixme` checker, so the in-source removal markers are invisible to lint.
- Files: `langextract/_compat/README.md`, `langextract/_compat/inference.py`, `langextract/_compat/schema.py`, `langextract/_compat/exceptions.py`, `langextract/_compat/registry.py`, `langextract/inference.py`, `langextract/registry.py`, `langextract/schema.py`, `langextract/exceptions.py`, `langextract/data.py`, `langextract/tokenizer.py`, `langextract/extraction.py`, `langextract/core/format_handler.py`, `langextract/providers/ollama.py`
- Impact: Callers keep compiling against APIs scheduled for removal (`language_model_type`, `gemini_schema`, `structured_output_format`, legacy resolver kwargs, `fuzzy_alignment_algorithm="legacy"`). Wildcard re-exports (`from langextract.core.data import *` in `langextract/data.py` and `langextract/tokenizer.py`) hide the real home of symbols.
- Fix approach: Keep new code on `langextract.core` and `langextract.providers`. Do not add symbols under `langextract/_compat/`. When touching call sites, pass `model` / `config` / `model_id` and a `FormatHandler` instead of legacy resolver kwargs. Track the `TODO(v2.0.0)` in `langextract/extraction.py` and the abstract-class TODO in `langextract/resolver.py` (`AbstractResolver` has a single subclass, `Resolver`) as explicit v2 deletions.

**Two provider discovery systems that do not share state:**

- Issue: Model routing uses the mutable regex registry in `langextract/providers/router.py`, loaded by `load_builtins_once` / `load_plugins_once` in `langextract/providers/__init__.py`. A second, `lru_cache`d map lives in `langextract/plugins.py` (`available_providers`, `get_provider_class`) and is what `langextract/registry.py` forwards to. `factory.create_model` never consults `plugins.py`.
- Files: `langextract/providers/router.py`, `langextract/providers/__init__.py`, `langextract/plugins.py`, `langextract/factory.py`, `langextract/providers/builtin_registry.py`
- Impact: A plugin visible to `lx.plugins.get_provider_class` can be invisible to `lx.extract`, and the reverse. `plugins.py` still contains a Python 3.8/3.9 `entry_points().get` branch even though `requires-python` is `>=3.10`.
- Fix approach: Route every lookup through `router.resolve` / `router.resolve_provider` after `load_plugins_once()`. Delete or thin `langextract/plugins.py` down to a wrapper that calls the router. Drop the pre-3.10 branch.

**`load_builtins_once` is not gated on its flag:**

- Issue: `load_plugins_once` returns early when `_plugins_loaded` is set. `load_builtins_once` always walks `BUILTIN_PROVIDERS` and calls `router.register_lazy`. Dedup in `_add_entry` makes the extra calls harmless, but the flag is only a test latch.
- Files: `langextract/providers/__init__.py`, `langextract/providers/router.py`
- Impact: Every `create_model` call re-registers the same patterns. Tests that flip `_builtins_loaded` without `router.clear()` do not get a clean registry.
- Fix approach: Return immediately when `_builtins_loaded` is true, and clear both the flag and `router.clear()` together in `_reset_for_testing`.

**Gemini and OpenAI inference are copied, not shared:**

- Issue: Both providers carry the same batch-vs-thread-pool-vs-sequential shape. `# pylint: disable=duplicate-code` is set at the top of `langextract/providers/gemini.py`, `langextract/providers/openai.py`, `langextract/providers/ollama.py`, and `langextract/providers/schemas/gemini.py`.
- Files: `langextract/providers/gemini.py` (`infer` around the `ThreadPoolExecutor` block), `langextract/providers/openai.py` (matching `yield [result]` block), `langextract/providers/schemas/gemini.py`, `langextract/providers/schemas/openai.py`
- Impact: Retry, ordering, and error-wrapping fixes have to be applied twice. The OpenAI path already drifts (optional extra, different client).
- Fix approach: Extract the ordered parallel fan-out into a helper next to `langextract/core/base_model.py` and keep provider files to request building plus one-call execution.

**Chunk iterator still carries two sources of text:**

- Issue: `langextract/chunking.py` records `# TODO: Refactor redundancy between document and text` inside `ChunkIterator.__init__`. The iterator accepts `text` or `document`, then writes `tokenized_text` back onto `self.document`.
- Files: `langextract/chunking.py`
- Impact: Callers can pass a string and a `Document` whose `.text` differs. Alignment then uses the tokenized copy while prompts use `chunk_text` derived from that copy, so the original `Document.text` is silently ignored.
- Fix approach: Require a `Document`, tokenize `document.text` once, and stop accepting a parallel `text` argument.

**English-only tokenizer shortcuts:**

- Issue: `langextract/core/tokenizer.py` hard-codes `_KNOWN_ABBREVIATIONS = frozenset({"Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "St."})` with `# TODO: Evaluate removal for large-context use cases`. Fuzzy alignment stems tokens with a trailing-`s` rule in `_normalize_token` in `langextract/resolver.py`.
- Files: `langextract/core/tokenizer.py`, `langextract/resolver.py`
- Impact: Sentence breaks and fuzzy spans are wrong for Japanese and other non-spaced scripts even though `docs/examples/japanese_extraction.md` documents that use case. `UnicodeTokenizer` exists but `extract` defaults to `RegexTokenizer`.
- Fix approach: Pass an explicit tokenizer from `extract` when the caller needs grapheme splitting. Do not stem inside alignment unless the caller opts in.

**Pylint complexity checks are turned off:**

- Issue: `.pylintrc` disables `too-many-locals`, `too-many-branches`, `too-many-statements`, `too-many-arguments`, and `fixme`.
- Files: `.pylintrc`, `langextract/resolver.py` (1414 lines), `langextract/providers/gemini_batch.py` (1048 lines), `langextract/annotation.py` (627 lines), `scripts/create_provider_plugin.py` (1531 lines)
- Impact: The alignment and batch modules keep absorbing branches. `BatchConfig.__post_init__` in `langextract/providers/gemini_batch.py` even repeats the same `timeout > 0` check twice.
- Fix approach: Re-enable `fixme` for `langextract/`. Split `WordAligner` out of `langextract/resolver.py` before adding another alignment algorithm.

**Runtime dependencies that the library does not import:**

- Issue: `pyproject.toml` lists packages with no import under `langextract/`.
- Files: `pyproject.toml`
- Impact: Install size and CVE surface grow for every user. `numpy` appears only in `tests/data_lib_test.py` and `benchmarks/plotting.py`. `python-dotenv` is used by examples, benchmarks, and `tests/test_live_api.py`, not by the library.
- Fix approach: Move unused packages off `project.dependencies`.

| Package | Declared in | Imported by library code |
|---|---|---|
| `aiohttp`, `async_timeout`, `exceptiongroup` | `pyproject.toml` `dependencies` | Not detected |
| `ml-collections` | `pyproject.toml` `dependencies` | Not detected |
| `numpy` | `pyproject.toml` `dependencies` | Not detected |
| `python-dotenv` | `pyproject.toml` `dependencies` | Not detected |
| `pandas` | `pyproject.toml` `dependencies` | `langextract/io.py` CSV path only |
| `google-cloud-storage` | `pyproject.toml` `dependencies` | `langextract/providers/gemini_batch.py` only |

`pandas` and `google-cloud-storage` should be extras (`io` / `vertex-batch`) so the default install stays on `google-genai`, `requests`, `PyYAML`, and `regex`.

## Known Bugs

**Paused Vertex batch jobs are treated as success:**

- Symptoms: `infer_batch` returns as soon as the job state is `JOB_STATE_PAUSED`, then reads whatever JSONL is already in the output prefix. Missing rows become `""`.
- Files: `langextract/providers/gemini_batch.py` (`_TERMINAL_OK` includes `JOB_STATE_PAUSED`; `_poll_completion` returns on that set; `_extract_from_file` pads with `outputs_by_idx.get(i, "")`)
- Trigger: A Vertex batch job pauses (quota, manual pause) before every prompt has an output line.
- Workaround: Leave batch mode off (`batch.enabled` defaults to `False`). Do not add `JOB_STATE_PAUSED` to the success set; keep polling or raise `InferenceRuntimeError`.

**Malformed batch JSONL lines disappear:**

- Symptoms: A line that is not valid JSON is skipped. The prompt index is later filled with an empty string and extraction continues.
- Files: `langextract/providers/gemini_batch.py` (`_parse_batch_line` returns on `json.JSONDecodeError`)
- Trigger: Vertex writes a truncated or non-JSON line into the output object.
- Workaround: Set logging high enough to see `Batch API: Parsed %d results` versus the expected count. Raise on decode errors unless `ignore_item_errors` is true, and do not pad gaps when that flag is false.

**Chunk/output length mismatch is truncated by `zip`:**

- Symptoms: If `language_model.infer` yields fewer scored outputs than prompts in the batch, the extra chunks are never resolved or aligned. No error is raised.
- Files: `langextract/annotation.py` (`for text_chunk, scored_outputs in zip(batch, outputs)`)
- Trigger: A provider returns a short iterator, or an item is dropped inside batch padding.
- Workaround: Compare `len(outputs)` to `len(batch)` and raise `InferenceOutputError` before the loop. The empty-`scored_outputs` check below the zip never sees the dropped tail.

**`pydantic>=1.8.0` does not match the code:**

- Symptoms: Importing prompt loading or Gemini batch fails on Pydantic v1 with `AttributeError: module 'pydantic' has no attribute 'TypeAdapter'` or missing `BaseModel.model_dump`.
- Files: `pyproject.toml` (`pydantic>=1.8.0`), `langextract/prompting.py` (`pydantic.TypeAdapter`), `langextract/providers/gemini_batch.py` (`obj.model_dump(...)`)
- Trigger: An environment that already pins Pydantic 1.x resolves the declared floor.
- Workaround: Pin `pydantic>=2` in `project.dependencies`. `TypeAdapter` and `model_dump` are v2 APIs.

**`visualize` only renders the first JSONL record:**

- Symptoms: A multi-document JSONL file displays `documents[0]` and ignores the rest. There is no warning.
- Files: `langextract/visualization.py` (`annotated_doc = documents[0]`)
- Trigger: `lx.visualize(path)` after `save_annotated_documents` wrote more than one row.
- Workaround: Pass a single `AnnotatedDocument`. Iterate the JSONL in the caller until `visualize` accepts an index or returns one HTML document per row.

## Security Considerations

**`visualize` embeds extraction text in a `<script>` block:**

- Risk: `json.dumps` does not escape `<`. A source span or model string containing `</script>` closes the inline script. `attributesHtml` is passed to `innerHTML`. Attribute values are escaped, but `extraction_text` and `extraction_class` are inserted raw into the JSON object that the page parses.
- Files: `langextract/visualization.py` (`js_data = json.dumps(extraction_data)` then `const extractions = {js_data};`, and `attributesContainer.innerHTML = extraction.attributesHtml`)
- Current mitigation: Source text written into the highlight DOM goes through `html.escape`. Palette colors in `_PALETTE` are fixed hex literals, so the `style` attribute is not attacker-controlled. Attribute keys and values inside `_format_attributes` are escaped.
- Recommendations: Replace `<` with `\u003c` (and `U+2028` / `U+2029`) before splicing JSON into HTML. Prefer `textContent` over `innerHTML` for the attributes panel. Add a regression test in `tests/visualization_test.py` whose extraction text is `</script><script>alert(1)</script>`.

**`fetch_urls=True` is an unfiltered server-side fetch:**

- Risk: `requests.get` follows redirects, has no response-size cap, and `is_url` accepts any IP, including loopback and RFC1918. The unit test `IsUrlTest.test_valid_urls` in `tests/data_lib_test.py` asserts `http://192.168.1.1`, `http://localhost:8080`, and `http://[::1]:8080` are valid.
- Files: `langextract/extraction.py` (`fetch_urls: bool = False`), `langextract/io.py` (`is_url`, `download_text_from_url`)
- Current mitigation: The default is `False`, and the `extract` docstring tells callers this is an SSRF hole. Content-Type mismatches only `print` a warning.
- Recommendations: Keep the default off. If the flag is set, refuse non-global IPs after DNS resolution, disable redirects or re-check each hop, and cap bytes before `b''.join(chunks)`.

**`output_name` is not sanitized:**

- Risk: `output_file = output_dir / output_name` lets `output_name="../outside.jsonl"` write outside `output_dir`.
- Files: `langextract/io.py` (`save_annotated_documents`)
- Current mitigation: The docstring tells hosted callers to reject `..` and absolute paths. The function itself does not.
- Recommendations: Reject names that are absolute or contain `..` before `mkdir`.

**Installed provider plugins outrank built-ins and run at import:**

- Risk: `load_plugins_once` calls `entry_point.load()` for every `langextract.providers` entry point. The default `pattern_priority` is 20, while built-ins in `langextract/providers/patterns.py` use priority 10. `router.resolve` picks the highest priority. A broad plugin pattern such as `.*` captures every `model_id`, including `gemini-*` and `gpt-*`, and the provider class can read `api_key` from kwargs.
- Files: `langextract/providers/__init__.py`, `langextract/providers/router.py`, `langextract/providers/patterns.py`
- Current mitigation: `LANGEXTRACT_DISABLE_PLUGINS=1` skips discovery. Failed plugin imports are logged and skipped, which also hides a broken trusted plugin.
- Recommendations: Default plugin priority below built-in priority (under 10). Document that entry points are trusted code. Keep `LANGEXTRACT_DISABLE_PLUGINS` set in services that only use Gemini, OpenAI, and Ollama.

**One env var is a credential for every cloud provider:**

- Risk: `_kwargs_with_environment_defaults` sends `LANGEXTRACT_API_KEY` to Gemini when `GEMINI_API_KEY` is unset and to OpenAI when `OPENAI_API_KEY` is unset. A Gemini key stored in the shared variable is attached to `gpt-*` requests.
- Files: `langextract/factory.py`
- Current mitigation: Provider-specific variables are checked first. A warning fires only when more than one variable in the same tuple is set.
- Recommendations: Stop falling back to `LANGEXTRACT_API_KEY` for OpenAI. Require `OPENAI_API_KEY` or an explicit `api_key=`.

**Ollama will post the API key to whatever `base_url` the caller supplies:**

- Risk: `OllamaLanguageModel` builds the request URL from `base_url` / `model_url` / `OLLAMA_BASE_URL` and, when `api_key` is set, puts it on `Authorization` (or a caller-chosen header). There is no host allow-list except a warning for localhost.
- Files: `langextract/providers/ollama.py` (`_request_headers`, `_post_ollama_json`)
- Current mitigation: Localhost plus an API key warns. The key is redacted in `__repr__`.
- Recommendations: Treat `base_url` as a trust boundary. Do not forward `LANGEXTRACT_API_KEY` into the Ollama client.

**Gemini batch cache objects are world-writable within the bucket:**

- Risk: Cache blobs live at `cache/{sha256}.json` with no generation precondition. Anyone who can write the bucket can replace a cached completion. `get_multi` returns that text as a model result. `iter_items` lists the entire `cache/` prefix.
- Files: `langextract/providers/gemini_batch.py` (`GCSBatchCache`)
- Current mitigation: The hash covers model id, prompt, schema, and generation config. `enable_caching` must be set explicitly when batch mode is on.
- Recommendations: Use a per-job prefix and `if_generation_match=0` on create so an existing object is not silently overwritten.

**Debug logging redacts only exact parameter names:**

- Risk: `extract(..., debug=True)` calls `configure_debug_logging`, which stays on for the process (`langextract/extraction.py` documents this). `_REDACT_KEYS` matches `api_key` and similar names. A key nested under another name, or sitting inside a prompt string, is logged via `_safe_repr`.
- Files: `langextract/core/debug_utils.py`, `langextract/extraction.py`
- Current mitigation: Known secret parameter names become `<REDACTED>`. Strings are truncated to 500 characters.
- Recommendations: Keep `debug=False` in services. Add tests; `tests/` has no `debug_utils` coverage.

## Performance Bottlenecks

**Fuzzy alignment is quadratic-to-cubic in chunk length:**

- Problem: Every unmatched extraction runs an LCS DP of O(n · m²) time and O(m²) memory against the chunk token sequence. The deprecated `legacy` algorithm slides a window from `len(extraction)` to `len(source)` and runs `difflib.SequenceMatcher` on each window.
- Files: `langextract/resolver.py` (`_best_lcs_spans`, `_fuzzy_align_extraction`)
- Cause: Default `max_char_buffer` is 1000 (`langextract/extraction.py`), but callers raise it for long documents. `extraction_passes > 1` repeats alignment. Fuzzy runs only after exact match fails, yet a single long hallucination still scans the whole chunk.
- Improvement path: Cap fuzzy search to a token window around a cheap anchor (first/last token hit). Keep `fuzzy_alignment_algorithm="lcs"` (do not revive `legacy`). For bulk jobs, set `enable_fuzzy_alignment=False` when exact spans are enough.

**Gemini real-time inference sleeps inside worker threads:**

- Problem: Each worker in `ThreadPoolExecutor` retries with blocking `time.sleep` up to `max_retry_delay`. Default `max_workers` is 10, matching `batch_length`.
- Files: `langextract/providers/gemini.py` (`_process_single_prompt`), `langextract/providers/openai.py` (same fan-out)
- Cause: Retries hold a pool thread. A 429 storm occupies all workers while the next batch waits in `langextract/annotation.py`.
- Improvement path: Bound total in-flight calls separately from retry wait, or use the provider batch path (`langextract/providers/gemini_batch.py`, `langextract/providers/openai_batch.py`) once prompts exceed `batch.threshold` (Gemini default 50).

**Ollama inference is one HTTP call at a time:**

- Problem: `extract` still forwards `max_workers`, but `OllamaLanguageModel.infer` loops prompts sequentially through `_post_ollama_json`.
- Files: `langextract/providers/ollama.py`, `langextract/extraction.py`
- Cause: The parallel pool exists only on Gemini and OpenAI. The `extract` docstring says `max_workers` is "Supported by Gemini models."
- Improvement path: Do not raise `max_workers` expecting Ollama speedup. Add a pool in `OllamaLanguageModel.infer` only if the server is known to handle concurrent requests.

**CSV load materializes the whole file:**

- Problem: `_read_csv` uses `pandas.read_csv` on the full file, then yields rows.
- Files: `langextract/io.py`
- Cause: Pandas is the CSV parser. There is no chunksize.
- Improvement path: Stream with the stdlib `csv` module so `Dataset.load` does not need pandas.

**URL download concatenates the entire body:**

- Problem: `download_text_from_url` appends every chunk to a list and joins once. `Content-Length` is only a progress hint.
- Files: `langextract/io.py`
- Cause: No maximum size.
- Improvement path: Stop after a configured byte limit and raise before decode.

## Fragile Areas

**Process-global provider registry plus `lru_cache`:**

- Files: `langextract/providers/router.py` (`_entries`, `_entry_keys`, `@functools.lru_cache` on `resolve` and `resolve_provider`), `langextract/plugins.py` (`_discovered`, `get_provider_class`)
- Why fragile: `resolve` caches the winning class. `clear()` drops the cache; a later `register` does not. Concurrent `register` and `resolve` mutate `_entries` with no lock. `get_provider_class` caches forever (`maxsize=None`), including the `allow_override` combination first observed.
- Safe modification: Call `router.clear()` and `get_provider_class.cache_clear()` in tests. In production, register every provider before the first `resolve`. Add a lock if plugins can load off the main thread.
- Test coverage: `tests/factory_test.py` and `tests/registry_test.py` restore `_entries` by hand. They do not cover a resolve that happens before `load_plugins_once`.

**Pattern collisions at equal priority:**

- Files: `langextract/providers/patterns.py`, `langextract/providers/router.py`
- Why fragile: Gemini, OpenAI, and Ollama all use priority 10. `resolve` sorts by priority only, so registration order breaks ties. Ollama claims `^gemma`, `^llama`, `^qwen`, `^gpt-oss`, and Hugging Face ids such as `^meta-llama/[Ll]lama`. Those ids never reach a hosted HF provider.
- Safe modification: When adding a pattern, give the more specific provider a higher priority and add a case to `tests/factory_test.py`. Do not reuse `^gpt` or `^gemini`.
- Test coverage: Factory tests cover several explicit overrides. A new family prefix is easy to miss.

**Parse errors are swallowed by default:**

- Files: `langextract/extraction.py` (forces `suppress_parse_errors=True` when the key is absent), `langextract/resolver.py`, `langextract/annotation.py`
- Why fragile: A malformed chunk logs and disappears. The returned `AnnotatedDocument` looks complete.
- Safe modification: For evaluation runs, pass `resolver_params={"suppress_parse_errors": False}` so `ResolverParsingError` fails the document. Change the default only with a migration note; `tests/init_test.py` (`AnnotationSuppressParseErrorsTest`) locks the current default.
- Test coverage: Resolver tests cover both flag values. End-to-end tests often stub a perfect model string.

**Multi-pass merge is first-pass-wins on character overlap:**

- Files: `langextract/annotation.py` (`_merge_non_overlapping_extractions`, `_extractions_overlap`)
- Why fragile: Later passes cannot correct an earlier wrong span that overlaps. Extractions with no `char_interval` are always appended, so unaligned duplicates stack.
- Safe modification: Keep pass 1 as the trusted pass. Drop or separate `alignment_status is None` rows before merge if the caller needs a clean set.
- Test coverage: `tests/annotation_test.py` (`AnnotatorMultiPassTest`).

**Shared Gemini / OpenAI client across worker threads:**

- Files: `langextract/providers/gemini.py`, `langextract/providers/openai.py`, `langextract/providers/schemas/openai.py` (comment that one schema is shared across workers)
- Why fragile: `generate_content` / chat completions run on a pool that shares `self._client`. Schema dicts are copied before publish in the OpenAI schema helper; the client object is not.
- Safe modification: Do not mutate provider config after `infer` starts. Keep `max_workers` modest under retry storms.
- Test coverage: `tests/inference_test.py`, `tests/gemini_retry_test.py` mock the client. They do not stress real client thread safety.

**`Document.document_id` mutates on first read:**

- Files: `langextract/core/data.py` (`Document.document_id` and `AnnotatedDocument.document_id` assign `doc_{uuid.uuid4().hex[:8]}` when unset)
- Why fragile: Reading the property changes equality-relevant state. `with_additional_context` deliberately copies that generated id back onto the original instance (`tests/data_lib_test.py`). Eight hex digits are 32 bits.
- Safe modification: Pass an explicit `document_id` for any corpus you will round-trip. Do not use the generated id as a primary key across processes.
- Test coverage: `tests/data_lib_test.py` (`DocumentWithAdditionalContextTest`). No collision test.

**Highlight nesting depends on span-sort stability:**

- Files: `langextract/visualization.py` (`_build_highlighted_text` sort key)
- Why fragile: Overlapping spans must close and open in a specific order or the HTML nests incorrectly. Equal spans rely on the `(position, tag, length)` tuple.
- Safe modification: Add a fixture with nested and abutting spans in `tests/visualization_test.py` before changing the sort key.
- Test coverage: `tests/visualization_test.py` is 160 lines and does not cover script breakout or nested spans.

## Scaling Limits

**Generated document ids:**

- Current capacity: `uuid4().hex[:8]` in `langextract/core/data.py` is about 4 billion values, but birthday collisions become plausible around tens of thousands of documents in one process.
- Limit: `annotate_documents` groups chunks by `document_id` in `langextract/annotation.py`. A collision merges two documents' extractions.
- Scaling path: Store the full `uuid4().hex` (or require caller-supplied ids) once a job can exceed a few thousand documents.

**In-memory batch and alignment:**

- Current capacity: Default chunk size is 1000 characters and default batch is 10 prompts (`langextract/extraction.py`). Gemini batch allows `max_prompts_per_job` of 20000 (`langextract/providers/gemini_batch.py`).
- Limit: All prompts in a `infer` call are realized as a list before the provider runs. Alignment token lists for a chunk live in memory together with the LCS tables (O(m²) in extraction length). `extraction_passes` repeats that work and the API bill.
- Scaling path: Stream batches, keep `max_char_buffer` near the default, and use Vertex / OpenAI batch for large prompt counts instead of raising `max_workers`.

**GCS batch cache listing:**

- Current capacity: `GCSBatchCache.iter_items` lists every blob under `cache/`.
- Limit: A shared long-lived bucket grows without a per-tenant prefix. Lifecycle uses `retention_days` only when that value is set (`langextract/providers/gemini_batch.py`).
- Scaling path: Prefix caches by project and job, and rely on bucket lifecycle rather than unbounded listing.

**Provider fan-out:**

- Current capacity: Gemini and OpenAI default to 10 workers. Gemini batch file uploads use another pool of 10, chosen to match the default HTTP pool (`langextract/providers/gemini_batch.py`).
- Limit: Raising `max_workers` above the SDK connection pool produces timeouts that then occupy retry slots.
- Scaling path: Raise pool size and `max_workers` together, or switch to the batch API.

## Dependencies at Risk

**`pydantic>=1.8.0`:**

- Risk: v1 does not provide `TypeAdapter` or `model_dump`. v2 is what the code calls.
- Impact: `langextract/prompting.py` and `langextract/providers/gemini_batch.py` fail on import under Pydantic 1.
- Migration plan: Declare `pydantic>=2`.

**`google-genai` and `google-cloud-storage` on the default install:**

- Risk: Both are imported by the Gemini stack (`langextract/providers/gemini.py`, `langextract/providers/gemini_batch.py`). Batch support talks to Vertex job states by enum (`JOB_STATE_SUCCEEDED`, `JOB_STATE_PAUSED`, and the failure set). An SDK rename of those enums breaks import or polling.
- Impact: Every install pulls Vertex client and GCS libraries, including users who only call Ollama.
- Migration plan: Keep `google-genai` as the Gemini extra's hard dependency if you split extras; pin a tested floor (`>=1.39.0` is already declared) and cover enum names in `tests/test_gemini_batch_api.py`.

**`openai` is optional but easy to import by accident:**

- Risk: The OpenAI provider is an entry point (`pyproject.toml` `[project.entry-points."langextract.providers"]`) and a built-in pattern. Import happens at first `gpt-*` resolve.
- Impact: Missing `openai` becomes `InferenceConfigError` at call time, not install time. `langextract/providers/openai_batch.py` depends on the same client.
- Migration plan: Document `pip install langextract[openai]`. Keep the optional extra; do not import `openai` at package import.

**Python floor versus CI:**

- Risk: `requires-python` is `>=3.10` with no upper bound. CI in `.github/workflows/ci.yaml` runs 3.10, 3.11, and 3.12 only. `pytype` is a dev dependency and is not a tox env (`tox.ini`).
- Impact: 3.13+ regressions and type errors ship without a red build.
- Migration plan: Add 3.13 to the matrix before claiming support. Run `pytype` on `langextract/` or drop it from `dev` extras.

**`regex` and `google` style pins:**

- Risk: Tokenization depends on `regex` Unicode properties (`\p{Is_Han}` and friends in `langextract/core/tokenizer.py`). Format checks pin `pyink==24.3.0` and `isort==5.13.2`.
- Impact: A `regex` engine change moves token offsets and therefore every char interval. A floating formatter would fail `format-check` on unrelated edits.
- Migration plan: Keep the formatter pins. Upgrade `regex` only with `tests/tokenizer_test.py` and `tests/fuzzy_alignment_cases_test.py`.

## Missing Critical Features

**No coverage gate:**

- Problem: `pyproject.toml` has pytest options and markers (`live_api`, `vertex_ai`, `requires_pip`, `integration`) but no coverage config or required percentage.
- Blocks: Knowing whether a change in `langextract/resolver.py` or `langextract/providers/gemini_batch.py` dropped a branch.

**Live and plugin tests are optional in CI:**

- Problem: `tox.ini` default commands exclude `live_api`, `requires_pip`, and `integration`. The live job in `.github/workflows/ci.yaml` exits 0 when both `GEMINI_API_KEY` and `OPENAI_API_KEY` are empty. Ollama integration is a separate tox env (`ollama-integration`) and is not in the default matrix. Plugin install tests run only when provider paths change.
- Blocks: Contract drift against Gemini, OpenAI, and a running Ollama server.

**Hosted-provider routing stops at three backends:**

- Problem: Model ids that look like Hugging Face repos (`meta-llama/...`, `Qwen/...`, `mistralai/...`) are registered to Ollama in `langextract/providers/patterns.py`. There is no built-in HTTP provider for other OpenAI-compatible hosts except "pass `ModelConfig` yourself" (`README.md`).
- Blocks: Calling those ids through `model_id=` without a local Ollama server.

**Non-CSV datasets:**

- Problem: `Dataset.load` in `langextract/io.py` raises `NotImplementedError` for anything that does not end in `.csv`.
- Blocks: JSONL or parquet input through the `Dataset` API. JSONL exists only for annotated output (`save_annotated_documents` / `load_annotated_documents_jsonl`).

## Test Coverage Gaps

**`langextract/core/debug_utils.py`:**

- What's not tested: Redaction, truncation, and the one-way `configure_debug_logging` latch. No test file mentions `debug_utils`.
- Files: `langextract/core/debug_utils.py`
- Risk: A refactor logs `api_key` or fails to attach a handler.
- Priority: High

**Visualization security and nesting:**

- What's not tested: Script-breaking strings, nested spans, and multi-document JSONL. `visualize` returning only the first document has no assertion.
- Files: `langextract/visualization.py`, `tests/visualization_test.py`
- Risk: XSS regression or broken highlight HTML ships unnoticed.
- Priority: High

**SSRF and download limits:**

- What's not tested: Redirects, private-IP refusal, and maximum body size. Tests lock in the current permissive `is_url` behavior.
- Files: `langextract/io.py`, `tests/data_lib_test.py` (`IsUrlTest`)
- Risk: Hardening `fetch_urls` will fight existing tests unless those tests are rewritten first.
- Priority: High

**Short `infer` iterators:**

- What's not tested: `zip(batch, outputs)` when the model returns fewer items than the batch.
- Files: `langextract/annotation.py`, `tests/annotation_test.py`
- Risk: Silent chunk loss.
- Priority: High

**Paused batch jobs and bad JSONL lines:**

- What's not tested: `JOB_STATE_PAUSED` as a non-success state, and a JSONL stream containing one invalid line with `ignore_item_errors=False`.
- Files: `langextract/providers/gemini_batch.py`, `tests/test_gemini_batch_api.py`
- Risk: Partial batch output is presented as a full result.
- Priority: High

**Registry cache staleness:**

- What's not tested: `router.resolve` before `load_plugins_once`, then a plugin registration without `cache_clear`.
- Files: `langextract/providers/router.py`, `tests/factory_test.py`
- Risk: Tests pass by resetting globals, production keeps the first winner.
- Priority: Medium

**Pydantic v1 versus v2:**

- What's not tested: The dependency solver is never asked to install `pydantic` 1.x. CI uses whatever pip resolves under `>=1.8.0`, which today is v2.
- Files: `pyproject.toml`, `langextract/prompting.py`
- Risk: The floor stays wrong until someone installs v1.
- Priority: Medium

**Ollama and live API:**

- What's not tested in default CI: `tests/test_ollama_integration.py` (skipped unless Ollama is running) and `tests/test_live_api.py` (skipped without keys, and the workflow treats missing keys as success).
- Files: `tests/test_ollama_integration.py`, `tests/test_live_api.py`, `tox.ini`, `.github/workflows/ci.yaml`
- Risk: Request-body drift against real servers.
- Priority: Medium

**Benchmarks and provider scaffolding:**

- What's not tested: `benchmarks/benchmark.py`, `benchmarks/fuzzy_benchmark.py`, and `benchmarks/plotting.py` are outside `testpaths`. `scripts/create_provider_plugin.py` is covered by `tests/create_provider_plugin_test.py` (2426 lines) but that test is heavy and partly behind the `requires_pip` marker.
- Files: `benchmarks/`, `scripts/create_provider_plugin.py`, `tests/create_provider_plugin_test.py`
- Risk: Alignment performance regressions and plugin-template drift.
- Priority: Low

**Warning hygiene:**

- What's not tested: `tox.ini` sets `PYTHONWARNINGS = ignore` for the default envs. Deprecation warnings from `langextract/schema.py` and `langextract/core/format_handler.py` do not fail the build.
- Files: `tox.ini`
- Risk: v2 removals land on callers who never saw the warnings in CI.
- Priority: Low

---

*Concerns audit: 2026-10-09*

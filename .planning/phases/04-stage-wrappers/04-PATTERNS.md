# Phase 4: Stage wrappers - Pattern Map

**Mapped:** 2026-10-10
**Files analyzed:** 3 modified files (+ 9 new symbols inside them)
**Analogs found:** 3 / 3 files (all symbols have an in-file or in-repo analog; two have only a partial one — see "No Analog Found")

Scope: no `04-CONTEXT.md` exists. File list comes from `04-RESEARCH.md` ("Recommended structure" + size table): everything lands in the existing `scripts/trace_extract.py`, `config.yaml`, `tests/trace_extract_test.py`. Nothing in `langextract/` or `examples/` is touched (CTR-01/CTR-02). All analog paths below are git-tracked (`git ls-files` verified; no `.gsd/` mirrors).

Style that applies to every excerpt: 2-space indent; script uses single quotes, tests use double quotes; `from __future__ import annotations` already in script; reST `:param:` docstrings; Apache header already present.

## File Classification

| New/Modified File / Symbol | Role | Data Flow | Closest Analog | Match Quality |
|----------------------------|------|-----------|----------------|---------------|
| `scripts/trace_extract.py` — `StageRecord` dataclass | model (record) | transform | `ExtractionSnapshot` in same file (lines 144-156) | exact |
| `scripts/trace_extract.py` — `make_chunk_wrapper(sink)` | utility (wrapper factory) | streaming (iterator) | `debug_log_calls` (`langextract/core/debug_utils.py` 105-148) for decorator shape; `ChunkIterator.__next__` for semantics | role-match |
| `scripts/trace_extract.py` — `make_prompt_wrapper(sink)` | utility (wrapper factory) | request-response | `debug_log_calls` | role-match |
| `scripts/trace_extract.py` — `make_model_wrapper(sink)` | utility (wrapper factory) | streaming (generator) | `debug_log_calls` + `OllamaLanguageModel.infer` (generator) | role-match |
| `scripts/trace_extract.py` — `make_parse_wrapper(sink)` | utility (wrapper factory) | request-response / transform | `debug_log_calls` + `snapshot_extractions` | role-match |
| `scripts/trace_extract.py` — `make_align_wrapper(sink)` | utility (wrapper factory) | streaming (generator) | `debug_log_calls` + `snapshot_extractions` | role-match |
| `scripts/trace_extract.py` — empty-parse diagnosis helper | utility | transform | `Resolver.resolve` error branch (`resolver.py` 276-335) | role-match |
| `scripts/trace_extract.py` — `print_stage_records(records, config)` + per-stage blocks | utility (printer) | transform (stdout) | `print_stage_catalog` (130-143) + `print_grounding_pair` / `_print_grounding_lines` (221-287) | exact |
| `scripts/trace_extract.py` — safe raw-text printer | utility | transform | `_format_grounding` (208-219) style (small pure formatter) | partial |
| `config.yaml` — `empty_list_message` (+ small labels) | config | file-I/O | existing keys `empty_parse_message`, `ungrounded_label` in same file | exact |
| `tests/trace_extract_test.py` — wrapper unit tests | test | request-response | `TraceExtractSnapshotTest` in same file (50-235) | exact |
| `tests/trace_extract_test.py` — offline real-`extract` integration test | test | request-response | same class + `mock.patch.object` usage in `tests/test_gemini_batch_api.py` | role-match |

## Pattern Assignments

### `StageRecord` (model, transform) — `scripts/trace_extract.py`

**Analog:** `ExtractionSnapshot` (`scripts/trace_extract.py` lines 144-156) — frozen dataclass of primitives, no live objects.

```144:156:scripts/trace_extract.py
@dataclasses.dataclass(frozen=True)
class ExtractionSnapshot:
  """Field copies of one Extraction, taken at a single pipeline stage."""

  extraction_class: str
  extraction_text: str
  extraction_index: int | None
  group_index: int | None
  attributes: dict[str, Any] | None
  char_interval: tuple[int | None, int | None] | None
  token_interval: tuple[int, int] | None
  alignment_status: str | None
```

**Apply:** `StageRecord(label: str, in_data: dict[str, Any], out_data: dict[str, Any])`, `frozen=True`. Keep `dataclasses` import as-is (already `import dataclasses`). Records hold only primitives and `ExtractionSnapshot`s (enum → `.value`/`str`, tuples not live intervals). The test loader already registers the module in `sys.modules` (needed for `@dataclass` + `from __future__ import annotations`), so no loader change.

**Never-live-objects guard to mirror** (raising `TypeError` on live items), from `_validate_grounding_pair` (lines 253-258):

```python
  for item in (*parse_list, *align_list):
    if not isinstance(item, ExtractionSnapshot):
      raise TypeError(
          'print_grounding_pair needs ExtractionSnapshot items, got '
          f'{type(item).__name__}; live objects are never printed'
      )
```

---

### Wrapper factories — shared shape (utility, all five)

**Analog (shape):** `debug_log_calls` in `langextract/core/debug_utils.py` — decorator that takes the original, returns `wrapper(*args, **kwargs)`, forwards args verbatim, and uses `inspect.signature(fn).bind…` only to *read* arguments.

```83-101:langextract/core/debug_utils.py
def _format_bound_args(
    fn: Callable, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> str:
  """Format function arguments using signature inspection."""
  try:
    sig = inspect.signature(fn)
    bound = sig.bind_partial(*args, **kwargs)
    bound.apply_defaults()
  except Exception:
    # Fallback (no names) if binding fails
    ...
  for name, value in bound.arguments.items():
    if name in ("self", "cls"):
      parts.append(f"{name}=<{type(value).__name__}>")
```

```110-148:langextract/core/debug_utils.py
  @functools.wraps(fn)
  def wrapper(*args, **kwargs):
    logger = _LOG
    if not logger.isEnabledFor(logging.DEBUG):
      return fn(*args, **kwargs)
    ...
    try:
      result = fn(*args, **kwargs)
    except Exception:
      ...
      raise
    ...
    return result

  return wrapper
```

**Copy:** `@functools.wraps(original)` on the replacement; always forward the **original** `*args, **kwargs` to `original` (never the bound copy); exceptions propagate (`raise`/no catch around the original). **Differ:** `debug_log_calls` is `fn -> wrapper`; Phase 4 factories are `make_X_wrapper(sink) -> (original -> replacement)` so the default `lambda original: original` is Phase 3's identity passthrough (A1). Replacement signature is always `(self, *args, **kwargs)` (RESEARCH Pattern 1). Wrapper factories must **not** import `langextract` (Pitfall 10 / Phase 2 "no import" criterion) — they receive `original` as an argument. Add `import functools` and `import inspect` to the script's stdlib import block (alphabetical per existing order: `from collections.abc …`, `import dataclasses`, then `import functools`, `import inspect`, `from pathlib import Path`, …).

**Call shapes the wrappers must tolerate** (annotation.py, verified):

```370:373:langextract/annotation.py
        prompts = [
            prompt_builder.build_prompt(
                chunk.chunk_text, chunk.document_id, chunk.additional_context
            )
```
```392:392:langextract/annotation.py
        outputs = self._language_model.infer(batch_prompts=prompts, **kwargs)
```
```406:410:langextract/annotation.py
          resolved_extractions = resolver.resolve(
              scored_outputs[0].output,
              debug=debug,
              suppress_parse_errors=suppress_parse_errors,
              **kwargs,
```
```424:431:langextract/annotation.py
          aligned_extractions = resolver.align(
              resolved_extractions,
              text_chunk.chunk_text,
              token_offset,
              char_offset,
              tokenizer_inst=tokenizer,
              **kwargs,
          )
```

(`kwargs` carries `max_workers`; `batch_prompts` is keyword-only at the call site; `infer`'s outputs are `list()`ed by the Annotator.)

---

### `make_chunk_wrapper` (utility, streaming iterator) — target `ChunkIterator.__iter__`

**Analog (semantics):** `ChunkIterator.__iter__` / `__next__` — `__iter__` is NOT a generator.

```422:423:langextract/chunking.py
  def __iter__(self) -> Iterator[TextChunk]:
    return self
```
```441:442:langextract/chunking.py
  def __next__(self) -> TextChunk:
    sentence = next(self.sentence_iter)
```

**Core pattern** (RESEARCH Pattern 2, verified offline; do NOT use `for c in original(self)` / `yield from` — `RecursionError`):

```python
def make_chunk_wrapper(sink):
  def wrap(original):
    @functools.wraps(original)
    def traced_iter(self):
      it = original(self)            # returns self for ChunkIterator
      while True:
        try:
          chunk = next(it)           # next(), never `for ... in it`
        except StopIteration:
          return                     # PEP 479
        sink.append(StageRecord('chunk', {...}, {...}))   # primitives only
        yield chunk                  # same TextChunk object
    return traced_iter
  return wrap
```

`in`: `self.max_char_buffer`, `self.tokenized_text.text`. `out` per chunk: `chunk.chunk_text`, `(chunk.char_interval.start_pos, .end_pos)`, `(chunk.token_interval.start_index, .end_index)`, `chunk.document_id`.

---

### `make_prompt_wrapper` (utility, request-response) — target `ContextAwarePromptBuilder.build_prompt`

**Analog:** `debug_log_calls` wrapper body (call once, capture result, return it unchanged).

**Core pattern:** `bound = inspect.signature(original).bind(self, *args, **kwargs); bound.apply_defaults()` → read `chunk_text`, `document_id`, `additional_context`; `prompt = original(self, *args, **kwargs)` **exactly once** (it calls `self._update_state`); `sink.append(StageRecord('prompt', {...}, {'prompt': prompt}))`; `return prompt`. Add `context_window_chars` from `getattr(self, '_context_window_chars', None)` only if the attribute exists (read, don't assume). Do not read `self._generator.template` here (A4: `prompt-template` live data is Phase 5).

---

### `make_model_wrapper` (utility, streaming generator) — target `OllamaLanguageModel.infer`

**Analog (semantics):** `OllamaLanguageModel.infer` is a generator yielding one list per prompt.

```266:268:langextract/providers/ollama.py
  def infer(
      self, batch_prompts: Sequence[str], **kwargs
  ) -> Iterator[Sequence[core_types.ScoredOutput]]:
```
```310:310:langextract/providers/ollama.py
        yield [core_types.ScoredOutput(score=1.0, output=output)]
```

**Core pattern** (RESEARCH Pattern 3): outer function (not a generator) records `in` at call time and returns an inner generator that yields the *same* items:

```python
def traced_infer(self, *args, **kwargs):
  bound = inspect.signature(original).bind(self, *args, **kwargs)
  prompts = tuple(bound.arguments['batch_prompts'])
  in_data = {'batch_prompts': prompts, 'kwargs': redact(extra_kwargs, keys)}
  def gen():
    for item in original(self, *args, **kwargs):   # lazy; never list()
      sink.append(StageRecord('model', in_data,
                  {'outputs': tuple((s.score, s.output) for s in item)}))
      yield item                                    # SAME list object
  return gen()
```

**Redaction** — reuse the existing helper, pass `keys` explicitly (default re-reads `config.yaml` per call):

```79:98:scripts/trace_extract.py
def redact(
    mapping: Mapping[str, Any],
    keys: Iterable[str] | None = None,
) -> dict[str, Any]:
  ...
  if keys is None:
    keys = load_config(_CONFIG_PATH)['redact_keys']
  key_set = {k.lower() for k in keys}
```

**Error handling:** do not catch `InferenceRuntimeError`/`InferenceOutputError`; Ollama failures must propagate. `out` contains raw text only — parsed extractions never appear under `model` (STG-04).

---

### `make_parse_wrapper` (utility, transform) — target `Resolver.resolve`

**Analog:** `snapshot_extractions` (script 190-198) + the Phase 2 test that snapshots `resolve` output before `align` mutates it (`tests/trace_extract_test.py` 66-88).

```190:198:scripts/trace_extract.py
def snapshot_extractions(
    extractions: Iterable[Any],
) -> tuple[ExtractionSnapshot, ...]:
  """Snapshot extractions in order, before later stages mutate them.
  ...
  """
  return tuple(_snapshot_extraction(e) for e in extractions)
```

**Core pattern** (RESEARCH Pattern 4): `out = original(self, *args, **kwargs)`; `raw = args[0] if args else kwargs['input_text']`; flags from the Resolver instance, **not** from `extract` arguments:

```python
fh = getattr(self, 'format_handler', None)
flags = {name: getattr(fh, name, None) for name in
         ('format_type', 'use_fences', 'strict_fences', 'use_wrapper', 'wrapper_key')}
# format_type is an enum → store .value; records hold primitives
sink.append(StageRecord('parse', {'raw_model_text': raw, 'flags': flags,
                                  'suppress_parse_errors': kwargs.get('suppress_parse_errors')},
                        {'extractions': snapshot_extractions(out)}))   # BEFORE return
return out                                                              # original objects, untouched
```

Library behaviour to respect (`resolver.py` 276-335): returns `[]` on `FormatError`/`ValueError` when `suppress_parse_errors`, and fresh `Extraction`s on each call. Handler flag source: `langextract/core/format_handler.py` 111-121 (attrs) and `OLLAMA_FORMAT_HANDLER` (`providers/ollama.py` 133-139).

**Empty-parse diagnosis** (no direct analog; RESEARCH Pattern 5): when `out` is empty, call the **original** `resolve` again with `suppress_parse_errors=False` inside `try/except Exception as e`; no error ⇒ valid empty list (`empty_list_message`), error ⇒ `empty_parse_message` + `str(e)`. Build the retry kwargs as `{**kwargs, 'suppress_parse_errors': False}` and forward positional `args` unchanged. Error branch to mirror:

```310:330:langextract/resolver.py
      if suppress_parse_errors:
        ...
        return []
      raise
```
(see lines 310-330: both `FormatError` and `ValueError` branches return `[]` only when suppressed.)

---

### `make_align_wrapper` (utility, streaming generator) — target `Resolver.align`

**Analog (semantics):** `Resolver.align` — generator, early bare `return` on empty, `char_offset or 0`, aligner runs fully on first `next()`.

```377:384:langextract/resolver.py
    if not extractions:
      logging.debug(
          "No extractions found in the annotated text; exiting alignment"
          " process."
      )
      return
```
```392:392:langextract/resolver.py
        char_offset or 0,
```
```405:408:langextract/resolver.py
    for extraction in itertools.chain(*aligned_yaml_extractions):
      logging.debug("Yielding aligned extraction: %s", extraction)
      yield extraction
```

**Core pattern** (RESEARCH Pattern 6): outer function binds args (`b.apply_defaults()`), returns a generator that collects yielded items and snapshots in `finally` so an empty parse still writes an `align` record:

```python
def traced_align(self, *args, **kwargs):
  b = inspect.signature(original).bind(self, *args, **kwargs); b.apply_defaults()
  src, tok_off, chr_off = (b.arguments['source_text'],
                           b.arguments['token_offset'], b.arguments['char_offset'])
  in_data = {'source_text': src, 'token_offset': tok_off,
             'char_offset': chr_off or 0,            # print 0, not None
             'n_extractions': len(b.arguments['extractions'])}
  def gen():
    seen = []
    try:
      for e in original(self, *args, **kwargs):
        seen.append(e)
        yield e                                      # same object the aligner mutated
    finally:
      sink.append(StageRecord('align', in_data, {'extractions': snapshot_extractions(seen)}))
  return gen()
```

**Source slice** (STG-06, Pitfall 7): spans are document coordinates → `source_text[start - char_offset : end - char_offset]`; `char_interval is None` ⇒ `config['ungrounded_label']`. Test evidence: `align(…, 5, 100)` → `CharInterval(118, 126)`, `chunk[18:26] == 'headache'`.

---

### `print_stage_records` + per-stage blocks (utility, stdout transform)

**Analog 1:** `print_stage_catalog` — header form is locked (Phase 1 D-05): `[label] function — path`, blank line between stages.

```135:143:scripts/trace_extract.py
def print_stage_catalog() -> None:
  """Print seven stage headers (and align helper) with blank-line gaps."""
  for i, (label, function_name, path) in enumerate(STAGE_CATALOG):
    if i:
      print()
    print(f'[{label}] {function_name} — {path}')
    if label == 'align':
      print('helper: WordAligner.align_extractions')
```

**Analog 2:** `print_grounding_pair` → `_print_grounding_lines` (validate first, then print, so a failure prints nothing; thin public function delegating to private helpers):

```221:243:scripts/trace_extract.py
def print_grounding_pair(
    parse_snapshots: Iterable[ExtractionSnapshot],
    align_snapshots: Iterable[ExtractionSnapshot],
    ungrounded_label: str,
) -> None:
  ...
  parse_list = list(parse_snapshots)
  align_list = list(align_snapshots)
  _validate_grounding_pair(parse_list, align_list)
  _print_grounding_lines(parse_list, align_list, ungrounded_label)
```
```271:287:scripts/trace_extract.py
  pairs = list(zip(parse_list, align_list))
  print(f'grounding pair (parse → align): {len(pairs)} extractions')
  if not pairs:
    print('    parse: []')
    print('    align: []')
  for i, (parse, align) in enumerate(pairs, start=1):
    print(
        f'  [{i}] {parse.extraction_class}: {parse.extraction_text!r}'
        f'  index={parse.extraction_index}'
    )
    print(f'    parse: {_format_grounding(parse)}')
    print(f'    align: {_format_grounding(align, ungrounded_label)}')
```

**Apply:**
- Group records by `label`, iterate in `STAGE_CATALOG` order, print the existing header, then `in:` / `out:` blocks via `textwrap.indent(pprint.pformat(...))` (add `import pprint`, `import textwrap`).
- For `parse` + `align` call `print_grounding_pair(parse_rec.out['extractions'], align_rec.out['extractions'], config['ungrounded_label'])` — do not write a new pair printer. Print the align `char_offset` / `token_offset` lines (even when `0`) and the per-extraction slice/`ungrounded` next to it; format intervals with the existing `_format_interval` (200-205).
- Model block prints raw text only; parse block prints parsed snapshots + callout (STG-04/STG-09). Collect-then-print in the caller's `finally` (Pattern 8); wrappers never print.
- `main()` stays unchanged in Phase 4 (Phase 5 wires the real call); current `main()`:

```290:297:scripts/trace_extract.py
def main() -> int:
  """Print the call header and stage catalog.
  ...
  config = load_config(_CONFIG_PATH)
  print_call_header(config)
  print_stage_catalog()
  return 0
```

**Safe raw-text helper** (Pitfall 9, ≈4 lines; analog is only the small-pure-formatter style of `_format_interval`/`_format_grounding`): escape non-printable chars except `\n`/`\t`, e.g. `''.join(c if c in '\n\t' or c.isprintable() else repr(c)[1:-1] for c in text)`. Name with leading underscore.

---

### `config.yaml` (config, file-I/O)

**Analog:** existing keys in the same file — messages and labels live in config (Phase 1 D-10/D-13), folded `>` scalars for sentences.

```
# Stored for later phases; not printed in Phase 1
empty_parse_message: >
  Chunk omitted on parse or schema error; raw model text is kept above.

# Align-side marker for extractions Resolver.align could not ground
ungrounded_label: ungrounded
```

**Apply:** add `empty_list_message: >` (valid empty list — nothing omitted) beside `empty_parse_message`, same style. Add any small display labels (e.g. offset caption "chunk start in the document") here, not as Python literals. Keep `redact_keys` unchanged; the "Stored for later phases; not printed in Phase 1" comment may stay (no reformatting of unrelated lines). Test that reads config keys: `test_ungrounded_label_comes_from_config` (tests 199-201).

---

### `tests/trace_extract_test.py` (test, request-response)

**Analog:** `TraceExtractSnapshotTest` — absltest class, module loader, shared canned constants.

**Loader / imports / constants (reuse, do not redefine):**

```25:48:tests/trace_extract_test.py
from absl.testing import absltest

from langextract import data
from langextract import resolver
from langextract.providers import ollama

_SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "scripts"
    / "trace_extract.py"
)
_SOURCE_TEXT = "Patient reports a headache since Monday."
_CANNED = (
    '{"extractions": [{"symptom": "headache"}, {"symptom": "purple elephant"}]}'
)


def _load_script_module():
  """Loads scripts/trace_extract.py as a module."""
  spec = importlib.util.spec_from_file_location("trace_extract", _SCRIPT_PATH)
  module = importlib.util.module_from_spec(spec)
  # dataclasses resolves string annotations through sys.modules.
  sys.modules[spec.name] = module
  spec.loader.exec_module(module)
  return module
```

**setUp + real-resolver fixture pattern** (lines 52-64) — real `Resolver(format_handler=ollama.OLLAMA_FORMAT_HANDLER)`, real `resolve`, real `align`; no fakes for the library:

```52:64:tests/trace_extract_test.py
  def setUp(self):
    super().setUp()
    self.trace = _load_script_module()
    self.resolver = resolver.Resolver(
        format_handler=ollama.OLLAMA_FORMAT_HANDLER
    )
    self.resolved = self.resolver.resolve(_CANNED, suppress_parse_errors=True)

  def _align(self):
    return list(
        self.resolver.align(
            self.resolved, _SOURCE_TEXT, token_offset=0, char_offset=0
        )
    )
```

**Stdout capture pattern** (lines 106-110) for printer tests:

```106:110:tests/trace_extract_test.py
  def _print_pair(self, parse, align):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      self.trace.print_grounding_pair(parse, align, "ungrounded")
    return buf.getvalue().splitlines()
```

**Empty-parse + assertion style to extend** (lines 112-124): `self.resolver.resolve("not json", suppress_parse_errors=True)` → `[]`; assert on `lines[0]` / `any(ln.endswith(...))`.

**Patching rule (Pitfall 8):** never assign class attributes in test bodies. Use `mock.patch.object(cls, name, wrapper(original))` as a context manager or `self.enter_context(...)` (absltest `TestCase.enter_context`), as in the repo's convention:

```994:998:tests/test_gemini_batch_api.py
        mock.patch.object(gb, "_submit_file", autospec=True)
    ...
    self.enter_context(mock.patch.object(gb, "_poll_completion", autospec=True))
```

Add `from unittest import mock` and `import langextract as lx` to the test imports (existing imports: `contextlib, importlib.util, io, pathlib, sys`, then absl, then `langextract` imports — keep that grouping). Add `from langextract import chunking` / `prompting` only if needed for the per-wrapper unit tests.

**New tests to model on RESEARCH "Test Strategy":**
- Unit (per wrapper): patch one class attribute with `make_X_wrapper(sink)(original)`; drive the real object; assert record fields and that yielded/returned objects are the *same* (`assertIs`).
- Chunk: assert no `RecursionError`, same `TextChunk`s, and `ChunkIterator.__iter__` is the original after the `with` block.
- Align: reuse `self.resolved` + `_SOURCE_TEXT`; offsets `0/0`, `[18, 26)`, `match_exact`, slice `'headache'`, ungrounded entry; non-zero-offset case via direct `Resolver.align(…, 5, 100)`.
- Parse (STG-09): `"not json"` → empty + error callout + flags; `'{"extractions": []}'` → valid-empty message; fenced reply with `use_fences=False` visible in `in`.
- Integration (STG-03): real `lx.extract(model_id="gemma3:4b", …, resolver_params={"format_handler": ollama.OLLAMA_FORMAT_HANDLER}, extraction_passes=1, show_progress=False)` with only `ollama.OllamaLanguageModel._ollama_query` patched to return `{"response": _CANNED}`; wrap all five targets via stacked `mock.patch.object`; assert all five labels present, prompt record string == `infer` `batch_prompts[0]`, exactly one fake HTTP call. The `_ollama_query` patch lives in the test only.
- Run: `.venv/bin/python -m pytest tests/trace_extract_test.py -q` (bare `python` lacks PyYAML).

## Shared Patterns

### Primitives-only records / snapshot-before-mutation
**Source:** `scripts/trace_extract.py` lines 144-198 (`ExtractionSnapshot`, `_copy_attributes`, `snapshot_extractions`)
**Apply to:** every wrapper that stores extractions (parse at return, align at exhaustion); `StageRecord` fields
- Snapshot parse **at `resolve` return** and align **at generator exhaustion**; `Resolver.align` mutates parse's objects in place. Never store live `Extraction`s, `TextChunk`s, enums, or `ScoredOutput`s.

### Forward-verbatim, read-by-bind
**Source:** `langextract/core/debug_utils.py` 83-148 (`_format_bound_args`, `debug_log_calls`)
**Apply to:** all five factories
- `inspect.signature(original).bind(self, *args, **kwargs)` for reading only; forward original `*args, **kwargs`; never swallow exceptions from the original; `functools.wraps`.

### Generator transparency
**Source:** `OllamaLanguageModel.infer` (`ollama.py` 266-310) and `Resolver.align` (`resolver.py` 337-408) as the things being wrapped
**Apply to:** model, align, chunk
- Lazy consumption, same items out, no `list()`. Outer non-generator function for model/align so `in` is captured at call time; chunk wrapper is a generator driven by `next(it)`.

### Redaction of printed kwargs
**Source:** `scripts/trace_extract.py` lines 79-111 (`redact`, `_redact_flat`), keys in `config.yaml` `redact_keys`
**Apply to:** model `in` kwargs (and any record that stores forwarded kwargs)
- `redact(kwargs, keys=config['redact_keys'])` before storing in the record.

### Config-resident messages and labels (D-10)
**Source:** `config.yaml` (`empty_parse_message`, `ungrounded_label`); `load_config` (script 54-72)
**Apply to:** callouts, labels, offset captions
- No message literals in Python; printers take `config: Mapping[str, Any]` (like `print_call_header(config)`) and read keys with `config[...]`.

### Collect-then-print, caller-owned sink
**Source:** `print_grounding_pair` (needs both snapshots) and RESEARCH Pattern 8
**Apply to:** all wrappers + `print_stage_records`
- Wrappers only `sink.append(StageRecord(...))`; printing happens afterwards in the caller's `finally`; no global state.

## No Analog Found

| File / concern | Role | Data Flow | Reason |
|----------------|------|-----------|--------|
| Class-attribute install/restore (`trace_probes`) | utility | context manager | Phase 3 owns it; not built yet (only `03-DISCUSS-CHECKPOINT.json` exists). Phase 4 supplies `original -> replacement` callables; tests use `mock.patch.object`. Phase 4 integration through `trace_probes` (04-03 task 3) is blocked on Phase 3. |
| Chunk wrapper for non-generator `__iter__` | utility | streaming | No repo precedent; use RESEARCH Pattern 2 (`next(it)` loop), verified offline. The older `.planning/research/ARCHITECTURE.md` Pattern 1 (`for chunk in original(self)`) is **wrong** (RecursionError) — do not copy it. |
| Empty-parse disambiguation (re-run original `resolve` with `suppress_parse_errors=False`) | utility | transform | No analog; only the `resolve` error branch to understand behaviour. Planner decision A3 (truthful two-message callout vs. always `empty_parse_message`). |
| Safe raw-model-text printer (control-char escaping) | utility | transform | No existing escaper in repo; ≈4-line helper per RESEARCH Pitfall 9. |
| Offline real-`lx.extract` with `_ollama_query` patched | test | request-response | Existing tests call `Resolver` directly; no repo test runs real `lx.extract` with a patched provider query. Use RESEARCH Pattern 7 (verified); `mock.patch.object` + `enter_context` style from `tests/test_gemini_batch_api.py`. |

## Planning Notes (for the planner)

- Diff budget (CLAUDE.md): ≤ ~150 non-test lines / ≤ 3 source files per task, ≤ ~400 per plan. RESEARCH split: 04-01 chunk/prompt/model (~95), 04-02 parse/diagnosis/align (~95, touches script + `config.yaml`), 04-03 printers (~95 + end-to-end test). Every task touches only `scripts/trace_extract.py` (+ `config.yaml` once) plus tests.
- Imports to add to the script (no `langextract` import): `functools`, `inspect`, `pprint`, `textwrap`. Existing script has `# no langextract import` as a Phase 2 acceptance criterion; keep it.
- Existing tests (11) must still pass; `main()` stdout unchanged (no `grounding pair` in catalog output).
- Test runs: `.venv/bin/python -m pytest tests/trace_extract_test.py -q`.

## Metadata

**Analog search scope:** `scripts/`, `tests/trace_extract_test.py`, `tests/test_gemini_batch_api.py` (patch idiom), `config.yaml`, `langextract/core/debug_utils.py`, `langextract/{annotation,chunking,resolver,prompting}.py`, `langextract/providers/ollama.py`, `langextract/core/format_handler.py`, Phase 1/2/3 planning artifacts
**Files scanned:** ~14 (repo-wide grep for `functools.wraps` / `inspect.signature` / `patch.object` as wrapper-pattern searches)
**Pattern extraction date:** 2026-10-10
**Tracked-source gate:** all analog paths confirmed with `git ls-files`

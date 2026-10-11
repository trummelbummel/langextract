---
phase: 04-stage-wrappers
reviewed: 2026-10-11T06:10:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - scripts/trace_extract.py
  - config.yaml
  - tests/trace_extract_test.py
findings:
  critical: 0
  warning: 5
  info: 6
  total: 11
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-10-11T06:10:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the five stage wrappers (`chunk`, `prompt`, `model`, `parse`, `align`), `print_stage_records` and its helpers, the two new `config.yaml` keys, and `tests/trace_extract_test.py`. I read all three PLAN.md and SUMMARY.md files first. `pytest tests/trace_extract_test.py` gives 39 passed, and catalog-only `python scripts/trace_extract.py` is unchanged.

The wrappers are transparent. They yield the same objects lazily, and I found no recursion or double-call problems. No secrets, `eval` or unsafe deserialization were found. The remaining defects are in the printer and in the diagnosis logic. I reproduced each one with a script run against the real `Resolver`.

- **Output spoofing:** the threat model claims T-04-09 and T-04-05 are mitigated, but model-controlled text can still start fake stage headers at column 0.
- **Empty values:** an empty extraction tuple prints as a bare `extractions:` line, which hides the "explicit empty" intent.
- **Misleading callout:** `{"extractions": [{}]}` is described as "a valid empty extraction list; nothing was omitted".

**CLAUDE.md / diff budget:** compliant. Non-test lines per commit are 125, 82, 51, 40, and 97, all at or under 150, with at most 2 source files each. Per plan they are 207, 91 and 97, all under 400. Plan 04-01 ran about 55% over its own task estimates, but stayed inside the hard budget. Tests use `absltest`/`parameterized` fixtures (`enter_context`, `named_parameters`) and never touch the network.

## Warnings

### WR-01: Model-controlled text can inject fake stage headers into printed output

**File:** `scripts/trace_extract.py:499-503` (also `:461`)
**Issue:** `_safe_text` deliberately keeps `\n`. `_print_block` indents it, but `_print_align_section` does not. It interpolates `_safe_text(snap.extraction_class)` raw into the `[i] class: 'text'` line. The extraction class is a JSON key from the untrusted model reply, so a key such as `"x\n[model] FAKE — evil"` produces output like this:

```
  [1] x
[model] FAKE — evil: 'headache'  span=[14, 22)  ...
```

The same unindented text also reaches `print_grounding_pair`, which is Phase 2 code. The `callout:` block at line 461 has the same shape: `\n  error: {_safe_text(parse_error)}` is unindented, so any parser error that echoes model text across several lines can break the layout. I reproduced the align case. The threat model rows T-04-05 and T-04-09 list this boundary as "mitigated", but the tests only check control characters such as ESC.
**Fix:** Format model-derived inline text with `repr` so newlines become `\n`. For the multi-line error, indent the continuation lines.

```python
f'  [{i}] {_safe_text(snap.extraction_class)!r}: '
...
return f'callout: {message}\n' + textwrap.indent(
    f'error: {_safe_text(parse_error)}', '  '
)
```

Add a regression test with a class name containing `\n[model] `. Assert that no printed line other than the real headers starts with `[`.

### WR-02: Empty tuple or list prints as a bare `key:` line instead of an explicit empty value

**File:** `scripts/trace_extract.py:445-451`
**Issue:** The branch `isinstance(value, (list, tuple)) and all(isinstance(v, str) and v for v in value)` is vacuously true for `()` and `[]`. An empty parse therefore prints:

```
out:
  extractions:
  parse_error: None
```

I reproduced this. This is the case plan 04-01 and STG-04 say must be explicit ("an empty value never a missing line"). A reader cannot tell it from a truncated print. It also affects `batch_prompts=()`.
**Fix:** Require a non-empty sequence for the per-item-block branch so empties fall through to `pformat`:

```python
elif (
    isinstance(value, (list, tuple))
    and value
    and all(isinstance(v, str) and v for v in value)
):
```

Add a test that an empty parse prints `extractions: ()`.

### WR-03: "Valid empty list; nothing was omitted" callout is false for non-empty lists whose items yield nothing

**File:** `scripts/trace_extract.py:362-366`, `:457-459`
**Issue:** The diagnosis rule is "strict re-run does not raise, so the model returned a valid empty list". `{"extractions": [{}]}` (a non-empty list holding one empty item) also returns `[]` without raising. I reproduced it, and the printed callout says "Model returned a valid empty extraction list; nothing was omitted." That is wrong: one item was silently dropped. This is the misleading-trace failure that T-04-07 and STG-09 aim to prevent.
**Fix:** Decide the "valid empty list" case from the parsed data instead of from the absence of an exception. Record a third state, for example `parse_error = "no extractable items"` or a separate `callout_kind`. Alternatively, only use `empty_list_message` when the raw payload parsed to an empty list. Add `[{}]` to the matrix test.

### WR-04: Tracing code can change or abort the traced call (non-transparent edge cases)

**File:** `scripts/trace_extract.py:197`, `:398`, `:407-409`
**Issue:** The wrappers run extra code on the real call path, with no guard:
- Line 197: `tuple(bound.arguments['batch_prompts'])` consumes a one-shot iterable before `original` runs. `original` then receives the exhausted generator and silently gets no prompts. `Annotator` passes a list today, but `infer` accepts any `Iterable`.
- Line 398: `len(given['extractions'])` raises `TypeError` for a generator or other unsized iterable, so the tracer breaks `align`.
- Lines 407-409: `snapshot_extractions(seen)` inside `finally` can raise and replace the original exception, for example when a partially built extraction lacks attributes.

A diagnostic tool should not alter or abort what it observes.
**Fix:** Materialize safely and keep the original arguments consistent:

```python
prompts = tuple(bound.arguments['batch_prompts'])
# rebind so the original sees the same data
bound.arguments['batch_prompts'] = prompts
...
'n_extractions': len(given['extractions']) if hasattr(given['extractions'], '__len__') else None,
```

Alternatively, wrap the snapshot in the `finally` block in its own `try/except Exception` that records a placeholder. Either way, add a test with a generator `batch_prompts`.

### WR-05: `prompt_index == 0` does not identify one infer call when a prompt has several scored outputs

**File:** `scripts/trace_extract.py:205-213`
**Issue:** The summary and `04-01-SUMMARY.md` tell Phase 5 to count infer calls as model records with `prompt_index == 0`. `index` here is the position of the yielded item, and one record is appended per `ScoredOutput` inside that item. A provider returning more than one `ScoredOutput` per prompt, which the `Sequence[ScoredOutput]` type allows, produces several records with `prompt_index == 0` within one call. Phase 5's single-inference guard would then over-count and fail falsely. The records of one call share `in_data`, but that is not an explicit key.
**Fix:** Add an explicit per-call marker, for example a `call_id` (counter or `id(in_data)`) and an `output_index`, or use `enumerate` on the scored outputs for a separate field. Document the guard on a field that is exact: count distinct `call_id` values.

## Info

### IN-01: `[align]` record is not written if the generator is never started; early-close timing depends on GC

**File:** `scripts/trace_extract.py:401-410`
**Issue:** The `try/finally` lives inside the generator body. A generator that is never advanced runs no `finally` block, so no record is written. The 04-03 summary says this "covers empty input and early close". It covers empty input (the generator runs and `original` returns). It does not cover the never-started case, and an early close records only when the generator is closed or garbage collected.
**Fix:** Either note the limitation in the docstring, or record the in-data eagerly and update the sink entry later.

### IN-02: Plan 04-03 Task 2 deferred, so there is no installer outside tests

**File:** `scripts/trace_extract.py` (module), `tests/trace_extract_test.py:53-72`
**Issue:** The only code that installs wrappers is `_patch_stages` in the test module. T-04-11 (restoring five class attributes through `trace_probes`) is explicitly unverified, and the plan-level `>= 31 passed` check no longer evidences Task 2. This was documented as a deliberate halt, but Phase 5 must provide the production installer before the stage records are reachable.
**Fix:** Track this as a Phase 3/5 dependency. When `trace_probes` lands, move `_STAGE_TARGETS` out of the test module.

### IN-03: Stale comments and docstrings

**File:** `config.yaml:6`, `scripts/trace_extract.py:16`, `tests/trace_extract_test.py:15`
**Issue:** `config.yaml` still says `empty_parse_message` is "Stored for later phases; not printed in Phase 1", but it is printed now. The script docstring says it prints only "the stage catalog and static call header". The test docstring says "extraction snapshots" only.
**Fix:** Update the three strings.

### IN-04: Multi-line `pformat` continuation lines are not indented

**File:** `scripts/trace_extract.py:453`
**Issue:** `print(f'  {key}: {pprint.pformat(value)}')` indents only the first line. The `flags` dict and the snapshot tuple wrap with continuation lines at column 0 or 1, and the output is hard to scan.
**Fix:** `print(textwrap.indent(f'{key}: {pprint.pformat(value)}', '  '))`.

### IN-05: Repeated records and duplicated error text make multi-chunk output hard to read

**File:** `scripts/trace_extract.py:526-536`
**Issue:** For a label with several records (one per chunk, or per `ScoredOutput`), `in:` and `out:` blocks are printed back to back with no index, and the shared model `in_data` (the full prompt) is repeated for each output. `parse_error` also appears twice for an empty parse, once in the callout and once in the `out:` block.
**Fix:** Print a `#i` marker per record, and omit `parse_error` from `out:` when a callout was printed. Multi-chunk handling is out of scope for v1 (STG-10).

### IN-06: Test style points

**File:** `tests/trace_extract_test.py:603-604`, `:518-540`
**Issue:**
- `[l for l in ...]` uses the ambiguous name `l` (E741).
- `test_parse_callout_follows_raw_text_and_diagnosis` branches on its parameters (`if error is None`, `if error:`, `if "```" in canned`). CLAUDE.md asks for one behavior per test, and conditionals hide which case ran.
- There is no test for multi-record or multi-chunk pairing (index pairing in `print_stage_records`), `batch_size > 1`, or an unstarted/closed align generator.

**Fix:** Rename the variable to `line`. Move the fenced-input flag assertion into its own test, and pass the expected error as an explicit parameter. Add the missing cases.

---

_Reviewed: 2026-10-11T06:10:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

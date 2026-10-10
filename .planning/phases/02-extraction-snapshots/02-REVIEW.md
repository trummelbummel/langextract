---
phase: 02-extraction-snapshots
reviewed: 2026-10-10T17:20:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - scripts/trace_extract.py
  - tests/trace_extract_test.py
  - config.yaml
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: issues
---

# Phase 2: Code Review Report

**Reviewed:** 2026-10-10
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues

## Summary

Reviewed `ExtractionSnapshot`, `snapshot_extractions`, `print_grounding_pair`, the `ungrounded_label` config key, and the tests against the 02-01 and 02-02 plans.

CLAUDE.md and plan constraints hold:

- No top-level `langextract` import in the script. Only the test imports it.
- No `deepcopy` anywhere, and the script never calls `Resolver.align`. Objects handed to align are never copied or replaced.
- Snapshots are field copies. `char_interval` and `token_interval` become tuples, `alignment_status` becomes its `.value` string, and `attributes` is copied one level deep with list values re-listed. I confirmed in code and by running the tests that parse snapshots stay ungrounded after align mutates the live objects.
- Diff budget is respected (about +127 non-test lines across the phase). Nothing under `langextract/` or `examples/` was touched.
- `.venv/bin/python tests/trace_extract_test.py` runs 11 tests, all OK. The catalog output via `.venv/bin/python scripts/trace_extract.py` is unchanged.

There are no Critical issues. The Warnings are about places where the "never print a misleading pair" guarantee (T-02-04, T-02-02) can still be defeated. All three were reproduced with a short script.

## Warnings

### WR-01: `ungrounded_label=None` silently degrades to printing `None`

**File:** `scripts/trace_extract.py:193-203, 208-212`
**Issue:** `_format_grounding` uses `none_label is not None` as its "apply the label" switch. If a caller passes `None`, the align line prints `char_interval=None alignment_status=None`. That is the same text as the parse line, which is the "ungrounded vs not-yet-grounded" ambiguity the phase exists to remove. `print_grounding_pair` declares `ungrounded_label: str` as required but does not enforce it. Phase 4 will pass `load_config(...)['ungrounded_label']`, so a missing or null YAML value would degrade silently. An empty string `''` has the same effect: it prints a blank where the marker should be. Reproduced with `print_grounding_pair(a, a, None)`.
**Fix:** Validate the label once at the top of `print_grounding_pair`, next to the other guards, and make `_format_grounding` take a required label for the align side:
```python
if not isinstance(ungrounded_label, str) or not ungrounded_label:
  raise ValueError('ungrounded_label must be a non-empty string')
```
Then pass `None` from the parse side explicitly, or use a separate `_format_grounding(snap, label=None)` for the parse line.

### WR-02: Pairing guard cannot detect reordered duplicates

**File:** `scripts/trace_extract.py:230-239`
**Issue:** The identity check compares only `(extraction_class, extraction_text)`. For duplicate extractions (the case the plan calls out, e.g. two `pain` entries) a swapped or misordered align tuple passes every guard. The printed pair then attaches `[0,4)` to the extraction at `index=2` and `[10,14)` to the one at `index=1`, which is a plausible-looking but wrong record. Reproduced: parse indices (1, 2) against `reversed(parse)` prints without error. `extraction_index` and `group_index` are already on the snapshot, and `Resolver.align` preserves them, so comparing them costs nothing. Plan 02-02 explicitly states a desync is "a probe bug the developer must see".
**Fix:** Include the indices in the comparison:
```python
key = lambda s: (s.extraction_class, s.extraction_text,
                 s.extraction_index, s.group_index)
if key(parse) != key(align):
  raise ValueError(f'parse/align mismatch at position {i}: ...')
```
Add a test with duplicate class/text and swapped indices.

### WR-03: Script is not runnable under system Python (PyYAML top-level import)

**File:** `scripts/trace_extract.py:32`
**Issue:** The 02-01 plan prohibition states the catalog "must stay runnable under system python without pandas". `import yaml` at module top means `python3 scripts/trace_extract.py` fails with `ModuleNotFoundError: yaml` on a machine without PyYAML. I reproduced this with Homebrew `python3`. The 02-01 SUMMARY records this as a pre-existing Phase 1 environment note and ran the verify commands with `.venv/bin/python` instead. The plan's literal `<verify>` command (bare `python`) therefore fails in this environment and was substituted rather than fixed. This predates Phase 2 but is carried unchanged into it.
**Fix:** Either document `.venv/bin/python` (or `uv run`) as the required interpreter in the module docstring `Usage:` block, or lazy-import `yaml` inside `load_config` with a clear `Error: PyYAML required` message and exit code 1 (matching the existing missing-config handling).

## Info

### IN-01: `ExtractionSnapshot` is `frozen=True` but unhashable and shallowly mutable

**File:** `scripts/trace_extract.py:139-150`
**Issue:** `attributes` is a `dict`, so `hash(snapshot)` raises `TypeError` (reproduced) and `snapshot.attributes['k'] = ...` still mutates a "frozen" record. Nothing hashes snapshots today and the printer does not mutate them, so this is only a latent trap for Phase 4, for example if snapshots are put in a set or used as dict keys.
**Fix:** Pass `eq=True, frozen=True` as-is but add a one-line docstring note, or store `attributes` as a tuple of `(key, tuple|str)` pairs. Only change this if Phase 4 needs hashing.

### IN-02: `_format_grounding` substitutes the label per field, which can mix states

**File:** `scripts/trace_extract.py:199-203`
**Issue:** `char_interval` and `alignment_status` are replaced independently. An extraction with a grounded `char_interval` and a `None` status prints `alignment_status=ungrounded` next to a real span. This cannot happen from `Resolver.align` today because it sets both together, but the label then claims something false.
**Fix:** Apply the label only when `snap.char_interval is None`, or only when both are `None`.

### IN-03: `_snapshot_extraction` assumes `alignment_status` is an enum

**File:** `scripts/trace_extract.py:176`
**Issue:** `status.value` raises `AttributeError` if a value is ever already a plain string, for example when a future caller hand-builds an extraction. This is acceptable for a duck-typed trace helper but gives a poor error.
**Fix:** `getattr(status, 'value', status)`.

### IN-04: Test coverage gaps and `sys.modules` side effect

**File:** `tests/trace_extract_test.py:40-48, 82-85`
**Issue:**
- `token_interval` snapshotting (`(start_index, end_index)`) is never asserted. The align test checks only `char_interval` and `alignment_status`, though `Resolver.align` does set `token_interval`.
- `_load_script_module` registers the module in `sys.modules` on every `setUp` and never removes it. That works, but it leaks into other tests in the same process.
- `test_text_mismatch_names_position` and the plan behavior disagree on the position number (the plan says "position 1", the test checks "position 2"). The test is internally consistent, so this is only a plan/test drift.
**Fix:** Add `self.assertEqual(align[0].token_interval, (...))` to the align test. Use `addCleanup(sys.modules.pop, spec.name, None)` in the loader.

### IN-05: Stale `config.yaml` header and comment

**File:** `config.yaml:1, 5`
**Issue:** The header says "Call constants … (Phase 1)" and the comment says "not printed in Phase 1", but the file now also holds the Phase 2 `ungrounded_label`. `empty_parse_message` remains unused, which is intended per D-13. `ungrounded_label` is read by no production code path yet, only by a test, because `main()` does not call `print_grounding_pair`. That is intended until Phase 4.
**Fix:** Reword the header to "Call and display constants for scripts/trace_extract.py". Optionally add a note that `ungrounded_label` is consumed from Phase 4.

---

_Reviewed: 2026-10-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

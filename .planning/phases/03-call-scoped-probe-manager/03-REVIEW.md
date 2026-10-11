---
phase: 03-call-scoped-probe-manager
reviewed: 2026-10-11T06:51:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - scripts/trace_extract.py
  - tests/trace_extract_test.py
findings:
  critical: 1
  warning: 2
  info: 3
  total: 6
status: issues
---

# Phase 3: Code Review Report

**Reviewed:** 2026-10-11T06:51:00Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues

## Summary

Reviewed `trace_probes()`, identity wrap factories, mid-install rollback, `wrappers=` validation, `_self_check_probe_restore()`, and `TraceExtractProbeTest` against plans 03-01 / 03-02 and CONTEXT D-01..D-16.

The happy paths are solid: five targets install, exception/normal exit restore by identity, unknown wrapper keys raise `ValueError`, self-check is silent on success and exits 1 on failure, and chunk correctly uses return-self (not `yield from`). No secrets, `eval`, or unsafe deserialization in scope. Diff-budget and “no `langextract/` edits” constraints hold.

The phase’s core safety promise (D-13 / T-03-01: never leave a partial monkeypatch) is incomplete: mid-install rollback only catches `Exception`, so `KeyboardInterrupt` during install leaks already-wrapped class attributes. Reproduced. Two further robustness gaps around `_PROBES_ACTIVE` were also reproduced.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Mid-install rollback skips `BaseException` — partial monkeypatch leak

**File:** `scripts/trace_extract.py:532-540`
**Issue:** Install failures are handled with `except Exception:`, then `_restore_probe_attrs(saved)`. `KeyboardInterrupt` and `SystemExit` are `BaseException` subclasses, so they bypass rollback. I reproduced: a `wrappers=` factory that raises `KeyboardInterrupt` on the second label leaves `ChunkIterator.__iter__` still wrapped while `_PROBES_ACTIVE` stays `False`. That directly breaks D-13 / T-03-01 (“never leave a partial monkeypatch”). For `python scripts/trace_extract.py` the process often dies with the interrupt, but `with trace_probes():` is the Phase 5 call-scoped API — a Ctrl-C (or other `BaseException`) during the install loop in a long-lived process leaves langextract class attributes permanently patched with no active-session flag.
**Fix:** Use `except BaseException:` (or a `try`/`finally` around the install loop) so already-applied wraps always restore before the error propagates:

```python
saved: list[tuple[type, str, Callable[..., Any]]] = []
try:
  for label, (cls, attr) in targets.items():
    original = cls.__dict__[attr]
    replacement = factories[label](original)
    saved.append((cls, attr, original))
    setattr(cls, attr, replacement)
except BaseException:
  _restore_probe_attrs(saved)
  _PROBES_ACTIVE = False
  raise
```

Add a regression test that injects `KeyboardInterrupt` from the second factory and asserts all five attrs restore by identity.

## Warnings

### WR-01: `_PROBES_ACTIVE` stays `True` if restore raises

**File:** `scripts/trace_extract.py:543-547` (also mid-install path `:537-540`)
**Issue:** In the post-install `finally`, `_PROBES_ACTIVE = False` runs only after `_restore_probe_attrs(saved)`. If restore raises, the flag remains `True` and every later `trace_probes()` raises `RuntimeError('trace_probes() already active')` for the rest of the process — a sticky denial of the probe API (T-03-02 adjacent). Reproduced by patching `_restore_probe_attrs` to raise.
**Fix:** Always clear the flag:

```python
finally:
  try:
    _restore_probe_attrs(saved)
  finally:
    _PROBES_ACTIVE = False
```

Apply the same nesting on the mid-install failure path.

### WR-02: Re-entry guard is inactive during the install loop

**File:** `scripts/trace_extract.py:517-542`
**Issue:** `_PROBES_ACTIVE` is set only after all five `setattr`s succeed. During install it is still `False`, so a `wrappers=` factory that itself enters `with trace_probes():` is not rejected. Reproduced: a factory for the first label nested `trace_probes()` successfully (`reentered['ok'] is True`). That violates D-14/D-15 for the install window and can interleave two install/restore cycles. Phase 4 will pass real factories here; a buggy factory could stack wraps.
**Fix:** Set `_PROBES_ACTIVE = True` immediately after the re-entry check (before the install loop), and ensure every exit path (mid-install `BaseException`, normal `finally`) clears it. Optionally reject nested entry from factories with the same `already active` error.

## Info

### IN-01: Failure-path self-check test relies on manual attr cleanup

**File:** `tests/trace_extract_test.py:985-1003`
**Issue:** `test_self_check_probe_restore_failure_exits` patches restore to a no-op (intentionally leaking wraps) and restores class attrs with a trailing loop. If that loop is skipped or incomplete after a future edit, later tests in the process see polluted targets. Prefer `self.addCleanup(...)` registered before the patched call so cleanup is tied to the test lifecycle.
**Fix:** `self.addCleanup` for each `(cls, attr, original)` plus `_PROBES_ACTIVE = False` before entering the failing self-check.

### IN-02: Catalog prints before self-check can fail on import

**File:** `scripts/trace_extract.py:818-821`
**Issue:** `main` prints the full catalog, then `_self_check_probe_restore()` lazy-imports langextract. An import/install failure yields exit 1 after stdout already showed a successful-looking catalog. Intentional per D-09 ordering, but easy to misread in CI logs.
**Fix:** No change required for Phase 3; if it confuses operators later, run a cheap `_load_probe_targets()` before printing or prefix the stderr error with “after catalog”.

### IN-03: No regression coverage for `BaseException` mid-install or flag-clear ordering

**File:** `tests/trace_extract_test.py` (probe suite)
**Issue:** Tests cover `Exception` mid-install (`RuntimeError` from a factory) and nested `with` after enter, but not `KeyboardInterrupt` during install, restore raising, or factory re-entry during install — the three gaps above.
**Fix:** Add the three focused absltests once CR-01 / WR-01 / WR-02 are fixed.

---

_Reviewed: 2026-10-11T06:51:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

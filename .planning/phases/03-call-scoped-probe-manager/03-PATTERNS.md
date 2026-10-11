# Phase 3: Call-scoped probe manager - Pattern Map

**Mapped:** 2026-10-11
**Files analyzed:** 1 modified file (+ 5 new symbols inside it)
**Analogs found:** 1 / 1 files (all symbols have an in-repo or in-file analog; one concern has no production CM analog — see "No Analog Found")

Scope: file list from `03-CONTEXT.md` only (RESEARCH.md skipped this plan-phase run). Sole implementation surface is `scripts/trace_extract.py` — `trace_probes()`, `_PROBES_ACTIVE`, identity wraps, in-script restore self-check, and `main` growth. No `langextract/` edits. Phase 3 demo is in-script (D-09); `tests/trace_extract_test.py` is an optional later consumer, not a required deliverable. All analog paths below are git-tracked (`git ls-files` verified; no `.gsd/` mirrors).

Style that applies to every excerpt: 2-space indent; script uses single quotes; `from __future__ import annotations` already present; reST `:param:` docstrings; Apache header already present. Diff budget: ~150 non-test lines / ≤3 source files per task (`CLAUDE.md`).

## File Classification

| New/Modified File / Symbol | Role | Data Flow | Closest Analog | Match Quality |
|----------------------------|------|-----------|----------------|---------------|
| `scripts/trace_extract.py` — `trace_probes(wrappers=None)` | utility (context manager / installer) | request-response (scoped monkeypatch) | `_patch_stages` in `tests/trace_extract_test.py` (install) + ARCHITECTURE Pattern 1 + `factory_test.py` try/finally restore | role-match |
| `scripts/trace_extract.py` — `_PROBES_ACTIVE` | config (module flag) | request-response (re-entry guard) | module-level `_REPO_ROOT` / `_CONFIG_PATH` flags in same file | partial |
| `scripts/trace_extract.py` — identity wraps (default / partial fill) | utility (wrapper factory) | transform / streaming | `make_stage_wrappers` + `lambda original: original` contract (04-RESEARCH); `make_*_wrapper` for call shapes | exact (key/value contract) / role-match (bodies) |
| `scripts/trace_extract.py` — probe target table (class, attr) | config / utility | transform | `_STAGE_TARGETS` in `tests/trace_extract_test.py` | exact |
| `scripts/trace_extract.py` — restore self-check (+ helper) | utility | request-response | `load_config` stderr/`SystemExit(1)` + CONTEXT self-check flow | role-match |
| `scripts/trace_extract.py` — `main()` growth | utility (entrypoint) | request-response | existing `main` (catalog print) | exact |

## Pattern Assignments

### `trace_probes(wrappers=None)` (utility, scoped monkeypatch) — `scripts/trace_extract.py`

**Analog (install targets + wrap application):** `_STAGE_TARGETS` + `_patch_stages` (`tests/trace_extract_test.py` lines 57-72). Production installer must do the same five `(class, attribute)` pairs without `mock.patch` — assign on the class, restore in `finally`.

```57:72:tests/trace_extract_test.py
# Stage label -> (class, attribute) that a stage wrapper replaces.
_STAGE_TARGETS = {
    "chunk": (chunking.ChunkIterator, "__iter__"),
    "prompt": (prompting.ContextAwarePromptBuilder, "build_prompt"),
    "model": (ollama.OllamaLanguageModel, "infer"),
    "parse": (resolver.Resolver, "resolve"),
    "align": (resolver.Resolver, "align"),
}


def _patch_stages(test, wrappers, labels):
  """Installs wrappers[label](original) on each target; restored by cleanup."""
  for label in labels:
    cls, attr = _STAGE_TARGETS[label]
    replacement = wrappers[label](cls.__dict__[attr])
    test.enter_context(mock.patch.object(cls, attr, replacement))
```

**Copy:**
- Keys = catalog labels `chunk` / `prompt` / `model` / `parse` / `align` (matches `make_stage_wrappers` and Phase 4 A1 — Claude's discretion: prefer this over method-reference keys so Phase 4 needs no adapter).
- Values = `original -> replacement` callables; apply as `wrappers[label](cls.__dict__[attr])` then `setattr(cls, attr, replacement)`.
- Read originals from `cls.__dict__[attr]` (or direct class attribute) — never from an instance (bound-method restore pitfall; SUMMARY Pitfall 7 / ARCHITECTURE Pattern 1).

**Analog (save / assign / finally restore shape):** ARCHITECTURE Pattern 1 (research, lines 89-104) — the canonical call-scoped observer. Translate the single-target sketch into a five-target loop inside a context manager.

```python
# From .planning/research/ARCHITECTURE.md Pattern 1 (conceptual)
original = ChunkIterator.__iter__
# ... assign wrap ...
ChunkIterator.__iter__ = _traced_iter
try:
  document = lx.extract(...)  # Phase 3: yield control only; no extract
finally:
  ChunkIterator.__iter__ = original
```

**Analog (try/finally restore discipline in Python tests):** `tests/factory_test.py` lines 490-524 — save module/class state, mutate, restore in `finally` even on exception.

```490:524:tests/factory_test.py
    finally:
      router._entries = original_entries  # pylint: disable=protected-access
      router._entry_keys = original_keys  # pylint: disable=protected-access

  def test_gemini_vertexai_with_credentials(self):
    """Test that Vertex AI credentials can be passed through."""
    original_entries = router._entries.copy()  # pylint: disable=protected-access
    original_keys = router._entry_keys.copy()  # pylint: disable=protected-access

    try:
      # ... mutate router ...
      model = factory.create_model(config)
      self.assertEqual(model.credentials, mock_credentials)
    finally:
      router._entries = original_entries  # pylint: disable=protected-access
      router._entry_keys = original_keys  # pylint: disable=protected-access
```

**Recommended shape (no in-repo `@contextmanager` exists — use stdlib):**

```python
import contextlib
# ...
@contextlib.contextmanager
def trace_probes(wrappers: Mapping[str, Callable] | None = None):
  # 1) reject if _PROBES_ACTIVE (D-14/D-15/D-16)
  # 2) resolve wrappers map → always five labels; missing → identity (D-04/D-08)
  # 3) lazy-import stage classes (keep top-level free of langextract if Phase 2 criterion still valued; Phase 4 wrappers already take original as arg)
  # 4) save originals; install one-by-one; on mid-install failure restore installed then re-raise (D-13)
  # 5) set _PROBES_ACTIVE = True; try: yield; finally: restore all five + clear flag
```

**Do not use `mock.patch` in the script** — tests own that path; production path is direct class-attribute assign.

**Phase 4 hand-off (already landed):** `make_stage_wrappers` returns the exact map Phase 4 will pass:

```418:433:scripts/trace_extract.py
def make_stage_wrappers(
    sink: list[StageRecord], config: Mapping[str, Any]
) -> dict[str, Callable[[Callable[..., Any]], Callable[..., Any]]]:
  """Map catalog labels to original -> replacement wrapper callables.
  ...
  """
  return {
      'chunk': make_chunk_wrapper(sink),
      'prompt': make_prompt_wrapper(sink),
      'model': make_model_wrapper(sink, config['redact_keys']),
      'parse': make_parse_wrapper(sink),
      'align': make_align_wrapper(sink),
  }
```

---

### `_PROBES_ACTIVE` (module flag, re-entry guard)

**Analog (module-level constants):** same file lines 37-39.

```37:39:scripts/trace_extract.py
_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO_ROOT / 'config.yaml'
_REDACTION_TOKEN = '<REDACTED>'
```

**Apply:** `_PROBES_ACTIVE: bool = False` beside those constants. Set `True` only after successful install begins (or at enter after re-entry check — planner choice); clear in the same `finally` that restores class attributes (D-15). Re-entry raises `RuntimeError('trace_probes() already active')` (D-16). No existing `RuntimeError` re-entry guard in `langextract/` — message text is Claude's discretion within that shape.

---

### Identity wraps (utility, transform / streaming)

**Analog (contract):** Phase 4 locked `original -> replacement`; identity default is conceptually `lambda original: original`. **But D-12 requires `is not` against saved originals inside the `with`**, so Phase 3 must install distinct callable objects that behave as identity — not the bare original.

**Analog (call shapes / generator transparency):** existing `make_*_wrapper` bodies in the same file. Phase 3 identity must:
- Call `original(self, *args, **kwargs)` once and return/yield the same objects (D-05).
- **Not** use `@functools.wraps` (D-07) — differ from Phase 4 wrappers which do wrap.
- **Not** append to a sink, print, or count.
- Forward `*args, **kwargs` verbatim (infer/`max_workers`).

**Non-generator identity** (prompt / parse) — mirror structure of `make_prompt_wrapper` / `make_parse_wrapper` without recording:

```280:295:scripts/trace_extract.py
  def wrap(original: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(original)
    def traced_build_prompt(self, *args, **kwargs):
      bound = inspect.signature(original).bind(self, *args, **kwargs)
      bound.apply_defaults()
      prompt = original(self, *args, **kwargs)
      ...
      return prompt

    return traced_build_prompt
```

Phase 3 strip to:

```python
def wrap(original):
  def identity(self, *args, **kwargs):
    return original(self, *args, **kwargs)
  return identity
```

**Generator identity** (model / align) — mirror `make_model_wrapper` / `make_align_wrapper` lazy yield; never `list(original(...))` (D-06):

```205:214:scripts/trace_extract.py
      def traced_outputs():
        for index, item in enumerate(original(self, *args, **kwargs)):
          for scored in item:
            out_data = {
                'prompt_index': index,
                'score': scored.score,
                'raw_model_text': scored.output,
            }
            sink.append(StageRecord('model', in_data, out_data))
          yield item

      return traced_outputs()
```

Phase 3 strip to:

```python
def identity(self, *args, **kwargs):
  for item in original(self, *args, **kwargs):
    yield item
  # or: yield from original(self, *args, **kwargs)
```

**ChunkIterator.__iter__ caveat (exact — do not treat as a plain generator):** Phase 4 already discovered `__iter__` returns `self`; a yield-based wrap that re-enters `for x in self` loops forever. Identity for chunk must **return** the original iterator object:

```python
def identity_iter(self, *args, **kwargs):
  return original(self, *args, **kwargs)
```

See `make_chunk_wrapper` docstring (lines 226-229) and body (237-261) — recording wrap drives `next(it)` precisely because of this. CONTEXT D-06 lists `__iter__` among "generator targets"; planner should follow the Phase 4 semantic fix (return-self) for identity, not a naive `yield from`.

**Partial map fill (D-08):** start from identity for all five labels, then overlay provided `wrappers` keys.

---

### Restore self-check (utility, request-response)

**Analog (stderr failure + exit):** `load_config` (lines 70-78).

```70:78:scripts/trace_extract.py
  if not path.exists():
    expected = path.resolve()
    print(f'Error: config file not found: {expected}', file=sys.stderr)
    raise SystemExit(1)
  with path.open('rt', encoding='utf-8') as f:
    data = yaml.safe_load(f)
  if not isinstance(data, dict):
    print(f'Error: {path} must contain a YAML mapping', file=sys.stderr)
    raise SystemExit(1)
```

**Apply (D-09–D-12, specifics):** after catalog print, silent-on-success helper roughly:

```python
def _self_check_probe_restore() -> None:
  # capture originals for all five targets
  with trace_probes():
    # assert each class attr `is not` original (install proof)
    raise RuntimeError('probe self-check')
  # catch above; assert each class attr `is` original
  # on any failure: print to stderr, raise SystemExit(1)
```

No live Ollama / `lx.extract` (phase boundary). Exact stderr wording is Claude's discretion.

---

### `main()` growth (utility, entrypoint)

**Analog:** existing `main` (lines 669-677).

```669:677:scripts/trace_extract.py
def main() -> int:
  """Print the call header and stage catalog.

  :return: Process exit code (0 on success).
  """
  config = load_config(_CONFIG_PATH)
  print_call_header(config)
  print_stage_catalog()
  return 0
```

**Apply:** keep header + catalog stdout contract unchanged; call self-check after catalog; return `0` only if self-check silent-succeeds. Do not print a normal-exit restore demo line (deferred).

---

## Shared Patterns

### Class-attribute save/restore (not bound methods)
**Source:** `.planning/research/ARCHITECTURE.md` Pattern 1; `_patch_stages` uses `cls.__dict__[attr]`
**Apply to:** `trace_probes` install + restore + self-check
```python
original = cls.__dict__[attr]          # or getattr(cls, attr) before patch
setattr(cls, attr, replacement)
# finally:
setattr(cls, attr, original)
```
Never save `instance.method` and write it back.

### Wrappers map contract (Phase 4-compatible)
**Source:** `make_stage_wrappers` (`scripts/trace_extract.py` 418-433); `_STAGE_TARGETS` keys
**Apply to:** `trace_probes(wrappers=...)`, identity defaults, partial fill
- Keys: `'chunk' | 'prompt' | 'model' | 'parse' | 'align'`
- Values: `Callable[[Callable[..., Any]], Callable[..., Any]]` (original → replacement)

### Stdlib-only manager
**Source:** ARCHITECTURE ("No wrapt"); CONTEXT Established Patterns
**Apply to:** `trace_probes` — `contextlib` + try/finally; no wrapt, no library hooks

### Error surfacing for script failures
**Source:** `load_config` stderr + `SystemExit(1)`
**Apply to:** self-check failures only; re-entry uses `RuntimeError` (not SystemExit) so callers/`with` can catch

### Diff budget
**Source:** `CLAUDE.md` / `.claude/skills/diff-budget/SKILL.md`
**Apply to:** planner task split — e.g. (1) `trace_probes` + flag + identity + targets, (2) self-check + `main` wire — each ≤~150 non-test lines, ≤3 source files (here usually 1)

### Optional test analog (if planner adds tests)
**Source:** `_load_script_module`, `_STAGE_TARGETS`, `_patch_stages` in `tests/trace_extract_test.py`
**Apply to:** unit tests of restore / re-entry / partial install — CONTEXT does not require them; in-script self-check is the phase demo

## No Analog Found

| File / Concern | Role | Data Flow | Reason |
|----------------|------|-----------|--------|
| `@contextlib.contextmanager` usage in production code | utility | request-response | No `@contextmanager` / `contextlib.contextmanager` in tracked `*.py` under the repo; use stdlib directly per ARCHITECTURE. Closest behavioral analogs are `_patch_stages` (install) + `factory_test` try/finally (restore). |
| Module-level re-entry `RuntimeError` guard | config | request-response | No `already active` / nested-scope guard in `langextract/` or scripts; invent per D-14–D-16. |

## Metadata

**Analog search scope:** `scripts/`, `tests/trace_extract_test.py`, `tests/factory_test.py`, `langextract/` (contextmanager / RuntimeError grep), `.planning/research/ARCHITECTURE.md`, `.planning/phases/04-stage-wrappers/` (wrapper contract cross-check)
**Files scanned:** ~80 Python files under `langextract/` + `scripts/` + `tests/` (glob/grep); primary reads: `scripts/trace_extract.py`, `tests/trace_extract_test.py`, `tests/factory_test.py`, ARCHITECTURE.md, 04-PATTERNS.md
**Tracked-source gate:** all named analogs verified via `git ls-files`
**Pattern extraction date:** 2026-10-11

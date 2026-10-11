# Phase 3: Call-scoped probe manager - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-11
**Phase:** 3-call-scoped-probe-manager
**Areas discussed:** Probe API shape, Phase-3 wrap bodies, Prove restore, Install failure / re-entry

---

## Probe API shape

| Option | Description | Selected |
|--------|-------------|----------|
| Context manager `with …:` | Automatic try/finally restore | ✓ |
| `install()` / `restore()` pair | Explicit; easy to skip restore | |
| You decide | | |

**User's choice:** Context manager

| Option | Description | Selected |
|--------|-------------|----------|
| `probes()` | Short research wording | |
| `probe_manager()` | Explicit | |
| `trace_probes()` | Ties to script “trace” framing | ✓ |
| You decide | | |

**User's choice:** `trace_probes()`

| Option | Description | Selected |
|--------|-------------|----------|
| No args | Five targets hard-coded | |
| Optional `wrappers={...}` | Phase 4 can inject recorders | ✓ |
| You decide | | |

**User's choice:** Optional wrap map

| Option | Description | Selected |
|--------|-------------|----------|
| Omit → identity for all five | Proves install/restore | ✓ |
| Require `wrappers` | Fail if missing | |
| You decide | | |

**User's choice:** Identity defaults when omitted

---

## Phase-3 wrap bodies

| Option | Description | Selected |
|--------|-------------|----------|
| Pure identity | No counters/prints | ✓ |
| Identity + call counter | Assertable counter | |
| One-line breadcrumb print | Noisy; overlaps Phase 4 | |
| You decide | | |

**User's choice:** Pure identity

| Option | Description | Selected |
|--------|-------------|----------|
| Transparent yield | Never `list()` generators | ✓ |
| Return whatever original returns | Riskier for generators | |
| You decide | | |

**User's choice:** Transparent yield

| Option | Description | Selected |
|--------|-------------|----------|
| No `functools.wraps` | Minimal Phase 3 | ✓ |
| Use `functools.wraps` | Preserve `__name__` | |
| You decide | | |

**User's choice:** No wraps metadata

| Option | Description | Selected |
|--------|-------------|----------|
| Partial map fills with identity | Always install all five | ✓ |
| Require all five keys | Reject incomplete maps | |
| You decide | | |

**User's choice:** Fill missing with identity

---

## Prove restore

| Option | Description | Selected |
|--------|-------------|----------|
| In-script self-check in `main` | After catalog; no Ollama | ✓ |
| Tests only | `main` stays catalog-only | |
| Both | | |
| You decide | | |

**User's choice:** In-script self-check in `main`

| Option | Description | Selected |
|--------|-------------|----------|
| Exception path only | Raise inside `with`, assert restore | ✓ |
| Normal exit + exception | Both paths demoed | |
| You decide | | |

**User's choice:** Exception path only

| Option | Description | Selected |
|--------|-------------|----------|
| Silent on success; stderr+exit 1 on fail | Catalog stdout unchanged | ✓ |
| One OK line on stdout | | |
| You decide | | |

**User's choice:** Silent on success

| Option | Description | Selected |
|--------|-------------|----------|
| `is not` originals | Prove install inside `with` | ✓ |
| Sentinel wrappers | Heavier; overlaps Phase 4 | |
| You decide | | |

**User's choice:** `is not` originals

---

## Install failure / re-entry

| Option | Description | Selected |
|--------|-------------|----------|
| Restore partial installs, then re-raise | Never leave partial monkeypatch | ✓ |
| Best-effort restore in `finally` only | | |
| You decide | | |

**User's choice:** Restore then re-raise

| Option | Description | Selected |
|--------|-------------|----------|
| One-shot only | Error if already active | ✓ |
| Allow nesting | Stack of originals | |
| You decide | | |

**User's choice:** One-shot only

| Option | Description | Selected |
|--------|-------------|----------|
| Module-level `_PROBES_ACTIVE` | Set on enter, clear in `finally` | ✓ |
| Inspect class attrs | Fragile | |
| You decide | | |

**User's choice:** Module-level flag

| Option | Description | Selected |
|--------|-------------|----------|
| `RuntimeError` clear message | e.g. already active | ✓ |
| `SystemExit(1)` | CLI-style | |
| You decide | | |

**User's choice:** `RuntimeError`

---

## Claude's Discretion

- `wrappers` map key/value shape for Phase 4 extensibility
- Exact stderr wording for self-check failure
- Normal-exit restore covered by shared `finally` without a separate demo print

## Deferred Ideas

- Recording wrappers / live extract / nested stacks / `functools.wraps` — later phases or out of MVP

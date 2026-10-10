# Phase 1: Stage catalog & contracts - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-10
**Phase:** 1-Stage catalog & contracts
**Areas discussed:** Phase-1 run output, Section formatting, Call header in Phase 1, Empty-parse copy & redaction stubs

---

## Phase-1 run output

| Option | Description | Selected |
|--------|-------------|----------|
| Catalog only | Seven stage sections; no later-phases footer | ✓ |
| Catalog + footer note | Same plus one line about later phases | |
| You decide | Prefer research build order | |

**User's choice:** Catalog only
**Notes:** Then chose omit in/out lines; exit 0 always; blank line between stages.

---

## Section formatting

| Option | Description | Selected |
|--------|-------------|----------|
| Bracketed header | `[label] function — path` | ✓ |
| Middle-dot form | three fields with · | |
| Markdown-ish multi-line | `## label` then function/file lines | |
| You decide | greppable single-line | |

**User's choice:** Bracketed header; repo-relative paths; primary owner only; WordAligner helper line under align in Phase 1.
**Notes:** —

---

## Call header in Phase 1

| Option | Description | Selected |
|--------|-------------|----------|
| Static header now | No network; planned values | ✓ |
| Defer header | Until live extract | |
| You decide | Static early | |

**User's choice:** Static minimal header; constants in repo-root `config.yaml` (user: any constant including extraction prompt); Phase 1 config = call constants only.
**Notes:** Free-text: “any constant needs to go into config.yaml including the extraction prompt.” Path: repo root `config.yaml`. Content: A (call constants only).

---

## Empty-parse copy & redaction stubs

| Option | Description | Selected |
|--------|-------------|----------|
| Empty-parse in config.yaml now | Not printed until parse has data | ✓ |
| Empty-parse in script | Conflicts with config rule | |
| Defer | Phase 4 | |
| You decide | Config key now | |

**User's choice:** Config sentence (research wording); redact_keys + redact() stub; redact_keys match `debug_utils`.
**Notes:** —

---

## Claude's Discretion

- Primary owners when research lists two files
- Exact YAML key naming

## Deferred Ideas

- Prompt / examples in config.yaml until Phase 5
- Live in/out, preflight, printing empty-parse until later phases

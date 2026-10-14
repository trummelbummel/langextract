---
id: 261014-g6y
timestamp: 2026-10-14T10:45:00Z
---

# Dedup review — 261014-g6y

## Scope

Production + tests from 261014-g6y commits, plus one-hop importers of
`events` / `TokenUsage` (`annotation`, `extraction`, `ollama`,
`chunk_events_test`; OpenAI/Gemini import `ScoredOutput` only — no shared
usage helper yet).

## Changes Applied

| Action | Files | What Changed |
|--------|-------|-------------|
| (none) | — | No safe auto-apply consolidations |

## Proposed Reorganization

| Signal | Files | Proposal | Impact | Verdict | Signals | Risk |
|--------|-------|----------|--------|---------|---------|------|
| — | — | no proposals to classify | — | — | — | — |

## Notes

- `OUTCOME_OK` / `OUTCOME_PARSE_ERROR` live once in `events.py` (style-review).
- `_usage_from_response` is Ollama-only; OpenAI/Gemini mapping is deferred (5b/c) — not duplicate yet.
- Test fakes in `chunk_events_test.py` are assertion-specific; not shared with `inference_test.py`.
- `events.py` has multiple importers — not an S07 orphan.

**Summary:** 0 redundancies found, 0 auto-fixed, 0 proposals for review.

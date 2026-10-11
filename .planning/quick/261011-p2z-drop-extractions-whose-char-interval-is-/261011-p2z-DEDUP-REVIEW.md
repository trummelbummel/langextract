---
quick_id: 261011-p2z
review: dedup
timestamp: 2026-10-11T17:25:00Z
commit_range: e6c846e..1ae049b
---

# Dedup review — 261011-p2z

## Scope

| Item | Value |
|------|--------|
| Mode | quick |
| Files | `langextract/extraction.py`, `tests/extract_drop_ungrounded_test.py` |
| One-hop | `tests/extract_precedence_test.py`, `langextract/__init__.py` |

## Changes applied

| Action | Files | What changed |
|--------|-------|--------------|
| *(none)* | — | No safe auto-consolidations |

## Proposed reorganization (propose-only)

| Signal | Files | Proposal | Impact |
|--------|-------|----------|--------|
| S09 | `extract_drop_ungrounded_test.py`, `extract_precedence_test.py` | Keep local `_setup_mocks` — bodies differ (fence flag, return shapes, assertion focus) | Sharing would churn unrelated precedence tests |
| S09 | same modules `setUp` examples | Keep local — trivial identical ExampleData setup; no `tests/conftest.py` yet | Low value vs churn |
| S06 | `langextract/extraction.py` | No split; `_drop_ungrounded` stays colocated | None |

## Summary

2 redundancies considered, 0 auto-fixed, 2 proposals (both keep-local).

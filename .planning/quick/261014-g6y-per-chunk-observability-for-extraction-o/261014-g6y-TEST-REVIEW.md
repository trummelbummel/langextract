---
id: 261014-g6y
timestamp: 2026-10-14T10:55:00Z
---

# Test review — 261014-g6y

## Scope

- `tests/chunk_events_test.py` (new) — all tests `new`
- `tests/inference_test.py` — new Ollama usage tests
- Production siblings: `annotation.py`, `events.py`, `types.py`, `extraction.py`, `ollama.py`

## Classification

| Task | Title | Verdict | Status |
|------|-------|---------|--------|
| TF-006 | Extract annotate run helpers (S13) | ✅ simple | [x] |
| TF-007 | Finish S13 migration + split multi-behavior (S13/S4) | ✅ simple | [ ] open (gate / step 6) |
| TF-008 | Parametrize Ollama usage twins (S4) | ✅ simple | [x] auto-resolved `aa4efe1` |

**Summary:** 3 simple / 0 complex out of 3 new tasks for this id.

## Smells

| ID | Evidence | Action |
|----|----------|--------|
| S13 | ~17× annotate_documents + filter boilerplate | TF-006/007 |
| S4 | multi-behavior tests; Ollama usage twins | TF-007/008 (also style R18/R19) |
| S1 | Ollama `_ollama_query` patches | OK (provider boundary) |

## Mutation scorecard

| Site | Mutation | Result |
|------|----------|--------|
| batch_index `[0,0,0,1]` → `[0,0,0,0]` | FAIL (good) |
| parse_error outcome → ok | FAIL (good) |
| duration_s `>=0` → `<0` | FAIL (good) |
| thread_ids `==` caller → `!=` | FAIL (good) |
| Ollama `input_tokens` 15 → 0 | FAIL (good) |

**5/5 sabotage caught. Working tree clean of sabotage.**

## Tests for review

`tests/chunk_events_test.py` — `ChunkEventsTest` methods ~179–760; `TokenUsageConstructionTest`.
`tests/inference_test.py` — `test_ollama_infer_fills_token_usage`, `test_ollama_gpt_oss_chat_fills_token_usage`, `test_ollama_infer_missing_usage_keys_are_none`.

## Backlog

- Open `[ ]`: TF-007 (simple — gate).
- Auto-resolved: TF-008 → `aa4efe1`.

# Phase 5: Live extract & Ollama preflight — API Coverage

Cold-load hangs are covered by `request_timeout_s: 300` on the single generate request (`language_model_params.timeout`).

| Surface | Used by | Decision | Verification |
|---------|---------|----------|--------------|
| `GET /api/tags` | `preflight_ollama` | covered (reachability, HTTP status, JSON shape, exact model match) | stub tests in 05-01 Task 2 (`TraceExtractPreflightTest`) |
| `POST /api/generate` | inside `lx.extract` via `OllamaLanguageModel` only | covered, exactly once per run | stub hit counter + `check_single_inference` + env-gated `TraceExtractRealOllamaTest` |
| `POST /api/chat` (gpt-oss path) | — | opt-out: not reached for `gemma3:4b` | provider routes gemma models to `/api/generate` |
| `/api/pull` | — | opt-out: no model management or second inference (RUN-03); user runs `ollama pull` | preflight error text names `ollama pull` |
| `/api/show` | — | opt-out: no model management | not called by script |
| `/api/ps` | — | opt-out: no model management | not called by script |
| warm-up generate | — | opt-out: no second inference (RUN-03) | `check_single_inference` + stub `/api/generate` hit == 1 |
| streaming responses | — | opt-out: provider sends `stream=false` | `langextract/providers/ollama.py` payload |
| auth headers / `api_key` | — | opt-out: local Ollama, no key passed | `_extract_kwargs` omits `api_key`; 05-01 grep gate |
| cloud providers | — | opt-out: out of scope (REQUIREMENTS Out of Scope) | `_extract_kwargs` pins local Ollama only |

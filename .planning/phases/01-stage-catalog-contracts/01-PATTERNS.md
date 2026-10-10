# Phase 1: Stage catalog & contracts - Pattern Map

**Mapped:** 2026-10-10
**Files analyzed:** 2
**Analogs found:** 2 / 2 (config has load-pattern only; no existing repo-root YAML)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `scripts/trace_extract.py` | utility (maintainer CLI) | transform + file-I/O | `scripts/validate_community_providers.py` | exact |
| `config.yaml` | config | file-I/O | `langextract/prompting.py` (`yaml.safe_load` of a file) + value defaults from `langextract/providers/ollama.py` | role-match |

**Implied helpers inside the script (not separate files):** stage catalog tuple, call-header printer, `redact()` stub — classified with the script.

## Pattern Assignments

### `scripts/trace_extract.py` (utility, transform + file-I/O)

**Analog:** `scripts/validate_community_providers.py` (primary CLI shape)

**Shebang / docstring / imports** — prefer `scripts/create_provider_plugin.py` order (shebang then Apache header then docstring), not validate’s inverted shebang:

```1:34:scripts/create_provider_plugin.py
#!/usr/bin/env python3
# Copyright 2025 Google LLC.
# ...
"""Create a new LangExtract provider plugin with all boilerplate code.
...
Usage:
    python create_provider_plugin.py MyProvider
```

**Main + exit codes** (lines 201–209 of validate script):

```python
if __name__ == '__main__':
  path = Path('COMMUNITY_PROVIDERS.md')
  if len(sys.argv) > 1:
    path = Path(sys.argv[1])
  if not path.exists():
    print(f'❌ Error: File not found: {path}')
    sys.exit(1)
  ok = validate(path)
  sys.exit(0 if ok else 1)
```

Phase 1: successful catalog print exits `0` (D-03). Missing `config.yaml` → print error, `sys.exit(1)` (same existence check). No argparse required for Phase 1 (catalog-only).

**Repo-root resolution for `config.yaml`:** script lives under `scripts/`, so root is parent of `scripts/`. Closest tracked pattern:

```47:52:tests/create_provider_plugin_test.py
_SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "scripts"
    / "create_provider_plugin.py"
)
_REPO_ROOT = _SCRIPT_PATH.parent.parent
```

For the new script itself:

```python
_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO_ROOT / "config.yaml"
```

**YAML load pattern** from `langextract/prompting.py` (lines 68–74) — use `yaml.safe_load`, open as text:

```python
with pathlib.Path(prompt_path).open("rt") as f:
  prompt_content = f.read()
  if format_type == data.FormatType.YAML:
    data_dict = yaml.safe_load(prompt_content)
```

Script variant (no FormatType branch):

```python
import yaml
from pathlib import Path

def load_config(path: Path) -> dict:
  with path.open("rt", encoding="utf-8") as f:
    data = yaml.safe_load(f) or {}
  if not isinstance(data, dict):
    raise SystemExit(f"ERROR: {path} must contain a YAML mapping")
  return data
```

**Plain stdout sections** — `examples/ollama/demo_ollama.py` uses decorative `print_header` / `print_section` (lines 83–93). **Do not copy that format.** Phase 1 headers are locked (D-05):

```text
[prompt-template] PromptTemplateStructured — langextract/prompting.py
```

Blank line between stage sections (D-04). Under `[align]` only, one helper line (D-08):

```text
helper: WordAligner.align_extractions
```

**Static call header constants** — names/defaults from `examples/ollama/demo_ollama.py` (lines 62–63) and `langextract/providers/ollama.py` (line 105), but values come from YAML not Python literals (D-10/D-11):

```62:63:examples/ollama/demo_ollama.py
DEFAULT_MODEL = "gemma2:2b"
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
```

```105:105:langextract/providers/ollama.py
_OLLAMA_DEFAULT_MODEL_URL = 'http://localhost:11434'
```

Phase 1 header content (D-09): `lx.extract`, `model_id` from config (milestone: `gemma3:4b`), provider display name (e.g. `OllamaLanguageModel`), host from `model_url`. Do **not** call `check_ollama_available` in Phase 1 (deferred to live-extract).

**Stage catalog owners** — primary function + primary file from FEATURES.md stage map (D-07; Claude’s discretion when research lists two files):

| Label | Function | Path |
|-------|----------|------|
| `prompt-template` | `PromptTemplateStructured` | `langextract/prompting.py` |
| `chunk` | `ChunkIterator` | `langextract/chunking.py` |
| `prompt` | `ContextAwarePromptBuilder.build_prompt` | `langextract/prompting.py` |
| `model` | `OllamaLanguageModel.infer` | `langextract/providers/ollama.py` |
| `parse` | `Resolver.resolve` | `langextract/resolver.py` |
| `align` | `Resolver.align` | `langextract/resolver.py` |
| `annotated-document` | `extract` | `langextract/extraction.py` |

Store as a module-level tuple/list of `(label, function_name, repo_relative_path)` and iterate for printing. No `in:` / `out:` lines yet (D-02).

**Redact stub** — mirror key set from `langextract/core/debug_utils.py` (lines 34–44, 57–70); keys live in YAML (D-14), not imported from private `_REDACT_KEYS`:

```34:70:langextract/core/debug_utils.py
# Sensitive keys to redact
_REDACT_KEYS = {
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "authorization",
    "bearer",
    "jwt",
}
...
def _redact_value(name: str, value: Any) -> str:
  """Redact sensitive values based on parameter name."""
  if isinstance(name, str) and name.lower() in _REDACT_KEYS:
    return "<REDACTED>"
  if isinstance(value, Mapping):
    redacted = {}
    for k, v in value.items():
      if isinstance(k, str) and k.lower() in _REDACT_KEYS:
        redacted[k] = "<REDACTED>"
      else:
        redacted[k] = _safe_repr(v)
    return _safe_repr(redacted)
  return _safe_repr(value)
```

Phase 1 stub: load `redact_keys` from config; implement a small public `redact(mapping)` that replaces matching keys with `"<REDACTED>"`. Not used for stdout yet (D-15).

**Indent / style:** match scripts — 2-space indent (pyink), Apache copyright, `snake_case` functions, `if __name__ == "__main__"`.

**Anti-patterns for this file (from ARCHITECTURE / CONTEXT):**
- Do not edit `langextract/` or `examples/ollama/demo_ollama.py`.
- Do not register a console script in `pyproject.toml`.
- Do not call `lx.extract` or wrap probes in Phase 1.
- Do not import private `_REDACT_KEYS` / `_redact_value` from the package.

---

### `config.yaml` (config, file-I/O)

**Analog:** No existing repo-root YAML config. Closest patterns:
1. **Load side:** `langextract/prompting.py` `yaml.safe_load` (above).
2. **Value defaults:** `langextract/providers/ollama.py` `_OLLAMA_DEFAULT_MODEL_URL`; CONTEXT/STACK for `gemma3:4b`.
3. **Centralized constants idea only:** `benchmarks/config.py` (Python dataclasses — do **not** copy that format; Phase 1 constants must be YAML per D-10).

**Suggested Phase 1 shape** (key names at Claude’s discretion; keep `model_id` / `model_url` as locked names):

```yaml
# Call constants for scripts/trace_extract.py (Phase 1)
model_id: gemma3:4b
model_url: http://localhost:11434
provider: OllamaLanguageModel

# Stored for later phases; not printed in Phase 1
empty_parse_message: >
  Chunk omitted on parse or schema error; raw model text is kept above.

redact_keys:
  - api_key
  - apikey
  - token
  - secret
  - password
  - authorization
  - bearer
  - jwt
```

Prompt / examples deferred (D-11). Empty-parse string stored now (D-13), printed only when parse has live data.

## Shared Patterns

### Maintainer CLI entry
**Source:** `scripts/validate_community_providers.py`, `scripts/create_provider_plugin.py`
**Apply to:** `scripts/trace_extract.py`
- Run as `python scripts/trace_extract.py` (not installed entry point).
- Shebang `#!/usr/bin/env python3`, Apache header, module docstring with Usage.
- `if __name__ == "__main__":` → `main()` or inline; `sys.exit(0)` on success.

### Config via YAML + PyYAML
**Source:** `langextract/prompting.py` (load); `pyproject.toml` already depends on `PyYAML>=6.0`
**Apply to:** script load of `config.yaml`
- `yaml.safe_load` only (never `yaml.load`).
- Resolve path from `__file__` → repo root; do not hardcode CWD-only relative paths without resolving.

### Secret redaction key list
**Source:** `langextract/core/debug_utils.py` lines 35–44
**Apply to:** `config.yaml` `redact_keys` + script `redact()` stub
- Exact eight key names; case-insensitive match on key names when redacting.
- Replacement token `"<REDACTED>"` to match library debug logs.

### Stdout contract (Phase 1)
**Source:** CONTEXT D-01–D-09 (not demo_ollama decorative headers)
**Apply to:** catalog printer in the script
1. Call header (static, from YAML).
2. Seven stage headers `[label] function — path`.
3. Align helper line.
4. Blank line between stages.
5. No `in:`/`out:`, no Ollama network, no later-phase footer.

## No Analog Found

| File / concern | Role | Data Flow | Reason |
|----------------|------|-----------|--------|
| Repo-root `config.yaml` as a committed product config | config | file-I/O | No existing YAML at repo root; only in-library YAML parsing of prompt/model payloads. Use `yaml.safe_load` + CONTEXT key list. |
| Stage catalog tuple / `[label] function — path` printer | utility | transform | New Phase 1 surface; owners from FEATURES.md, format from CONTEXT. |

## Metadata

**Analog search scope:** `scripts/`, `examples/ollama/`, `langextract/core/debug_utils.py`, `langextract/prompting.py`, `langextract/providers/ollama.py`, `benchmarks/config.py`, `tests/create_provider_plugin_test.py` (Path pattern only)
**Files scanned:** ~15 tracked Python files in those areas; all named analogs verified via `git ls-files`
**Pattern extraction date:** 2026-10-10
**Tracked-source gate:** analogs are git-tracked (no `.gsd/` mirrors)
)

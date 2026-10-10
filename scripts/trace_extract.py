#!/usr/bin/env python3
# Copyright 2025 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Print the LangExtract pipeline stage catalog and static call header.

Usage:
    python scripts/trace_extract.py
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import dataclasses
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO_ROOT / 'config.yaml'
_REDACTION_TOKEN = '<REDACTED>'

# (label, function_name, repo_relative_path)
STAGE_CATALOG: list[tuple[str, str, str]] = [
    ('prompt-template', 'PromptTemplateStructured', 'langextract/prompting.py'),
    ('chunk', 'ChunkIterator', 'langextract/chunking.py'),
    (
        'prompt',
        'ContextAwarePromptBuilder.build_prompt',
        'langextract/prompting.py',
    ),
    (
        'model',
        'OllamaLanguageModel.infer',
        'langextract/providers/ollama.py',
    ),
    ('parse', 'Resolver.resolve', 'langextract/resolver.py'),
    ('align', 'Resolver.align', 'langextract/resolver.py'),
    ('annotated-document', 'extract', 'langextract/extraction.py'),
]


def load_config(path: Path) -> dict:
  """Load call constants from a YAML mapping at path.

  Raises:
    SystemExit: with code 1 when path is missing or not a mapping.
  """
  if not path.exists():
    expected = path.resolve()
    print(f'Error: config file not found: {expected}', file=sys.stderr)
    raise SystemExit(1)
  with path.open('rt', encoding='utf-8') as f:
    data = yaml.safe_load(f)
  if not isinstance(data, dict):
    print(f'Error: {path} must contain a YAML mapping', file=sys.stderr)
    raise SystemExit(1)
  return data


def redact(
    mapping: Mapping[str, Any],
    keys: Iterable[str] | None = None,
) -> dict[str, Any]:
  """Return a copy of mapping with sensitive key values replaced.

  Matching is case-insensitive on key names. Nested mappings are redacted
  at least one level deep. When keys is None, loads redact_keys from config.
  """
  if keys is None:
    keys = load_config(_CONFIG_PATH)['redact_keys']
  key_set = {k.lower() for k in keys}

  def _redact_one(value: Any) -> Any:
    if isinstance(value, Mapping):
      return {
          k: (
              _REDACTION_TOKEN
              if isinstance(k, str) and k.lower() in key_set
              else v
          )
          for k, v in value.items()
      }
    return value

  out: dict[str, Any] = {}
  for k, v in mapping.items():
    if isinstance(k, str) and k.lower() in key_set:
      out[k] = _REDACTION_TOKEN
    elif isinstance(v, Mapping):
      out[k] = _redact_one(v)
    else:
      out[k] = v
  return out


def _host_from_model_url(model_url: str) -> str:
  """Return host (netloc) from model_url, or the raw string if unparseable."""
  parsed = urlparse(model_url)
  return parsed.netloc or model_url


def print_call_header(config: dict) -> None:
  """Print the static lx.extract call header from config constants."""
  model_id = config.get('model_id', '')
  model_url = config.get('model_url', '')
  provider = config.get('provider', '')
  host = _host_from_model_url(str(model_url))
  print(
      f'lx.extract  model_id={model_id}  {provider}  {model_url}  (host={host})'
  )
  print()


def print_stage_catalog() -> None:
  """Print seven stage headers (and align helper) with blank-line gaps."""
  for i, (label, function_name, path) in enumerate(STAGE_CATALOG):
    if i:
      print()
    print(f'[{label}] {function_name} — {path}')
    if label == 'align':
      print('helper: WordAligner.align_extractions')


@dataclasses.dataclass(frozen=True)
class ExtractionSnapshot:
  """Field copies of one Extraction, taken at a single pipeline stage."""

  extraction_class: str
  extraction_text: str
  extraction_index: int | None
  group_index: int | None
  attributes: dict | None
  char_interval: tuple[int | None, int | None] | None
  token_interval: tuple[int, int] | None
  alignment_status: str | None


def _snapshot_extraction(extraction: Any) -> ExtractionSnapshot:
  """Copy the traced fields of extraction by duck typing."""
  char = extraction.char_interval
  token = extraction.token_interval
  status = extraction.alignment_status
  return ExtractionSnapshot(
      extraction_class=extraction.extraction_class,
      extraction_text=extraction.extraction_text,
      extraction_index=extraction.extraction_index,
      group_index=extraction.group_index,
      attributes=extraction.attributes,
      char_interval=None if char is None else (char.start_pos, char.end_pos),
      token_interval=(
          None if token is None else (token.start_index, token.end_index)
      ),
      alignment_status=None if status is None else status.value,
  )


def snapshot_extractions(
    extractions: Iterable[Any],
) -> tuple[ExtractionSnapshot, ...]:
  """Snapshot extractions in order, before later stages mutate them."""
  return tuple(_snapshot_extraction(e) for e in extractions)


def _format_interval(interval: tuple[int | None, int | None] | None) -> str:
  if interval is None:
    return 'None'
  return f'[{interval[0]}, {interval[1]})'


def _format_grounding(snap: ExtractionSnapshot) -> str:
  return (
      f'char_interval={_format_interval(snap.char_interval)} '
      f'alignment_status={snap.alignment_status}'
  )


def print_grounding_pair(
    parse_snapshots: Iterable[ExtractionSnapshot],
    align_snapshots: Iterable[ExtractionSnapshot],
) -> None:
  """Print each extraction as a parse line followed by its align line."""
  pairs = list(zip(parse_snapshots, align_snapshots))
  print(f'grounding pair (parse → align): {len(pairs)} extractions')
  for i, (parse, align) in enumerate(pairs, start=1):
    print(
        f'  [{i}] {parse.extraction_class}: {parse.extraction_text!r}'
        f'  index={parse.extraction_index}'
    )
    print(f'    parse: {_format_grounding(parse)}')
    print(f'    align: {_format_grounding(align)}')


def main() -> int:
  config = load_config(_CONFIG_PATH)
  print_call_header(config)
  print_stage_catalog()
  return 0


if __name__ == '__main__':
  sys.exit(main())

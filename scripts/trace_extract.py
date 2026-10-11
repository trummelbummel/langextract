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


def load_config(path: Path) -> dict[str, Any]:
  """Load call constants from a YAML mapping at path.

  :param path: YAML config file to read.
  :return: The parsed top-level mapping.

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

  :param mapping: Mapping to redact; not modified.
  :param keys: Key names to redact; defaults to config redact_keys.
  :return: Redacted copy of mapping.
  """
  if keys is None:
    keys = load_config(_CONFIG_PATH)['redact_keys']
  key_set = {k.lower() for k in keys}
  flat = _redact_flat(mapping, key_set)
  return {
      k: _redact_flat(v, key_set) if isinstance(v, Mapping) else v
      for k, v in flat.items()
  }


def _redact_flat(
    mapping: Mapping[str, Any], key_set: set[str]
) -> dict[str, Any]:
  """Replace values of sensitive keys in mapping, one level deep."""
  return {
      k: _REDACTION_TOKEN if isinstance(k, str) and k.lower() in key_set else v
      for k, v in mapping.items()
  }


def _host_from_model_url(model_url: str) -> str:
  """Return host (netloc) from model_url, or the raw string if unparseable."""
  parsed = urlparse(model_url)
  return parsed.netloc or model_url


def print_call_header(config: Mapping[str, Any]) -> None:
  """Print the static lx.extract call header from config constants.

  :param config: Config mapping with model_id, model_url and provider.
  """
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
  attributes: dict[str, Any] | None
  char_interval: tuple[int | None, int | None] | None
  token_interval: tuple[int, int] | None
  alignment_status: str | None


def _copy_attributes(
    attributes: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
  """Copy attributes one level deep so list values are not aliased."""
  if attributes is None:
    return None
  return {
      k: list(v) if isinstance(v, list) else v for k, v in attributes.items()
  }


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
      attributes=_copy_attributes(extraction.attributes),
      char_interval=None if char is None else (char.start_pos, char.end_pos),
      token_interval=(
          None if token is None else (token.start_index, token.end_index)
      ),
      alignment_status=None if status is None else status.value,
  )


def snapshot_extractions(
    extractions: Iterable[Any],
) -> tuple[ExtractionSnapshot, ...]:
  """Snapshot extractions in order, before later stages mutate them.

  :param extractions: Live extraction objects to copy.
  :return: One ExtractionSnapshot per extraction, in input order.
  """
  return tuple(_snapshot_extraction(e) for e in extractions)


def _format_interval(interval: tuple[int | None, int | None] | None) -> str:
  """Format a half-open char interval, or 'None'."""
  if interval is None:
    return 'None'
  return f'[{interval[0]}, {interval[1]})'


def _format_grounding(
    snap: ExtractionSnapshot, none_label: str | None = None
) -> str:
  """Format grounding fields; none_label replaces None when given."""
  interval = _format_interval(snap.char_interval)
  status = snap.alignment_status
  if none_label is not None:
    if snap.char_interval is None:
      interval = none_label
    if status is None:
      status = none_label
  return f'char_interval={interval} alignment_status={status}'


def print_grounding_pair(
    parse_snapshots: Iterable[ExtractionSnapshot],
    align_snapshots: Iterable[ExtractionSnapshot],
    ungrounded_label: str,
) -> None:
  """Print each extraction as a parse line followed by its align line.

  Extractions that align could not ground show ungrounded_label on the align
  line; the parse line keeps None (not yet grounded).

  :param parse_snapshots: Snapshots taken after the parse stage.
  :param align_snapshots: Snapshots taken after the align stage.
  :param ungrounded_label: Text shown in place of None on align lines.
  :raises TypeError: If any item is not an ExtractionSnapshot.
  :raises ValueError: If the two sequences differ in length or order.
  """
  parse_list = list(parse_snapshots)
  align_list = list(align_snapshots)
  _validate_grounding_pair(parse_list, align_list)
  _print_grounding_lines(parse_list, align_list, ungrounded_label)


def _validate_grounding_pair(
    parse_list: list[ExtractionSnapshot], align_list: list[ExtractionSnapshot]
) -> None:
  """Raise when the parse and align snapshots cannot be paired."""
  for item in (*parse_list, *align_list):
    if not isinstance(item, ExtractionSnapshot):
      raise TypeError(
          'print_grounding_pair needs ExtractionSnapshot items, got '
          f'{type(item).__name__}; live objects are never printed'
      )
  if len(parse_list) != len(align_list):
    raise ValueError(
        f'parse has {len(parse_list)} extractions but align has '
        f'{len(align_list)}'
    )
  for i, (parse, align) in enumerate(zip(parse_list, align_list), start=1):
    if (parse.extraction_class, parse.extraction_text) != (
        align.extraction_class,
        align.extraction_text,
    ):
      raise ValueError(
          f'parse/align mismatch at position {i}: '
          f'{parse.extraction_text!r} vs {align.extraction_text!r}'
      )


def _print_grounding_lines(
    parse_list: list[ExtractionSnapshot],
    align_list: list[ExtractionSnapshot],
    ungrounded_label: str,
) -> None:
  """Print the paired parse and align lines for each extraction."""
  pairs = list(zip(parse_list, align_list))
  print(f'grounding pair (parse → align): {len(pairs)} extractions')
  if not pairs:
    print('    parse: []')
    print('    align: []')
  for i, (parse, align) in enumerate(pairs, start=1):
    print(
        f'  [{i}] {parse.extraction_class}: {parse.extraction_text!r}'
        f'  index={parse.extraction_index}'
    )
    print(f'    parse: {_format_grounding(parse)}')
    print(f'    align: {_format_grounding(align, ungrounded_label)}')


def main() -> int:
  """Print the call header and stage catalog.

  :return: Process exit code (0 on success).
  """
  config = load_config(_CONFIG_PATH)
  print_call_header(config)
  print_stage_catalog()
  return 0


if __name__ == '__main__':
  sys.exit(main())

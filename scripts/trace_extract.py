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
    python scripts/trace_extract.py --catalog-only
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable, Iterator, Mapping
import contextlib
import dataclasses
import functools
import inspect
import json
from pathlib import Path
import pprint
import sys
import textwrap
from typing import Any
import urllib.error
from urllib.parse import urlparse
import urllib.request

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO_ROOT / 'config.yaml'
_REDACTION_TOKEN = '<REDACTED>'
_PROBES_ACTIVE = False
_MAX_TAGS_BYTES = 1024 * 1024
# Library default for lx.extract max_char_buffer; one-chunk pre-check ceiling.
_MAX_CHAR_BUFFER = 1000
_SINGLE_CALL_LINE = 'run: 1 lx.extract, 1 OllamaLanguageModel.infer (1 prompt)'

_WrapFactory = Callable[[Callable[..., Any]], Callable[..., Any]]

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

  :raises SystemExit: With code 1 when path is missing or not a mapping.
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


@dataclasses.dataclass(frozen=True)
class StageRecord:
  """Live data in and out of one pipeline stage (primitives only)."""

  label: str
  in_data: dict[str, Any]
  out_data: dict[str, Any]


def _safe_text(text: Any) -> str:
  """Escape control characters; keep newline, tab and printable text."""
  if text is None:
    return 'None'
  return ''.join(
      ch if ch in '\n\t' or ch.isprintable() else repr(ch)[1:-1]
      for ch in str(text)
  )


def make_model_wrapper(
    sink: list[StageRecord], redact_keys: Iterable[str]
) -> _WrapFactory:
  """Build an original -> replacement wrapper for OllamaLanguageModel.infer.

  The replacement yields the same items lazily and appends one 'model'
  record per yielded ScoredOutput. Nothing is parsed or printed here.

  :param sink: Caller-owned list that receives StageRecords.
  :param redact_keys: Key names redacted in the recorded forwarded kwargs.
  :return: wrap(original) returning the replacement callable.
  """
  keys = list(redact_keys)

  def wrap(original: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(original)
    def traced_infer(self: Any, *args: Any, **kwargs: Any) -> Iterator[Any]:
      bound = inspect.signature(original).bind(self, *args, **kwargs)
      prompts = tuple(bound.arguments['batch_prompts'])
      extra = {k: v for k, v in kwargs.items() if k != 'batch_prompts'}
      in_data = {
          'batch_prompts': prompts,
          'batch_size': len(prompts),
          'kwargs': redact(extra, keys=keys),
      }

      def traced_outputs() -> Iterator[Any]:
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

    return traced_infer

  return wrap


def make_chunk_wrapper(
    sink: list[StageRecord],
) -> _WrapFactory:
  """Build an original -> replacement wrapper for ChunkIterator.__iter__.

  ChunkIterator.__iter__ returns self, so the replacement drives the result
  with next(); a for-in or yield-from would re-enter the patched __iter__.

  :param sink: Caller-owned list that receives StageRecords.
  :return: wrap(original) returning the replacement callable.
  """

  def wrap(original: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(original)
    def traced_iter(self: Any, *args: Any, **kwargs: Any) -> Iterator[Any]:
      it = original(self, *args, **kwargs)
      in_data = {
          'max_char_buffer': self.max_char_buffer,
          'document_text': self.tokenized_text.text,
      }
      while True:
        try:
          chunk = next(it)
        except StopIteration:
          return
        out_data = {
            'chunk_text': chunk.chunk_text,
            'char_interval': (
                chunk.char_interval.start_pos,
                chunk.char_interval.end_pos,
            ),
            'token_interval': (
                chunk.token_interval.start_index,
                chunk.token_interval.end_index,
            ),
            'document_id': getattr(chunk, 'document_id', None),
        }
        sink.append(StageRecord('chunk', in_data, out_data))
        yield chunk

    return traced_iter

  return wrap


def make_prompt_wrapper(
    sink: list[StageRecord],
) -> _WrapFactory:
  """Build an original -> replacement wrapper for build_prompt.

  The original runs exactly once (it updates the builder's previous-chunk
  state) and its prompt string is returned unchanged.

  :param sink: Caller-owned list that receives StageRecords.
  :return: wrap(original) returning the replacement callable.
  """

  def wrap(original: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(original)
    def traced_build_prompt(self: Any, *args: Any, **kwargs: Any) -> Any:
      bound = inspect.signature(original).bind(self, *args, **kwargs)
      bound.apply_defaults()
      prompt = original(self, *args, **kwargs)
      in_data = {
          'chunk_text': bound.arguments['chunk_text'],
          'document_id': bound.arguments['document_id'],
          'additional_context': bound.arguments['additional_context'],
          'context_window_chars': getattr(self, '_context_window_chars', None),
      }
      sink.append(StageRecord('prompt', in_data, {'prompt': prompt}))
      return prompt

    return traced_build_prompt

  return wrap


_FORMAT_FLAGS = (
    'format_type',
    'use_fences',
    'strict_fences',
    'use_wrapper',
    'wrapper_key',
)


def _format_flags(resolver_self: Any) -> dict[str, Any]:
  """Read format flags from the Resolver's own format_handler."""
  handler = getattr(resolver_self, 'format_handler', None)
  flags = {name: getattr(handler, name, None) for name in _FORMAT_FLAGS}
  flag = flags['format_type']
  flags['format_type'] = getattr(flag, 'value', flag)
  return flags


def _diagnose_empty_parse(
    original: Callable[..., Any], bound: inspect.BoundArguments
) -> str | None:
  """Re-run the original resolve strictly to learn why it returned nothing.

  Calls the unwrapped original (no StageRecord, result discarded) with
  suppress_parse_errors=False.

  :param original: The unwrapped Resolver.resolve.
  :param bound: The bound arguments of the traced call, defaults applied.
  :return: 'ErrorType: message' when strict resolve raises, else None.
  """
  strict = inspect.BoundArguments(bound.signature, dict(bound.arguments))
  strict.arguments['suppress_parse_errors'] = False
  try:
    original(*strict.args, **strict.kwargs)
  except Exception as e:  # pylint: disable=broad-exception-caught
    return f'{type(e).__name__}: {e}'
  return None


def make_parse_wrapper(
    sink: list[StageRecord],
) -> _WrapFactory:
  """Build an original -> replacement wrapper for Resolver.resolve.

  The record is appended before returning; the original result object is
  returned untouched, and only ungrounded snapshots of it are recorded.

  :param sink: Caller-owned list that receives StageRecords.
  :return: wrap(original) returning the replacement callable.
  """

  def wrap(original: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(original)
    def traced_resolve(self: Any, *args: Any, **kwargs: Any) -> Any:
      out = original(self, *args, **kwargs)
      bound = inspect.signature(original).bind(self, *args, **kwargs)
      bound.apply_defaults()
      in_data = {
          'raw_model_text': bound.arguments['input_text'],
          'flags': _format_flags(self),
          'suppress_parse_errors': bound.arguments['suppress_parse_errors'],
      }
      out_data = {'extractions': snapshot_extractions(out)}
      if not out:
        out_data['parse_error'] = _diagnose_empty_parse(original, bound)
      else:
        out_data['parse_error'] = None
      sink.append(StageRecord('parse', in_data, out_data))
      return out

    return traced_resolve

  return wrap


def make_align_wrapper(
    sink: list[StageRecord],
) -> _WrapFactory:
  """Build an original -> replacement wrapper for Resolver.align.

  The replacement returns a lazy generator that yields the same Extraction
  objects; the snapshot is taken in a finally block, so it sees the final
  grounding and is still written for empty or early-closed generators.

  :param sink: Caller-owned list that receives StageRecords.
  :return: wrap(original) returning the replacement callable.
  """

  def wrap(original: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(original)
    def traced_align(self: Any, *args: Any, **kwargs: Any) -> Iterator[Any]:
      bound = inspect.signature(original).bind(self, *args, **kwargs)
      bound.apply_defaults()
      given = bound.arguments
      in_data = {
          'source_text': given['source_text'],
          'token_offset': given['token_offset'],
          'char_offset': given['char_offset'] or 0,
          'n_extractions': len(given['extractions']),
      }

      def traced_outputs() -> Iterator[Any]:
        seen = []
        try:
          for extraction in original(self, *args, **kwargs):
            seen.append(extraction)
            yield extraction
        finally:
          out_data = {'extractions': snapshot_extractions(seen)}
          sink.append(StageRecord('align', in_data, out_data))

      return traced_outputs()

    return traced_align

  return wrap


def make_stage_wrappers(
    sink: list[StageRecord], config: Mapping[str, Any]
) -> dict[str, _WrapFactory]:
  """Map catalog labels to original -> replacement wrapper callables.

  :param sink: Caller-owned list that receives StageRecords.
  :param config: Config mapping providing redact_keys.
  :return: Wrapper factories keyed by stage label.
  """
  return {
      'chunk': make_chunk_wrapper(sink),
      'prompt': make_prompt_wrapper(sink),
      'model': make_model_wrapper(sink, config['redact_keys']),
      'parse': make_parse_wrapper(sink),
      'align': make_align_wrapper(sink),
  }


_PROBE_TARGETS: dict[str, tuple[type, str]] | None = None


def _load_probe_targets() -> dict[str, tuple[type, str]]:
  """Resolve the five extract call targets (lazy langextract import)."""
  global _PROBE_TARGETS
  if _PROBE_TARGETS is not None:
    return _PROBE_TARGETS
  from langextract import chunking
  from langextract import prompting
  from langextract import resolver
  from langextract.providers import ollama

  _PROBE_TARGETS = {
      'chunk': (chunking.ChunkIterator, '__iter__'),
      'prompt': (prompting.ContextAwarePromptBuilder, 'build_prompt'),
      'model': (ollama.OllamaLanguageModel, 'infer'),
      'parse': (resolver.Resolver, 'resolve'),
      'align': (resolver.Resolver, 'align'),
  }
  return _PROBE_TARGETS


def _identity_wrap_return(
    original: Callable[..., Any],
) -> Callable[..., Any]:
  """Passthrough that returns the original result (chunk/prompt/parse)."""

  def identity(self: Any, *args: Any, **kwargs: Any) -> Any:
    return original(self, *args, **kwargs)

  return identity


def _identity_wrap_yield(
    original: Callable[..., Any],
) -> Callable[..., Any]:
  """Passthrough that yields each item from the original (model/align)."""

  def identity(self: Any, *args: Any, **kwargs: Any) -> Iterator[Any]:
    yield from original(self, *args, **kwargs)

  return identity


def _restore_probe_attrs(
    saved: list[tuple[type, str, Callable[..., Any]]],
) -> None:
  """Restore class attributes in reverse install order."""
  for cls, attr, original in reversed(saved):
    setattr(cls, attr, original)


_IDENTITY_WRAP_FACTORIES: dict[str, _WrapFactory] = {
    'chunk': _identity_wrap_return,
    'prompt': _identity_wrap_return,
    'model': _identity_wrap_yield,
    'parse': _identity_wrap_return,
    'align': _identity_wrap_yield,
}


def _merge_wrap_factories(
    wrappers: Mapping[str, _WrapFactory] | None,
) -> dict[str, _WrapFactory]:
  """Overlay supplied wrappers on the identity factories, rejecting unknowns."""
  factories = dict(_IDENTITY_WRAP_FACTORIES)
  if wrappers:
    unknown = set(wrappers) - set(_IDENTITY_WRAP_FACTORIES)
    if unknown:
      raise ValueError(
          'unknown wrapper label(s): ' + ', '.join(sorted(unknown))
      )
    factories.update(wrappers)
  return factories


def _install_probes(
    targets: Mapping[str, tuple[type, str]],
    factories: Mapping[str, _WrapFactory],
) -> list[tuple[type, str, Callable[..., Any]]]:
  """Wrap every target; on failure restore the installed ones and re-raise."""
  saved: list[tuple[type, str, Callable[..., Any]]] = []
  try:
    for label, (cls, attr) in targets.items():
      original = cls.__dict__[attr]
      setattr(cls, attr, factories[label](original))
      saved.append((cls, attr, original))
  except Exception:
    _restore_probe_attrs(saved)
    raise
  return saved


@contextlib.contextmanager
def trace_probes(
    wrappers: Mapping[str, _WrapFactory] | None = None,
) -> Iterator[None]:
  """Install call-scoped identity (or supplied) wraps on extract targets.

  Restores every class attribute in finally, including on exception. Nested
  entry is rejected while probes are active.

  :param wrappers: Optional original->replacement factories keyed by catalog
    label (chunk/prompt/model/parse/align). Missing labels fall back to
    identity passthroughs.
  :raises RuntimeError: If probes are already active.
  :raises ValueError: If wrappers contains an unknown label.
  """
  global _PROBES_ACTIVE
  if _PROBES_ACTIVE:
    raise RuntimeError('trace_probes() already active')

  targets = _load_probe_targets()
  factories = _merge_wrap_factories(wrappers)
  saved = _install_probes(targets, factories)
  _PROBES_ACTIVE = True
  try:
    yield
  finally:
    _restore_probe_attrs(saved)
    _PROBES_ACTIVE = False


def _print_block(title: str, payload: Mapping[str, Any]) -> None:
  """Print one in:/out: block; text values pass through _safe_text."""
  print(f'{title}:')
  for key, value in payload.items():
    if isinstance(value, str) and not value:
      print(f"  {key}: ''")
    elif isinstance(value, str):
      print(f'  {key}:')
      print(textwrap.indent(_safe_text(value), '    '))
    elif isinstance(value, (list, tuple)) and all(
        isinstance(v, str) and v for v in value
    ):
      print(f'  {key}:')
      for i, item in enumerate(value):
        print(f'    [{i}]')
        print(textwrap.indent(_safe_text(item), '      '))
    else:
      print(f'  {key}: {pprint.pformat(value)}')


def _parse_callout(parse_error: str | None, config: Mapping[str, Any]) -> str:
  """Pick the callout line for an empty parse from config sentences."""
  if parse_error is None:
    return f"callout: {config['empty_list_message'].strip()}"
  message = config['empty_parse_message'].strip()
  return f'callout: {message}\n  error: {_safe_text(parse_error)}'


def _source_slice(
    source_text: str,
    snap: ExtractionSnapshot,
    char_offset: int,
    ungrounded_label: str,
) -> str:
  """Return the grounded source slice as a repr, or ungrounded_label."""
  if snap.char_interval is None:
    return ungrounded_label
  start, end = snap.char_interval
  return repr(_safe_text(source_text[start - char_offset : end - char_offset]))


def _print_align_section(
    record: StageRecord,
    parse_record: StageRecord | None,
    config: Mapping[str, Any],
) -> None:
  """Print offsets, per-extraction span/status/slice and the parse pair."""
  label = config['ungrounded_label']
  token_offset = record.in_data['token_offset']
  char_offset = record.in_data['char_offset']
  print(
      f'offsets: token_offset={token_offset}  char_offset={char_offset}  '
      f'({config["chunk_offset_caption"]})'
  )
  snaps = record.out_data['extractions']
  for i, snap in enumerate(snaps, start=1):
    span = (
        label
        if snap.char_interval is None
        else _format_interval(snap.char_interval)
    )
    status = label if snap.alignment_status is None else snap.alignment_status
    cut = _source_slice(record.in_data['source_text'], snap, char_offset, label)
    print(
        f'  [{i}] {_safe_text(snap.extraction_class)}: '
        f'{_safe_text(snap.extraction_text)!r}  span={span}  status={status}'
        f'  slice={cut}'
    )
  if parse_record is not None:
    print_grounding_pair(parse_record.out_data['extractions'], snaps, label)


def print_stage_records(
    records: Iterable[StageRecord], config: Mapping[str, Any]
) -> None:
  """Print captured stages in catalog order with marked in/out/path blocks.

  :param records: Records collected by the stage wrappers, in capture order.
  :param config: Config mapping providing the empty-parse callout sentences.
  """
  by_label: dict[str, list[StageRecord]] = {}
  for record in records:
    by_label.setdefault(record.label, []).append(record)
  printed_any = False
  for label, function_name, path in STAGE_CATALOG:
    if label not in by_label:
      continue
    if printed_any:
      print()
    printed_any = True
    print(f'[{label}] {function_name}')
    _print_block('%%%%%%', {'path': path})
    for i, record in enumerate(by_label[label]):
      _print_block('##########', record.in_data)
      if label == 'parse' and not record.out_data['extractions']:
        print(_parse_callout(record.out_data['parse_error'], config))
      _print_block('*******', record.out_data)
      if label == 'align':
        parses = by_label.get('parse', [])
        _print_align_section(
            record, parses[i] if i < len(parses) else None, config
        )


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


def _self_check_probe_restore() -> None:
  """Prove exception-path restore for all five probe targets.

  Silent on success. On any failure prints one Error line to stderr and
  raises SystemExit(1). Does not call lx.extract or contact a model.
  """
  targets = _load_probe_targets()
  originals = {
      label: cls.__dict__[attr] for label, (cls, attr) in targets.items()
  }
  try:
    try:
      with trace_probes():
        for label, (cls, attr) in targets.items():
          if getattr(cls, attr) is originals[label]:
            raise AssertionError(f'{label} was not wrapped')
        raise RuntimeError('probe self-check')
    except RuntimeError as exc:
      if str(exc) != 'probe self-check':
        raise
    for label, (cls, attr) in targets.items():
      if getattr(cls, attr) is not originals[label]:
        raise AssertionError(f'{label} was not restored')
  except Exception as exc:
    print(f'Error: probe self-check failed: {exc}', file=sys.stderr)
    raise SystemExit(1) from exc


class PreflightError(RuntimeError):
  """Raised when the Ollama host or model is not usable."""


def _fetch_tags(model_url: str, host: str, timeout: float) -> bytes:
  """Read at most _MAX_TAGS_BYTES of GET {model_url}/api/tags.

  :param model_url: Base URL of the Ollama server.
  :param host: Host shown in error messages.
  :param timeout: Seconds to wait for the response.
  :return: The raw response body.
  :raises PreflightError: On an HTTP error or an unreachable host.
  """
  url = f'{model_url.rstrip("/")}/api/tags'
  try:
    with urllib.request.urlopen(url, timeout=timeout) as response:
      return response.read(_MAX_TAGS_BYTES)
  except urllib.error.HTTPError as exc:
    raise PreflightError(
        f'Ollama at {host} returned HTTP {exc.code} for /api/tags'
    ) from exc
  except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
    reason = getattr(exc, 'reason', exc)
    raise PreflightError(
        f'Ollama is not reachable at {host} ({reason}). '
        'Start it with: ollama serve'
    ) from exc


def _listed_model_names(body: bytes, host: str) -> set[Any]:
  """Collect every name/model value listed in an /api/tags body.

  :param body: Raw JSON response body.
  :param host: Host shown in error messages.
  :return: The listed values (may include None for entries lacking a key).
  :raises PreflightError: If the body is not the expected structure.
  """
  try:
    entries = json.loads(body)['models']
    return {
        value
        for entry in entries
        for value in (entry.get('name'), entry.get('model'))
    }
  except (ValueError, KeyError, TypeError, AttributeError) as exc:
    raise PreflightError(f'unexpected /api/tags response from {host}') from exc


def preflight_ollama(model_url: str, model_id: str, timeout: float) -> None:
  """Check that model_id is listed by GET {model_url}/api/tags.

  Accepts exactly model_id or model_id + ':latest'; no other tag matches.

  :param model_url: Base URL of the Ollama server (http or https).
  :param model_id: Model name that must be listed.
  :param timeout: Seconds to wait for the response.
  :raises PreflightError: If the URL is invalid, the host is not reachable,
    the response is unusable or the model is not listed.
  """
  parsed = urlparse(model_url)
  if parsed.scheme not in ('http', 'https') or not parsed.netloc:
    raise PreflightError(
        f'model_url must be http(s)://host:port, got {model_url!r}'
    )
  host = _host_from_model_url(model_url)
  body = _fetch_tags(model_url, host, timeout)
  names = _listed_model_names(body, host)
  if model_id not in names and f'{model_id}:latest' not in names:
    available = ', '.join(sorted(n for n in names if n)) or 'none'
    raise PreflightError(
        f'model {model_id} is not available on {host} '
        f'(available: {available}). Run: ollama pull {model_id}'
    )


def _load_document_text(document_path: str | Path) -> str:
  """Read UTF-8 document text; resolve relative paths against the repo root.

  :param document_path: Absolute or repo-relative path from config.
  :return: File contents.
  :raises SystemExit: With code 1 when the file is missing.
  """
  path = Path(document_path)
  if not path.is_absolute():
    path = _REPO_ROOT / path
  path = path.resolve()
  if not path.is_file():
    print(f'Error: document not found: {path}', file=sys.stderr)
    raise SystemExit(1)
  return path.read_text(encoding='utf-8')


def _build_examples(config: Mapping[str, Any]) -> list[Any]:
  """Build lx.data.ExampleData items from config['examples']."""
  import langextract as lx  # pylint: disable=import-outside-toplevel

  return [
      lx.data.ExampleData(
          text=example['text'],
          extractions=[
              lx.data.Extraction(
                  extraction_class=item['extraction_class'],
                  extraction_text=item['extraction_text'],
              )
              for item in example['extractions']
          ],
      )
      for example in config['examples']
  ]


def _extract_kwargs(config: Mapping[str, Any]) -> dict[str, Any]:
  """Build the pinned lx.extract keyword arguments from config.

  :param config: Config mapping with the call constants.
  :return: Keyword arguments for one local-Ollama lx.extract call.
  """
  # pylint: disable=import-outside-toplevel
  from langextract.providers import ollama

  return {
      'text_or_documents': _load_document_text(config['document_path']),
      'prompt_description': config['prompt_description'],
      'examples': _build_examples(config),
      'model_id': config['model_id'],
      'model_url': config['model_url'],
      'max_char_buffer': config['max_char_buffer'],
      'context_window_chars': config['context_window_chars'],
      'resolver_params': {'format_handler': ollama.OLLAMA_FORMAT_HANDLER},
      'language_model_params': {'timeout': config['request_timeout_s']},
      'extraction_passes': 1,
      'debug': False,
      'show_progress': False,
      'fetch_urls': False,
  }


def check_single_inference(
    records: Iterable[StageRecord],
) -> str | None:
  """Return an error if records are not exactly one one-prompt Ollama infer.

  Counts infer calls via distinct model-record in_data identities (Phase 4
  shares one in_data dict per OllamaLanguageModel.infer call).

  :param records: Stage records collected during the live extract.
  :return: None when the single-inference contract holds, else an error string.
  """
  model = [r for r in records if r.label == 'model']
  by_call = {id(r.in_data): r for r in model}
  calls = len(by_call)
  prompts = sum(len(r.in_data['batch_prompts']) for r in by_call.values())
  if calls == 1 and prompts == 1:
    return None
  return (
      'run broke the single-inference contract: expected 1 '
      f'OllamaLanguageModel.infer call with 1 prompt, saw {calls} call(s) / '
      f'{prompts} prompts'
  )


def _refuse_oversized_document(document: str, limit: int) -> int | None:
  """Return exit code 1 when document exceeds the one-chunk ceiling.

  :param document: Loaded document text.
  :param limit: Max chars allowed (typically max_char_buffer).
  :return: 1 if too large, else None.
  """
  if len(document) <= limit:
    return None
  print(
      f'Error: document is {len(document)} chars; keep it ≤ {limit} '
      f'(max_char_buffer, default {_MAX_CHAR_BUFFER}) so the run is one '
      'chunk and one inference',
      file=sys.stderr,
  )
  return 1


def run_live(config: Mapping[str, Any]) -> int:
  """Preflight Ollama, run one traced lx.extract and print the walkthrough.

  :param config: Config mapping with the call constants.
  :return: Process exit code (0 on success).
  :raises PreflightError: If the Ollama host or model is not usable.
  """
  document = _load_document_text(config['document_path'])
  limit = config.get('max_char_buffer', _MAX_CHAR_BUFFER)
  refused = _refuse_oversized_document(document, limit)
  if refused is not None:
    return refused
  preflight_ollama(
      config['model_url'], config['model_id'], config['preflight_timeout_s']
  )
  import langextract as lx  # pylint: disable=import-outside-toplevel

  print_call_header(config)
  sink: list[StageRecord] = []
  try:
    with trace_probes(wrappers=make_stage_wrappers(sink, config)):
      lx.extract(**_extract_kwargs(config))
  finally:
    print_stage_records(sink, config)
  guard_error = check_single_inference(sink)
  if guard_error is not None:
    print(f'Error: {guard_error}', file=sys.stderr)
    return 1
  print(_SINGLE_CALL_LINE)
  return 0


def main(argv: list[str] | None = None) -> int:
  """Run the live traced call, or print the catalog with --catalog-only.

  :param argv: Command-line arguments; defaults to sys.argv[1:].
  :return: Process exit code (0 on success).
  """
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  parser.add_argument(
      '--catalog-only',
      action='store_true',
      help='print the call header and stage catalog without calling Ollama',
  )
  args = parser.parse_args(argv)
  config = load_config(_CONFIG_PATH)
  if not args.catalog_only:
    try:
      return run_live(config)
    except PreflightError as exc:
      print(f'Error: {exc}', file=sys.stderr)
      return 1
  print_call_header(config)
  print_stage_catalog()
  _self_check_probe_restore()
  return 0


if __name__ == '__main__':
  sys.exit(main())

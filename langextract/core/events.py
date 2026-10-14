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

"""Per-chunk extraction observability events."""

from __future__ import annotations

from collections.abc import Callable
import dataclasses
import logging
from typing import ClassVar

from langextract.core import types

__all__ = [
    "ChunkStarted",
    "ChunkFinished",
    "ParseFailed",
    "ExtractionEvent",
    "EventCallback",
    "make_dispatcher",
]


@dataclasses.dataclass(frozen=True)
class ChunkStarted:
  """Emitted when a chunk is about to be sent for inference."""

  name: ClassVar[str] = "chunk_started"
  document_id: str
  chunk_index: int
  char_start: int | None
  char_end: int | None
  pass_index: int
  batch_index: int


@dataclasses.dataclass(frozen=True)
class ChunkFinished:
  """Emitted after a chunk has been resolved and aligned."""

  name: ClassVar[str] = "chunk_finished"
  document_id: str
  chunk_index: int
  char_start: int | None
  char_end: int | None
  pass_index: int
  batch_index: int
  duration_s: float
  num_extractions: int
  outcome: str
  usage: types.TokenUsage | None = None


@dataclasses.dataclass(frozen=True)
class ParseFailed:
  """Emitted when resolver parsing fails for a chunk."""

  name: ClassVar[str] = "parse_failed"
  document_id: str
  chunk_index: int
  char_start: int | None
  char_end: int | None
  pass_index: int
  batch_index: int
  error_type: str
  message: str


ExtractionEvent = ChunkStarted | ChunkFinished | ParseFailed
EventCallback = Callable[[ExtractionEvent], None]


class _Dispatcher:
  """Calls on_event safely; logs the first observer failure only."""

  def __init__(self, on_event: EventCallback | None):
    self._on_event = on_event
    self._logged_failure = False

  def emit(self, event: ExtractionEvent) -> None:
    if self._on_event is None:
      return
    try:
      self._on_event(event)
    except Exception as exc:  # pylint: disable=broad-exception-caught
      if not self._logged_failure:
        logging.warning(
            "on_event observer failed for %s: %s",
            getattr(event, "name", type(event).__name__),
            exc,
        )
        self._logged_failure = True


def make_dispatcher(on_event: EventCallback | None) -> _Dispatcher:
  """Returns a per-run dispatcher for the given observer."""
  return _Dispatcher(on_event)

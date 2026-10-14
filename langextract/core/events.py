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

from absl import logging

from langextract.core import types

__all__ = [
    "ChunkStarted",
    "ChunkFinished",
    "ParseFailed",
    "ExtractionEvent",
    "EventCallback",
    "OUTCOME_OK",
    "OUTCOME_PARSE_ERROR",
]

OUTCOME_OK = "ok"
OUTCOME_PARSE_ERROR = "parse_error"


@dataclasses.dataclass(frozen=True)
class ChunkStarted:
  """Emitted when a chunk is about to be sent for inference."""

  name: str = dataclasses.field(default="chunk_started", init=False)
  document_id: str
  chunk_index: int
  char_start: int | None
  char_end: int | None
  pass_index: int
  batch_index: int


@dataclasses.dataclass(frozen=True)
class ChunkFinished:
  """Emitted after a chunk has been resolved and aligned."""

  name: str = dataclasses.field(default="chunk_finished", init=False)
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

  name: str = dataclasses.field(default="parse_failed", init=False)
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


class Dispatcher:
  """Calls on_event safely; logs the first observer failure only."""

  def __init__(self, on_event: EventCallback | None):
    self._on_event = on_event
    self._logged_failure = False

  @property
  def active(self) -> bool:
    """True when an observer callback is configured."""
    return self._on_event is not None

  def emit(self, event: ExtractionEvent) -> None:
    """Delivers event to on_event; logs only the first observer failure."""
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
            exc_info=True,
        )
        self._logged_failure = True

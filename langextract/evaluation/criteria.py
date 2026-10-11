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

"""Match criteria and exclusive-end span IoU for gold-set evaluation."""

from __future__ import annotations

from collections.abc import Callable
import dataclasses
from typing import Protocol

from langextract.core import data

__all__ = [
    "MatchCriterion",
    "span_iou",
    "SameClass",
    "SpanIoU",
    "AttributesEqual",
    "TextMatch",
]


class MatchCriterion(Protocol):
  """Yes/no match rule comparing a predicted extraction to gold."""

  def __call__(self, predicted: data.Extraction, gold: data.Extraction) -> bool:
    ...


def span_iou(a: data.Extraction, b: data.Extraction) -> float:
  """Intersection-over-union of half-open CharIntervals (exclusive end_pos).

  Returns 0.0 when either interval is missing, incomplete, inverted
  (end < start), adjacent/touching with no overlap, or when union is 0.
  """
  ca, cb = a.char_interval, b.char_interval
  if ca is None or cb is None:
    return 0.0
  s1, e1, s2, e2 = ca.start_pos, ca.end_pos, cb.start_pos, cb.end_pos
  if None in (s1, e1, s2, e2):
    return 0.0
  if e1 < s1 or e2 < s2:
    return 0.0
  inter = max(0, min(e1, e2) - max(s1, s2))
  if inter == 0:
    return 0.0
  union = (e1 - s1) + (e2 - s2) - inter
  return inter / union if union else 0.0


@dataclasses.dataclass(frozen=True)
class SameClass:
  """Match when predicted and gold share the same extraction_class."""

  def __call__(self, predicted: data.Extraction, gold: data.Extraction) -> bool:
    return predicted.extraction_class == gold.extraction_class


@dataclasses.dataclass(frozen=True)
class SpanIoU:
  """Match when span_iou(predicted, gold) >= threshold (default 0.5)."""

  threshold: float = 0.5

  def __call__(self, predicted: data.Extraction, gold: data.Extraction) -> bool:
    return span_iou(predicted, gold) >= self.threshold


@dataclasses.dataclass(frozen=True)
class AttributesEqual:
  """Match when predicted and gold attributes dicts compare equal (==)."""

  def __call__(self, predicted: data.Extraction, gold: data.Extraction) -> bool:
    return predicted.attributes == gold.attributes


@dataclasses.dataclass(frozen=True)
class TextMatch:
  """Match by calling an injected text comparison function (D-02 / D-03)."""

  text_eval_func: Callable[[str, str], bool]

  def __call__(self, predicted: data.Extraction, gold: data.Extraction) -> bool:
    return bool(
        self.text_eval_func(predicted.extraction_text, gold.extraction_text)
    )

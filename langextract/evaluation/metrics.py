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

"""Precision / recall / F1 helpers for gold-set evaluation."""

from __future__ import annotations

import dataclasses

__all__ = [
    "ClassScore",
    "prf_from_counts",
]


@dataclasses.dataclass(frozen=True)
class ClassScore:
  """Per-class or micro-averaged precision, recall, and F1 with raw counts."""

  precision: float
  recall: float
  f1: float
  tp: int
  fp: int
  fn: int


def prf_from_counts(tp: int, fp: int, fn: int) -> ClassScore:
  """Compute precision, recall, and F1 from TP/FP/FN counts.

  When a denominator is zero, the corresponding rate is 0.0 (empty both sides
  yields P=R=F1=0.0).
  """
  precision = tp / (tp + fp) if (tp + fp) else 0.0
  recall = tp / (tp + fn) if (tp + fn) else 0.0
  f1 = (
      (2.0 * precision * recall / (precision + recall))
      if (precision + recall)
      else 0.0
  )
  return ClassScore(
      precision=precision, recall=recall, f1=f1, tp=tp, fp=fp, fn=fn
  )

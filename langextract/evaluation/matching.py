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

"""Greedy one-to-one matching of predicted extractions to gold."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from langextract.core import data
from langextract.evaluation.criteria import MatchCriterion
from langextract.evaluation.criteria import span_iou

__all__ = [
    "greedy_match",
]


def greedy_match(
    predicted: Sequence[data.Extraction],
    gold: Sequence[data.Extraction],
    criteria: Sequence[MatchCriterion],
    score_fn: Callable[[data.Extraction, data.Extraction], float] | None = None,
) -> list[tuple[int, int]]:
  """Assign predicted extractions to gold with greedy 1:1 matching.

  Candidates are pairs that pass every MatchCriterion. Ranking uses
  ``score_fn`` (default ``span_iou``). Sort key is exactly
  ``(-score, pred_index, gold_index)`` so equal IoU (or equal custom
  scores) prefer lower prediction index, then lower gold index. Walk
  assigns a pair when both indices are still unused. Empty ``predicted``
  or ``gold`` returns ``[]``.

  Complexity is O(n*m) in the lengths of ``predicted`` and ``gold``.
  """
  if not predicted or not gold:
    return []
  ranking_score = score_fn if score_fn is not None else span_iou
  candidates: list[tuple[float, int, int]] = []
  for pred_index, pred_extraction in enumerate(predicted):
    for gold_index, gold_extraction in enumerate(gold):
      if all(
          criterion(pred_extraction, gold_extraction) for criterion in criteria
      ):
        score = ranking_score(pred_extraction, gold_extraction)
        candidates.append((score, pred_index, gold_index))
  # Sort key (-score, pred_index, gold_index): IoU-desc, then lower indices.
  candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
  used_pred: set[int] = set()
  used_gold: set[int] = set()
  matches: list[tuple[int, int]] = []
  for _score, pred_index, gold_index in candidates:
    if pred_index in used_pred or gold_index in used_gold:
      continue
    used_pred.add(pred_index)
    used_gold.add(gold_index)
    matches.append((pred_index, gold_index))
  return matches

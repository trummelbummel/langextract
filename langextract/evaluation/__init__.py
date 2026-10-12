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

"""Gold-set evaluation metrics package."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
import dataclasses
from typing import Protocol

from langextract.core import data

__all__ = [
    "AttributesEqual",
    "ClassScore",
    "EvaluationReport",
    "Evaluator",
    "MatchCriterion",
    "SameClass",
    "SpanIoU",
    "TextMatch",
    "evaluate",
    "greedy_match",
    "prf_from_counts",
    "report_from_counts",
    "span_iou",
]


class Evaluator:
  """Gold-set evaluation: metrics, matching, criteria, and orchestration."""

  class MatchCriterion(Protocol):
    """Yes/no match rule comparing a predicted extraction to gold."""

    def __call__(
        self, predicted: data.Extraction, gold: data.Extraction
    ) -> bool:
      ...

  @staticmethod
  def span_iou(predicted: data.Extraction, gold: data.Extraction) -> float:
    """Intersection-over-union of half-open CharIntervals (exclusive end_pos).

    Returns 0.0 when either interval is missing, incomplete, inverted
    (end < start), adjacent/touching with no overlap, or when union is 0.
    """
    predicted_interval = predicted.char_interval
    gold_interval = gold.char_interval
    if predicted_interval is None or gold_interval is None:
      return 0.0
    start1 = predicted_interval.start_pos
    end1 = predicted_interval.end_pos
    start2 = gold_interval.start_pos
    end2 = gold_interval.end_pos
    if None in (start1, end1, start2, end2):
      return 0.0
    if end1 < start1 or end2 < start2:
      return 0.0
    inter = max(0, min(end1, end2) - max(start1, start2))
    if inter == 0:
      return 0.0
    union = (end1 - start1) + (end2 - start2) - inter
    return inter / union if union else 0.0

  @dataclasses.dataclass(frozen=True)
  class SameClass:
    """Match when predicted and gold share the same extraction_class."""

    def __call__(
        self, predicted: data.Extraction, gold: data.Extraction
    ) -> bool:
      return predicted.extraction_class == gold.extraction_class

  @dataclasses.dataclass(frozen=True)
  class SpanIoU:
    """Match when span_iou(predicted, gold) >= threshold (default 0.5)."""

    threshold: float = 0.5

    def __call__(
        self, predicted: data.Extraction, gold: data.Extraction
    ) -> bool:
      return Evaluator.span_iou(predicted, gold) >= self.threshold

  @dataclasses.dataclass(frozen=True)
  class AttributesEqual:
    """Match when predicted and gold attributes dicts compare equal (==)."""

    def __call__(
        self, predicted: data.Extraction, gold: data.Extraction
    ) -> bool:
      return predicted.attributes == gold.attributes

  @dataclasses.dataclass(frozen=True)
  class TextMatch:
    """Match by calling an injected text comparison function (D-02 / D-03)."""

    text_eval_func: Callable[[str, str], bool]

    def __call__(
        self, predicted: data.Extraction, gold: data.Extraction
    ) -> bool:
      return bool(
          self.text_eval_func(predicted.extraction_text, gold.extraction_text)
      )

  @dataclasses.dataclass(frozen=True)
  class ClassScore:
    """Per-class or micro-averaged precision, recall, and F1 with raw counts."""

    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int

  @dataclasses.dataclass
  class EvaluationReport:
    """Per-class and micro-averaged scores from gold-set evaluation."""

    per_class: dict[str, Evaluator.ClassScore]
    micro: Evaluator.ClassScore

  @staticmethod
  def prf_from_counts(tp: int, fp: int, fn: int) -> Evaluator.ClassScore:
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
    return Evaluator.ClassScore(
        precision=precision, recall=recall, f1=f1, tp=tp, fp=fp, fn=fn
    )

  @staticmethod
  def report_from_counts(
      per_class_counts: Mapping[str, tuple[int, int, int]],
      micro: tuple[int, int, int],
  ) -> Evaluator.EvaluationReport:
    """Build an EvaluationReport from per-class and micro TP/FP/FN triples.

    Micro is computed from the global micro triple via prf_from_counts (not a
    mean of per-class F1). Per-class keys are sorted alphabetically.
    """
    per_class = {
        name: Evaluator.prf_from_counts(tp, fp, fn)
        for name, (tp, fp, fn) in sorted(per_class_counts.items())
    }
    return Evaluator.EvaluationReport(
        per_class=per_class,
        micro=Evaluator.prf_from_counts(*micro),
    )

  @staticmethod
  def greedy_match(
      predicted: Sequence[data.Extraction],
      gold: Sequence[data.Extraction],
      criteria: Sequence[Evaluator.MatchCriterion],
      score_fn: (
          Callable[[data.Extraction, data.Extraction], float] | None
      ) = None,
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
    ranking_score = score_fn if score_fn is not None else Evaluator.span_iou
    candidates: list[tuple[float, int, int]] = []
    for pred_index, pred_extraction in enumerate(predicted):
      for gold_index, gold_extraction in enumerate(gold):
        if all(
            criterion(pred_extraction, gold_extraction)
            for criterion in criteria
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

  @staticmethod
  def evaluate(
      predicted: Sequence[data.AnnotatedDocument],
      gold: Sequence[data.AnnotatedDocument],
      *,
      iou_threshold: float = 0.5,
      match_attributes: bool = False,
      text_eval_func: Callable[[str, str], bool] | None = None,
      criteria: Sequence[Evaluator.MatchCriterion] | None = None,
  ) -> Evaluator.EvaluationReport:
    """Score predicted AnnotatedDocuments against a gold set.

    Pairs documents by ``document_id`` (identical ID sets required; duplicates
    within a side raise ``ValueError``). Per document, runs ``greedy_match``
    then aggregates TP/FP/FN into per-class and micro scores. ``criteria=`` is
    mutually exclusive with non-default convenience flags.
    """
    return _evaluate_documents(
        predicted,
        gold,
        iou_threshold=iou_threshold,
        match_attributes=match_attributes,
        text_eval_func=text_eval_func,
        criteria=criteria,
    )


MatchCriterion = Evaluator.MatchCriterion
span_iou = Evaluator.span_iou
SameClass = Evaluator.SameClass
SpanIoU = Evaluator.SpanIoU
AttributesEqual = Evaluator.AttributesEqual
TextMatch = Evaluator.TextMatch
ClassScore = Evaluator.ClassScore
EvaluationReport = Evaluator.EvaluationReport
prf_from_counts = Evaluator.prf_from_counts
report_from_counts = Evaluator.report_from_counts
greedy_match = Evaluator.greedy_match
evaluate = Evaluator.evaluate


def _index_by_document_id(
    documents: Sequence[data.AnnotatedDocument],
    *,
    side: str,
) -> dict[str, data.AnnotatedDocument]:
  """Map document_id → document; raise ValueError on duplicate IDs."""
  indexed: dict[str, data.AnnotatedDocument] = {}
  for document in documents:
    document_id = document.document_id
    if document_id in indexed:
      raise ValueError(
          f"Duplicate document_id {document_id!r} in {side} documents"
      )
    indexed[document_id] = document
  return indexed


def _resolve_criteria(
    *,
    iou_threshold: float,
    match_attributes: bool,
    text_eval_func: Callable[[str, str], bool] | None,
    criteria: Sequence[MatchCriterion] | None,
) -> list[MatchCriterion]:
  """Build MatchCriterion list from convenience flags or explicit criteria."""
  if criteria is not None:
    if iou_threshold != 0.5 or match_attributes or text_eval_func is not None:
      raise ValueError(
          "criteria= is mutually exclusive with non-default convenience"
          " flags (iou_threshold, match_attributes, text_eval_func)"
      )
    return list(criteria)
  resolved: list[MatchCriterion] = [
      SameClass(),
      SpanIoU(iou_threshold),
  ]
  if match_attributes:
    resolved.append(AttributesEqual())
  if text_eval_func is not None:
    resolved.append(TextMatch(text_eval_func))
  return resolved


def _evaluate_documents(
    predicted: Sequence[data.AnnotatedDocument],
    gold: Sequence[data.AnnotatedDocument],
    *,
    iou_threshold: float = 0.5,
    match_attributes: bool = False,
    text_eval_func: Callable[[str, str], bool] | None = None,
    criteria: Sequence[MatchCriterion] | None = None,
) -> EvaluationReport:
  """Score predicted AnnotatedDocuments against a gold set (implementation)."""
  match_criteria = _resolve_criteria(
      iou_threshold=iou_threshold,
      match_attributes=match_attributes,
      text_eval_func=text_eval_func,
      criteria=criteria,
  )
  predicted_by_id = _index_by_document_id(predicted, side="predicted")
  gold_by_id = _index_by_document_id(gold, side="gold")
  predicted_ids = set(predicted_by_id)
  gold_ids = set(gold_by_id)
  if predicted_ids != gold_ids:
    only_predicted = sorted(predicted_ids - gold_ids)
    only_gold = sorted(gold_ids - predicted_ids)
    raise ValueError(
        "predicted and gold document_id sets must be identical;"
        f" only in predicted: {only_predicted}; only in gold: {only_gold}"
    )

  per_class_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
  micro_tp = micro_fp = micro_fn = 0
  for document_id in sorted(predicted_ids):
    pred_extractions = predicted_by_id[document_id].extractions or []
    gold_extractions = gold_by_id[document_id].extractions or []
    matches = greedy_match(pred_extractions, gold_extractions, match_criteria)
    matched_pred = {pred_index for pred_index, _ in matches}
    matched_gold = {gold_index for _, gold_index in matches}
    for pred_index, _gold_index in matches:
      class_name = pred_extractions[pred_index].extraction_class
      per_class_counts[class_name][0] += 1
      micro_tp += 1
    for pred_index, pred_extraction in enumerate(pred_extractions):
      if pred_index not in matched_pred:
        class_name = pred_extraction.extraction_class
        per_class_counts[class_name][1] += 1
        micro_fp += 1
    for gold_index, gold_extraction in enumerate(gold_extractions):
      if gold_index not in matched_gold:
        class_name = gold_extraction.extraction_class
        per_class_counts[class_name][2] += 1
        micro_fn += 1

  per_class_triples = {
      name: (counts[0], counts[1], counts[2])
      for name, counts in per_class_counts.items()
  }
  return report_from_counts(per_class_triples, (micro_tp, micro_fp, micro_fn))

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

"""Gold-set evaluation metrics implementation."""

from __future__ import annotations

import collections
from collections.abc import Callable, Mapping, Sequence
import dataclasses
from typing import NamedTuple, Protocol

from langextract.core import data

_DEFAULT_IOU_THRESHOLD = 0.5

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


@dataclasses.dataclass
class _CountTriple:
  """Mutable TP/FP/FN bucket for one extraction class during aggregation."""

  true_positives: int = 0
  false_positives: int = 0
  false_negatives: int = 0


class _Candidate(NamedTuple):
  """A predicted/gold pair that passed every criterion, with its rank score."""

  score: float
  pred_index: int
  gold_index: int


class Evaluator:
  """Gold-set evaluation: metrics, matching, criteria, and orchestration."""

  class MatchCriterion(Protocol):
    """Yes/no match rule comparing a predicted extraction to gold."""

    def __call__(
        self,
        predicted: data.Extraction,
        gold: data.Extraction,
    ) -> bool:
      """Returns True when predicted and gold are considered a match.

      Args:
        predicted: Model extraction under test.
        gold: Reference extraction from the gold set.
      """
      ...

  @staticmethod
  def span_iou(predicted: data.Extraction, gold: data.Extraction) -> float:
    """Intersection-over-union of half-open CharIntervals (exclusive end_pos).

    Returns 0.0 when either interval is missing, incomplete, inverted
    (end < start), adjacent/touching with no overlap, or when union is 0.

    Args:
      predicted: Extraction whose ``char_interval`` is the hypothesis span.
      gold: Extraction whose ``char_interval`` is the reference span.

    Returns:
      IoU in ``[0.0, 1.0]``.
    """
    predicted_interval = predicted.char_interval
    gold_interval = gold.char_interval
    if predicted_interval is None or gold_interval is None:
      return 0.0
    pred_start = predicted_interval.start_pos
    pred_end = predicted_interval.end_pos
    gold_start = gold_interval.start_pos
    gold_end = gold_interval.end_pos
    if None in (pred_start, pred_end, gold_start, gold_end):
      return 0.0
    if pred_end < pred_start or gold_end < gold_start:
      return 0.0
    overlap = max(0, min(pred_end, gold_end) - max(pred_start, gold_start))
    if overlap == 0:
      return 0.0
    union = (pred_end - pred_start) + (gold_end - gold_start) - overlap
    return overlap / union

  @dataclasses.dataclass(frozen=True)
  class SameClass:
    """Match when predicted and gold share the same extraction_class."""

    def __call__(
        self,
        predicted: data.Extraction,
        gold: data.Extraction,
    ) -> bool:
      """Returns True when both extractions share ``extraction_class``."""
      return predicted.extraction_class == gold.extraction_class

  @dataclasses.dataclass(frozen=True)
  class SpanIoU:
    """Match when span_iou(predicted, gold) >= threshold (default 0.5)."""

    threshold: float = _DEFAULT_IOU_THRESHOLD

    def __call__(
        self,
        predicted: data.Extraction,
        gold: data.Extraction,
    ) -> bool:
      """Returns True when span IoU meets ``threshold``."""
      return Evaluator.span_iou(predicted, gold) >= self.threshold

  @dataclasses.dataclass(frozen=True)
  class AttributesEqual:
    """Match when predicted and gold attributes dicts compare equal (==)."""

    def __call__(
        self,
        predicted: data.Extraction,
        gold: data.Extraction,
    ) -> bool:
      """Returns True when ``attributes`` dicts compare equal."""
      return predicted.attributes == gold.attributes

  @dataclasses.dataclass(frozen=True)
  class TextMatch:
    """Match by calling an injected text comparison function."""

    text_eval_func: Callable[[str, str], bool]

    def __call__(
        self,
        predicted: data.Extraction,
        gold: data.Extraction,
    ) -> bool:
      """Returns True when ``text_eval_func`` accepts both extraction texts."""
      return self.text_eval_func(
          predicted.extraction_text,
          gold.extraction_text,
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

  @dataclasses.dataclass(frozen=True)
  class EvaluationReport:
    """Per-class and micro-averaged scores from gold-set evaluation."""

    per_class: Mapping[str, Evaluator.ClassScore]
    micro: Evaluator.ClassScore

  @staticmethod
  def prf_from_counts(tp: int, fp: int, fn: int) -> Evaluator.ClassScore:
    """Compute precision, recall, and F1 from TP/FP/FN counts.

    When a denominator is zero, the corresponding rate is 0.0 (empty both sides
    yields P=R=F1=0.0).

    Args:
      tp: True-positive count.
      fp: False-positive count.
      fn: False-negative count.

    Returns:
      Precision, recall and F1 plus the raw counts.
    """
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        (2.0 * precision * recall / (precision + recall))
        if (precision + recall)
        else 0.0
    )
    return Evaluator.ClassScore(
        precision=precision,
        recall=recall,
        f1=f1,
        tp=tp,
        fp=fp,
        fn=fn,
    )

  @staticmethod
  def report_from_counts(
      per_class_counts: Mapping[str, tuple[int, int, int]],
      micro: tuple[int, int, int],
  ) -> Evaluator.EvaluationReport:
    """Build an EvaluationReport from per-class and micro TP/FP/FN triples.

    Micro is computed from the global micro triple via prf_from_counts (not a
    mean of per-class F1). Per-class keys are sorted alphabetically.

    Args:
      per_class_counts: Map of class name → ``(tp, fp, fn)``.
      micro: Global ``(tp, fp, fn)`` across all classes.

    Returns:
      Per-class and micro ``ClassScore`` report.
    """
    per_class = {
        name: Evaluator.prf_from_counts(true_pos, false_pos, false_neg)
        for name, (true_pos, false_pos, false_neg) in sorted(
            per_class_counts.items()
        )
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

    Args:
      predicted: Extractions from the model side.
      gold: Extractions from the gold side.
      criteria: All must return True for a pair to be a candidate.
      score_fn: Ranking score; defaults to ``span_iou``.

    Returns:
      ``(pred_index, gold_index)`` assignments in selection order.
    """
    if not predicted or not gold:
      return []
    ranking_score = score_fn if score_fn is not None else Evaluator.span_iou
    candidates = _candidate_pairs(
        predicted,
        gold,
        criteria,
        ranking_score,
    )
    candidates.sort(key=_best_score_then_lowest_index)
    return _select_one_to_one(candidates)

  @staticmethod
  def evaluate(
      predicted: Sequence[data.AnnotatedDocument],
      gold: Sequence[data.AnnotatedDocument],
      *,
      iou_threshold: float = _DEFAULT_IOU_THRESHOLD,
      match_attributes: bool = False,
      text_eval_func: Callable[[str, str], bool] | None = None,
      criteria: Sequence[Evaluator.MatchCriterion] | None = None,
  ) -> Evaluator.EvaluationReport:
    """Score predicted AnnotatedDocuments against a gold set.

    Pairs documents by ``document_id`` (identical ID sets required; duplicates
    within a side raise ``ValueError``). Per document, runs ``greedy_match``
    then aggregates TP/FP/FN into per-class and micro scores. ``criteria=`` is
    mutually exclusive with non-default convenience flags.

    Args:
      predicted: Model-side annotated documents.
      gold: Gold-set annotated documents (same ``document_id`` set).
      iou_threshold: ``SpanIoU`` threshold used when building default criteria.
      match_attributes: When True, also require ``AttributesEqual``.
      text_eval_func: Optional text comparator, wrapped as ``TextMatch``.
      criteria: Explicit criterion list; exclusive with the convenience flags.

    Returns:
      Per-class and micro evaluation report.

    Raises:
      ValueError: On duplicate or mismatched ``document_id`` sets, or when
        ``criteria`` is combined with non-default convenience flags.
    """
    match_criteria = _resolve_criteria(
        iou_threshold=iou_threshold,
        match_attributes=match_attributes,
        text_eval_func=text_eval_func,
        criteria=criteria,
    )
    predicted_by_id = _index_by_document_id(predicted, side="predicted")
    gold_by_id = _index_by_document_id(gold, side="gold")
    document_ids = _require_identical_document_ids(predicted_by_id, gold_by_id)
    per_class_counts = _aggregate_per_class_counts(
        document_ids,
        predicted_by_id,
        gold_by_id,
        match_criteria,
    )
    return _evaluation_report_from_count_triples(per_class_counts)


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


def _candidate_pairs(
    predictions: Sequence[data.Extraction],
    references: Sequence[data.Extraction],
    criteria: Sequence[MatchCriterion],
    ranking_score: Callable[[data.Extraction, data.Extraction], float],
) -> list[_Candidate]:
  """Score every predicted/gold pair that passes all criteria."""
  candidates: list[_Candidate] = []
  for pred_index, prediction in enumerate(predictions):
    for gold_index, reference in enumerate(references):
      if all(criterion(prediction, reference) for criterion in criteria):
        score = ranking_score(prediction, reference)
        candidates.append(_Candidate(score, pred_index, gold_index))
  return candidates


def _best_score_then_lowest_index(
    candidate: _Candidate,
) -> tuple[float, int, int]:
  return (-candidate.score, candidate.pred_index, candidate.gold_index)


def _select_one_to_one(
    ranked: Sequence[_Candidate],
) -> list[tuple[int, int]]:
  """Walk ranked candidates, keeping a pair only if both sides are unused."""
  used_pred: set[int] = set()
  used_gold: set[int] = set()
  matches: list[tuple[int, int]] = []
  for candidate in ranked:
    if candidate.pred_index in used_pred or candidate.gold_index in used_gold:
      continue
    used_pred.add(candidate.pred_index)
    used_gold.add(candidate.gold_index)
    matches.append((candidate.pred_index, candidate.gold_index))
  return matches


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
    if (
        iou_threshold != _DEFAULT_IOU_THRESHOLD
        or match_attributes
        or text_eval_func is not None
    ):
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


def _require_identical_document_ids(
    predicted_by_id: Mapping[str, data.AnnotatedDocument],
    gold_by_id: Mapping[str, data.AnnotatedDocument],
) -> list[str]:
  """Return sorted shared document ids, or raise if ID sets differ."""
  predicted_ids = set(predicted_by_id)
  gold_ids = set(gold_by_id)
  if predicted_ids != gold_ids:
    only_predicted = sorted(predicted_ids - gold_ids)
    only_gold = sorted(gold_ids - predicted_ids)
    raise ValueError(
        "predicted and gold document_id sets must be identical;"
        f" only in predicted: {only_predicted}; only in gold: {only_gold}"
    )
  return sorted(predicted_ids)


def _counts_for_document(
    predictions: Sequence[data.Extraction],
    references: Sequence[data.Extraction],
    match_criteria: Sequence[MatchCriterion],
) -> dict[str, _CountTriple]:
  """Greedy-match one document; return TP/FP/FN counts per extraction class.

  A match counts as TP under the prediction's class; an unmatched prediction
  is FP under its class and an unmatched reference is FN under its class.
  """
  per_class_counts: dict[str, _CountTriple] = collections.defaultdict(
      _CountTriple,
  )
  matches = greedy_match(predictions, references, match_criteria)
  matched_pred = {pred_index for pred_index, _ in matches}
  matched_gold = {gold_index for _, gold_index in matches}
  for pred_index, prediction in enumerate(predictions):
    counts = per_class_counts[prediction.extraction_class]
    if pred_index in matched_pred:
      counts.true_positives += 1
    else:
      counts.false_positives += 1
  for gold_index, reference in enumerate(references):
    if gold_index not in matched_gold:
      per_class_counts[reference.extraction_class].false_negatives += 1
  return per_class_counts


def _aggregate_per_class_counts(
    document_ids: Sequence[str],
    predicted_by_id: Mapping[str, data.AnnotatedDocument],
    gold_by_id: Mapping[str, data.AnnotatedDocument],
    match_criteria: Sequence[MatchCriterion],
) -> dict[str, _CountTriple]:
  """Sum per-class TP/FP/FN across documents that share the same id set."""
  per_class_counts: dict[str, _CountTriple] = collections.defaultdict(
      _CountTriple,
  )
  for document_id in document_ids:
    predictions = predicted_by_id[document_id].extractions or []
    references = gold_by_id[document_id].extractions or []
    for name, doc_counts in _counts_for_document(
        predictions,
        references,
        match_criteria,
    ).items():
      total = per_class_counts[name]
      total.true_positives += doc_counts.true_positives
      total.false_positives += doc_counts.false_positives
      total.false_negatives += doc_counts.false_negatives
  return per_class_counts


def _evaluation_report_from_count_triples(
    per_class_counts: Mapping[str, _CountTriple],
) -> Evaluator.EvaluationReport:
  """Build EvaluationReport from private per-class count buckets."""
  per_class_triples = {
      name: (
          counts.true_positives,
          counts.false_positives,
          counts.false_negatives,
      )
      for name, counts in per_class_counts.items()
  }
  micro_counts = _CountTriple()
  for counts in per_class_counts.values():
    micro_counts.true_positives += counts.true_positives
    micro_counts.false_positives += counts.false_positives
    micro_counts.false_negatives += counts.false_negatives
  micro = (
      micro_counts.true_positives,
      micro_counts.false_positives,
      micro_counts.false_negatives,
  )
  return Evaluator.report_from_counts(per_class_triples, micro)

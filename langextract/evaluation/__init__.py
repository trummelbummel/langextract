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
from collections.abc import Callable, Sequence

from langextract.core import data
from langextract.evaluation.criteria import AttributesEqual
from langextract.evaluation.criteria import MatchCriterion
from langextract.evaluation.criteria import SameClass
from langextract.evaluation.criteria import span_iou
from langextract.evaluation.criteria import SpanIoU
from langextract.evaluation.criteria import TextMatch
from langextract.evaluation.matching import greedy_match
from langextract.evaluation.metrics import ClassScore
from langextract.evaluation.metrics import EvaluationReport
from langextract.evaluation.metrics import prf_from_counts
from langextract.evaluation.metrics import report_from_counts

__all__ = [
    "AttributesEqual",
    "ClassScore",
    "EvaluationReport",
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


def evaluate(
    predicted: Sequence[data.AnnotatedDocument],
    gold: Sequence[data.AnnotatedDocument],
    *,
    iou_threshold: float = 0.5,
    match_attributes: bool = False,
    text_eval_func: Callable[[str, str], bool] | None = None,
    criteria: Sequence[MatchCriterion] | None = None,
) -> EvaluationReport:
  """Score predicted AnnotatedDocuments against a gold set.

  Pairs documents by ``document_id`` (identical ID sets required; duplicates
  within a side raise ``ValueError``). Per document, runs ``greedy_match``
  then aggregates TP/FP/FN into per-class and micro scores.
  """
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

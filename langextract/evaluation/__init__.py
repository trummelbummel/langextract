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

from langextract.evaluation.evaluation import AttributesEqual
from langextract.evaluation.evaluation import ClassScore
from langextract.evaluation.evaluation import evaluate
from langextract.evaluation.evaluation import EvaluationReport
from langextract.evaluation.evaluation import Evaluator
from langextract.evaluation.evaluation import greedy_match
from langextract.evaluation.evaluation import MatchCriterion
from langextract.evaluation.evaluation import prf_from_counts
from langextract.evaluation.evaluation import report_from_counts
from langextract.evaluation.evaluation import SameClass
from langextract.evaluation.evaluation import span_iou
from langextract.evaluation.evaluation import SpanIoU
from langextract.evaluation.evaluation import TextMatch

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

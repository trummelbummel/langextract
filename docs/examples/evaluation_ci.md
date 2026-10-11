# Gold-set Evaluation in CI

Use `lx.evaluation.evaluate` to score predicted extractions against a labeled
gold set and assert micro F1 in CI—no live models or network calls required.
Always set explicit `document_id` values so predicted and gold documents pair;
`CharInterval` uses an exclusive `end_pos`.

```python
import langextract as lx

text = "Patient has asthma."
span = lx.data.CharInterval(start_pos=12, end_pos=18)  # exclusive end
extraction = lx.data.Extraction(
    extraction_class="condition",
    extraction_text="asthma",
    char_interval=span,
)
gold = [
    lx.data.AnnotatedDocument(
        document_id="doc-1", text=text, extractions=[extraction]
    )
]
predicted = [
    lx.data.AnnotatedDocument(
        document_id="doc-1", text=text, extractions=[extraction]
    )
]

report = lx.evaluation.evaluate(predicted, gold)
assert report.micro.f1 == 1.0
```

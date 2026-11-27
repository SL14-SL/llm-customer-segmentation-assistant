# Testing, CI and model evaluation

[Back to project overview](../README.md)

## Validation and evaluation

The project separates automated software tests from live-model
evaluation.

Automated tests verify deterministic behavior. Live-model
evaluations additionally exercise natural-language interpretation
with a running Ollama model.

### Evaluation overview

Historical pre-refactoring results recorded on 2026-11-26 (not a new evaluation of the refactored code):

| Validation | Model | Result |
| --- | --- | --- |
| Automated tests | Not required | 179 passed |
| Ruff linting | Not required | Passed |
| Text-to-SQL reference evaluation | `qwen2.5-coder:3b` | 8/9 cases; failed case passed on targeted rerun |
| Single-segment tool-decision evaluation | `qwen2.5-coder:3b` | 7/7 automatic checks |
| Comparison clarification check | `qwen2.5:14b` | Passed |
| Comparison end-to-end evaluation | `qwen2.5:14b` | 8/8 cases |
| Docker startup and health checks | Both default models | Passed |
| Docker Text-to-SQL functional smoke test | `qwen2.5-coder:3b` | Passed |
| Docker comparison criteria and clarification | `qwen2.5:14b` | Passed |
| Docker deterministic scope rejection | Not required | Passed |

The evaluation suites are small development reference suites,
not independent general-accuracy benchmarks.

Results depend on the selected model and implementation version.

### Refactoring verification (2026-11-27)

| Check | Result |
| --- | --- |
| Full local automated suite | 296 passed |
| Streamlit AppTest integration tests (included above) | 7 Text-to-SQL + 11 comparison passed |
| Ruff and Compose validation | Passed |
| Local model-free smoke scripts | Both passed |
| Shell syntax | Passed |
| Updated GitHub Actions matrix | Pending execution |
| Post-refactoring live-model evaluations and full Docker verification | Pending |

The 296 tests include configuration, shared Ollama transport, typed errors, adapter contracts, shared criteria validation and Streamlit regression tests. The UI tests simulate model responses but exercise real conversation logic and synthetic DuckDB queries. They do not require Ollama or browser automation.

### Automated checks

```bash
uv run ruff check src tests scripts \
  streamlit_app.py streamlit_agent_demo.py
```

```bash
uv run pytest -q
```

The test suite covers:

- Structured decision parsing.
- SQL policy enforcement.
- Read-only query behavior.
- Result-limit enforcement.
- Clarification state.
- Export behavior.
- Tool argument validation.
- Comparison criteria validation.
- Probability threshold normalization.
- Inclusive probability boundary handling.
- Equivalent probability threshold handling.
- Deterministic scope validation.
- Unsupported requirements in clarification answers.
- Rejection before model inference.
- State-dependent action restrictions.
- Tool-call limits.
- Deterministic result reporting.
- Synthetic dataset schema.
- Dataset reproducibility.
- Preservation of existing database files.
- Failed database creation without publishing incomplete files.

Automated tests do not establish general natural-language
accuracy.

### Text-to-SQL reference evaluation

```bash
OLLAMA_MODEL=qwen2.5-coder:3b \
uv run python scripts/evaluate_assistant.py
```

A historical development run passed 9 of 9 reference cases.

The complete run on 2026-11-26 passed 8 of 9 cases.
The remaining clarification follow-up case passed after
improvements to the evaluation script and targeted re-execution.

Run the clarification case independently:

```bash
OLLAMA_MODEL=qwen2.5-coder:3b \
uv run python scripts/evaluate_assistant.py \
  --case high_risk_after_clarification
```

The targeted result does not constitute a new complete
9/9 evaluation run.

Covered behaviors include:

- Customer counts.
- Combined filters.
- Percentage thresholds.
- Missing values.
- Grouped aggregates.
- Ranked customer lists.
- Clarification follow-ups.

Query evaluation compares returned values while ignoring
output aliases.

Row order is checked when required.

Standalone clarification wording requires manual review.

Unsupported responses were checked manually and were not
included in these nine reference cases.

### Single-segment tool-decision evaluation

```bash
OLLAMA_MODEL=qwen2.5-coder:3b \
uv run python scripts/evaluate_tools.py
```

The development run on 2026-11-26 passed 7 of 7 automatic
checks.

Clarification wording was additionally reviewed manually.

These cases evaluate single-segment decisions rather than
the complete comparison agent.

### Comparison clarification check

```bash
OLLAMA_MODEL=qwen2.5:14b \
uv run python scripts/check_comparison_dialogue.py
```

This live-model check verifies that a threshold follow-up
preserves the previously selected contract types.

The check passed on 2026-11-26 using the recommended
14B comparison model.

It requires a running Ollama model.

### Comparison end-to-end evaluation

```bash
OLLAMA_MODEL=qwen2.5:14b \
uv run python scripts/evaluate_comparison.py
```

The development run on 2026-11-26 passed all 8 cases
using `qwen2.5:14b`, including the updated criteria
extraction and deterministic scope guard.

A historical run on 2026-11-11 also passed all 8 cases
with the same model.

Covered behaviors include:

- Two-contract comparisons.
- Three-contract comparisons.
- Empty segments.
- Threshold clarification.
- Rejection of unsupported tenure filters.
- Rejection of unsupported monthly-charge filters.
- Rejection of different per-segment thresholds.
- Rejection of additional filters in follow-up messages.

The smaller `qwen2.5-coder:3b` model produced less reliable
comparison results during development.

Observed failure modes included incomplete contract extraction
and omitted unsupported requirements.

For this reason, `qwen2.5:14b` is the default Docker comparison
model and the recommended model for local comparison evaluation.

The 8/8 result applies to the tested 14B model and reference
cases. It does not establish equivalent accuracy for smaller
models or arbitrary user requests.

### Targeted evaluation runs

The Text-to-SQL and comparison evaluation scripts support
the optional `--case` argument.

For example:

```bash
OLLAMA_MODEL=qwen2.5:14b \
uv run python scripts/evaluate_comparison.py \
  --case both_segments_empty
```

Multiple cases can be selected:

```bash
OLLAMA_MODEL=qwen2.5:14b \
uv run python scripts/evaluate_comparison.py \
  --case both_segments_empty \
  --case threshold_follow_up
```

Without `--case`, the complete reference suite is executed.

Targeted runs reduce inference time during debugging and
regression analysis.

A targeted run does not replace a complete evaluation after
changes affecting shared prompts or execution logic.

### Docker verification

Both containerized interfaces were manually tested
on 2026-11-26.

The earlier Docker configuration used the smaller
`qwen2.5-coder:3b` model for both applications.

The updated configuration was additionally verified with
separate models:

- Text-to-SQL: `qwen2.5-coder:3b`.
- Segment Comparison: `qwen2.5:14b`.

Verified behavior includes:

- Successful initialization of both models.
- Healthy Ollama server.
- Healthy Text-to-SQL application.
- Healthy comparison application.
- Independent application model configuration.
- Successful communication with the shared Ollama server.
- Text-to-SQL query returning the expected 300 customers.
- Comparison contract extraction and clarification with the 14B model.
- Correct preservation of the selected contracts.
- Correct normalization of the probability threshold.
- Deterministic rejection of unsupported tenure filters.
- Correct display of unsupported requirements in the comparison interface.
- Persistent model and database volumes.
- Shared application theme available inside Docker.

The earlier 3B Docker smoke test also verified the complete
comparison report for monthly and annual contracts with a
70% minimum churn probability.

The complete updated comparison workflow with the 14B model
was verified through the local end-to-end evaluation.

On resource-constrained hardware, concurrent requests to the
two Docker applications caused timeouts during manual testing.
Sequential interpretation requests completed successfully.

These smoke tests verify the exercised workflows.
They do not replace the complete live-model evaluation.

### Evaluation methodology and interpretation

The reference cases informed prompt changes and implementation
decisions during development.

They constitute small development evaluation suites rather
than independent general-accuracy benchmarks.

Results depend on the tested model, model configuration,
dataset and evaluation cases.

Deterministic scope checks cover known unsupported patterns
but cannot guarantee complete interpretation of natural
language.

The comparison interface requires the user to review the
recognized filters before execution.

Generated evaluation reports are stored under:

```text
data/evaluation/
```

These local evaluation artifacts are excluded from Git.

## Continuous integration and reusable smoke tests

The workflow runs lint and all automated tests plus a two-entry container matrix (Text-to-SQL and comparison). The container jobs build the same application image independently, check Streamlit server health, verify synthetic database access or deterministic agent execution and clean up their containers. No model downloads are required. Health alone does not verify UI execution; the AppTest suite covers that separately.

Run the reusable checks locally from the repository root:

```bash
SMOKE_DIR=$(mktemp -d)
uv run python -m customer_segmentation_assistant.demo.text_to_sql \
  --database "$SMOKE_DIR/text_sql_demo.duckdb"
CUSTOMER_DATABASE="$SMOKE_DIR/text_sql_demo.duckdb" \
  uv run python scripts/smoke/verify_text_to_sql.py
uv run python scripts/smoke/verify_comparison.py \
  --database "$SMOKE_DIR/comparison.duckdb"
rm -r -- "$SMOKE_DIR"
unset SMOKE_DIR
```

`bash scripts/smoke/wait_for_health.sh 8502` checks a running application (use 8503 for comparison). CI passes the Python scripts to the container through standard input rather than packaging test scripts into the image. The comparison smoke test requires a new database path. The new workflow is implemented but its GitHub Actions execution remains to be verified.

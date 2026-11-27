# Testing, CI and model evaluation

[Back to project overview](../README.md)

## Validation and evaluation

The project separates automated software tests from live-model
evaluation.

Automated tests verify deterministic behavior. Live-model
evaluations additionally exercise natural-language interpretation
with a running Ollama model.

### Validation results

Latest validation: 2026-11-27.

| Validation | Model | Result |
| --- | --- | --- |
| Automated test suite | Not required | 296 passed |
| Streamlit integration tests (included above) | Not required | 18/18 |
| Ruff linting | Not required | Passed |
| Docker Compose validation | Not required | Passed |
| Text-to-SQL reference evaluation | `qwen2.5-coder:3b` | 9/9 |
| Single-segment tool-decision evaluation | `qwen2.5-coder:3b` | 7/7 |
| Comparison clarification check | `qwen2.5:14b` | Passed |
| Comparison end-to-end evaluation | `qwen2.5:14b` | 8/8 |
| Docker image builds and health checks | Not required | Passed |
| Docker environment configuration | Not required | Verified |
| Deterministic smoke tests | Not required | Passed |
| Docker Text-to-SQL functional verification | `qwen2.5-coder:3b` | Passed |
| Docker comparison clarification and execution | `qwen2.5:14b` | Passed |
| Docker deterministic scope rejection | Not required | Passed |

The automated test suite covers configuration, model communication,
structured response validation, error handling, SQL policy enforcement,
conversation state, criteria validation and controlled tool execution.

The 18 Streamlit integration tests consist of seven Text-to-SQL
tests and eleven comparison tests. They simulate model responses
while exercising real conversation logic, validation and
synthetic DuckDB queries.

Automated tests and deterministic smoke tests do not require
a running language model.

Live-model evaluations verify natural-language interpretation
and execution against defined reference cases.

The evaluation suites are small development reference suites,
not independent general-accuracy benchmarks.

Results depend on the selected model, configuration, dataset
and implementation version.

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

The reference evaluation passed all 9 cases on 2026-11-27
using `qwen2.5-coder:3b`.

| Reference case | Result |
| --- | --- |
| Customer count | Passed |
| High-risk monthly contracts | Passed |
| Missing total charges | Passed |
| Average risk by contract | Passed |
| Undefined risk threshold | Passed |
| Combined tenure and probability filters | Passed |
| Retention action distribution | Passed |
| Highest monthly charges | Passed |
| High-risk query after clarification | Passed |

Query evaluation compares returned values while ignoring
output aliases.

Row order is checked when required.

Standalone clarification wording requires manual review.
The clarification response correctly requested the missing
numerical risk threshold.

Unsupported responses are verified separately and are not
included in these nine reference cases.

### Single-segment tool-decision evaluation

```bash
OLLAMA_MODEL=qwen2.5-coder:3b \
uv run python scripts/evaluate_tools.py
```

The evaluation passed all 7 automatic checks on 2026-11-27
using `qwen2.5-coder:3b`.

| Reference case | Result |
| --- | --- |
| Monthly contracts with 80% threshold | Passed |
| Two-year contracts with 40% threshold | Passed |
| Annual contracts with 72% threshold | Passed |
| Monthly contracts with 0% threshold | Passed |
| Missing contract and threshold | Passed |
| Missing threshold only | Passed |
| Missing contract only | Passed |

All three clarification responses were additionally reviewed
manually and correctly requested only the missing criteria.

These cases verify structured criteria extraction,
probability normalization and deterministic next-action selection.

They evaluate single-segment decisions rather than
the complete comparison agent.

### Comparison clarification check

```bash
OLLAMA_MODEL=qwen2.5:14b \
uv run python scripts/check_comparison_dialogue.py
```

This live-model check verifies that a threshold follow-up
preserves previously selected contract types.

The check passed on 2026-11-27 using `qwen2.5:14b`.

The verified dialogue consists of:

1. A request to compare monthly and annual contracts.
2. Extraction of both contract types without a default threshold.
3. A clarification question requesting the missing probability.
4. A follow-up supplying a minimum probability of 70%.
5. Complete comparison criteria containing both original
   contract types and the supplied threshold.

The check requires a running Ollama model.

### Comparison end-to-end evaluation

```bash
OLLAMA_MODEL=qwen2.5:14b \
uv run python scripts/evaluate_comparison.py
```

The end-to-end evaluation passed all 8 reference cases
on 2026-11-27 using `qwen2.5:14b`.

| Reference case | Result |
| --- | --- |
| Monthly versus two-year contracts | Passed |
| All three contract types | Passed |
| Both segments empty | Passed |
| Threshold clarification and follow-up | Passed |
| Unsupported tenure filter | Passed |
| Unsupported monthly-charge filter | Passed |
| Different per-segment thresholds | Passed |
| Unsupported filter in follow-up | Passed |

The evaluation verifies:

- Natural-language criteria extraction.
- Probability threshold validation and normalization.
- Clarification and conversation state.
- Deterministic scope validation.
- Controlled agent execution.
- Validated tool calls.
- Correct aggregate calculations.
- Complete segment coverage.
- Deterministic report generation.

#### Model selection

The comparison workflow uses `qwen2.5:14b` as its
recommended model.

Smaller models, including `qwen2.5-coder:3b`, demonstrated
less reliable contract extraction and identification of
unsupported requirements during model evaluation.

The 14B model is therefore the default for the Docker
comparison application.

The 3B model remains the default for Text-to-SQL
and single-segment tool-decision evaluation.

Model selection balances interpretation reliability,
memory requirements and inference time.

The reference results apply to the tested models and cases.
They do not establish equivalent accuracy for other models
or arbitrary natural-language requests.

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

Both containerized applications were successfully verified
on 2026-11-27.

The applications use a shared Ollama server with
independently configured language models.

| Application | Model |
| --- | --- |
| Text-to-SQL | `qwen2.5-coder:3b` |
| Bounded Segment Comparison | `qwen2.5:14b` |

#### Infrastructure verification

| Check | Result |
| --- | --- |
| Application image builds | Passed |
| Model initialization | Passed |
| Ollama health check | Passed |
| Text-to-SQL health check | Passed |
| Comparison health check | Passed |
| Independent model configuration | Verified |
| Shared Ollama endpoint | Verified |
| Network timeout configuration | Verified |
| Persistent model and database volumes | Verified |
| Shared application theme | Verified |

#### Deterministic smoke tests

Both reusable smoke scripts were successfully executed
inside the application containers.

The Text-to-SQL smoke test verified the expected dataset
of 300 synthetic customers.

The comparison smoke test verified:

- Exactly two completed tool calls.
- Correct monthly-contract customer count.
- Correct annual-contract customer count.
- Inclusion of both contract types in the computed report.

The comparison smoke test uses a deterministic planner
and an isolated synthetic database.

Neither smoke test requires live model inference.

#### Live Text-to-SQL verification

The containerized application was verified through
the Streamlit interface using its configured 3B model.

| Scenario | Verified behavior |
| --- | --- |
| Customer count | Correct result of 300 customers |
| Undefined high-risk threshold | Appropriate clarification question |
| Clarification follow-up | Correct interpretation of a 70% threshold |
| Ranked customer selection | Five matching customers in descending risk order |
| Result presentation | Dataframe, SQL inspection and CSV download controls |

#### Live comparison verification

The complete comparison workflow was verified through
the Streamlit interface using its configured 14B model.

The verified workflow includes:

1. Extraction of monthly and annual contract types.
2. Clarification of the missing probability threshold.
3. Interpretation of a shared inclusive minimum of 70%.
4. Display and explicit confirmation of recognized filters.
5. Two validated tool calls.
6. A valid completion action.
7. Deterministic report generation.

The computed report matched the expected synthetic
fixture results:

| Contract | Customer count | Average monthly charges | Average predicted churn probability |
| --- | ---: | ---: | ---: |
| Month-to-month | 2 | 75.00 | 75% |
| One year | 1 | 70.00 | 85% |

The interface displayed the model actions, aggregate
observations, completed tool-call count and computed report.

An additional request containing an unsupported customer
tenure filter was correctly rejected.

No execution button or computed report was displayed
for the unsupported request.

#### Resource considerations

Model inference was verified using sequential requests
to both applications.

Concurrent inference, initial model loading and model
switching may increase response times, particularly
on resource-constrained hardware.

The network timeout defaults to 180 seconds and can
be adjusted through `OLLAMA_TIMEOUT_SECONDS`.

See [System scope and design boundaries](scope.md)
for additional resource and deployment considerations.

These functional checks complement the automated software
tests and local live-model reference evaluations.

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

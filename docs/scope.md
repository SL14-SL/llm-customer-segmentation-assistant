# System Scope and Design Boundaries

[Back to project overview](../README.md)

This document defines the supported application scope, architectural
boundaries, resource considerations and requirements for production use.

The project deliberately focuses on controlled, transparent and
verifiable customer analytics rather than unrestricted autonomous
data analysis.

## Text-to-SQL Assistant

### Supported Scope

- Natural-language analytics against a single customer table.
- One scored customer dataset per application instance.
- Read-only customer queries and aggregate calculations.
- Clarification of missing or ambiguous request criteria.
- Explicitly supplied risk thresholds.
- Inspection of generated SQL and downloadable query results.

### Design Boundaries

The SQL policy restricts queries to a single supported table.
Joins and general multi-table analytics are outside the current scope.

The application operates on scored customer snapshots.
Observed churn outcomes and historical churn-event or score analysis
require additional data sources.

External information retrieval is outside the application scope.

Conversation context is retained during clarification within the
current session. Completed queries are independent, and subsequent
questions start a new request.

### Model Reliability

Generated SQL is validated before execution.

However, syntactically valid and permitted SQL may still differ
from the user's intended analytical request.

Generated queries remain visible for inspection.

## Bounded Segment Comparison

### Supported Scope

- English natural-language comparison requests.
- Two or three explicitly selected supported contract types.
- One shared inclusive minimum predicted churn probability.
- Customer counts, average monthly charges and average
  predicted churn probabilities.
- Criteria clarification and explicit execution confirmation.
- Controlled tool execution and deterministic reporting.

### Design Boundaries

The comparison workflow is intentionally specialized.

Arbitrary additional filters, different probability thresholds
for individual segments and general analytical requests are
outside its supported scope.

Conversation state is maintained within the active session
rather than stored permanently.

Model-generated probability thresholds are validated and
normalized to 12 decimal places.

The experimental model-written explanation in
`experiments/result_summary.py` is retained separately and is
not used to generate the computed comparison report.

### Model Reliability

Natural-language extraction may omit or misinterpret
requested criteria.

Deterministic scope checks reject known unsupported patterns
before model inference. These checks are not a complete
natural-language verification system.

Conservative pattern checks may also reject requests that
merely mention an unsupported attribute.

The recognized filters are displayed before execution and
define the comparison that is actually performed.

Comparison reliability depends on the selected language model.

## Deployment Scope

The project is designed as a local portfolio prototype
demonstrating controlled AI-assisted customer analytics.

Its architecture prioritizes:

- Local model inference.
- Read-only database access.
- Validated model outputs.
- Restricted tool execution.
- Transparent analytical results.
- Explicit user confirmation for comparison execution.

Customer contact, campaign execution and customer data
modification are outside the application scope.

Retrieval-augmented generation and multi-agent orchestration
are not part of the current architecture.

The synthetic datasets demonstrate application behavior
rather than measured business impact.

The project does not establish the predictive accuracy of
upstream churn scores.

## Resource Considerations

Response times depend on hardware, model loading,
prompt processing and system load.

Initial requests may take substantially longer than
subsequent requests.

The default Docker configuration uses two language models
with approximately 11 GB of combined model storage.

The 14B comparison model requires more memory and
computational resources than the 3B Text-to-SQL model.

Larger models may improve natural-language interpretation,
but introduce additional computational requirements.

On resource-constrained systems, model requests should be
executed sequentially rather than concurrently.

Concurrent inference, model switching and initial model
loading may cause requests to exceed the configured
network timeout.

The default timeout is 180 seconds and can be adjusted
through `OLLAMA_TIMEOUT_SECONDS`.

This timeout applies to individual model requests rather
than the entire comparison workflow.

See [Installation and configuration](getting-started.md)
for configuration details.

## Production Readiness

The current implementation provides a tested foundation
for local AI-assisted analytics.

Before deploying the application in a production environment,
additional measures would be required:

- Authentication and authorization.
- Role-based data access.
- Tenant isolation where applicable.
- Deployment-specific security controls.
- Operational monitoring and alerting.
- Resource management and request concurrency controls.
- Broader model evaluation using representative business data.
- Verification of data privacy and governance requirements.

The exact requirements depend on the target environment,
data sensitivity and intended users.

See [Architecture](architecture.md) and
[Validation and evaluation](evaluation.md) for the current
technical implementation and verification strategy.
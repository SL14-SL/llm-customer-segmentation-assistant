# Installation and configuration

[Back to project overview](../README.md)

## Quick start with Docker

The self-contained Docker environment includes both applications,
a shared Ollama server and separate synthetic datasets.

### Requirements

- Docker Desktop or Docker Engine with Docker Compose
- Internet access for the initial image and model downloads
- Sufficient local memory and storage for both language models
- Additional computational resources for the 14B comparison model

No local Python installation, Ollama installation or upstream
churn prediction project is required.

### Start

From the repository root:

```bash
docker compose up --build -d
```

Once startup completes, open:

| Application | URL | Demo dataset | Default model |
| --- | --- | --- | --- |
| Text-to-SQL Assistant | http://localhost:8502 | 300 synthetic customers | `qwen2.5-coder:3b` |
| Segment Comparison | http://localhost:8503 | 6 synthetic customers | `qwen2.5:14b` |

Both applications share one Ollama server but use independently
configurable language models.

The first startup downloads the required container images, Python
dependencies and language models. The default models require
approximately 11 GB of model storage, in addition to Docker images
and application data.

Each application waits until its model initialization has
completed successfully. Model initialization runs sequentially.

This configuration uses CPU inference. Response times depend on
hardware, model size and current system load.

The 14B comparison model requires substantially more computational
resources than the 3B Text-to-SQL model. On resource-constrained
systems, avoid simultaneous requests to both applications.

Initial model loading and concurrent inference may cause requests
to exceed the configured network timeout.

Check startup progress:

```bash
docker compose logs -f model-init comparison-model-init
```

```bash
docker compose ps -a
```

Application logs:

```bash
docker compose logs -f app comparison
```

### Try the Text-to-SQL Assistant

Enter:

```text
How many customers are in the dataset?
```

Expected result: **300 customers**.

Another example:

```text
What is the average churn probability for each contract type?
```

### Try the Segment Comparison

Enter:

```text
Compare monthly and annual contracts with a minimum churn probability of 70%.
```

Review the recognized filters and select **Run this comparison**.

Expected results:

| Contract | Matching customers | Average monthly charges | Average predicted churn probability |
| --- | ---: | ---: | ---: |
| Month-to-month | 2 | 75.00 | 75% |
| One year | 1 | 70.00 | 85% |

The results are calculated from the bundled synthetic fixture.
No currency is specified.

### Stop

```bash
docker compose down
```

Downloaded models and demo databases persist in named Docker volumes.

### Change models or timeout

```bash
OLLAMA_MODEL=qwen2.5-coder:3b \
COMPARISON_OLLAMA_MODEL=qwen2.5:14b \
OLLAMA_TIMEOUT_SECONDS=300 docker compose up -d
```

Alternatively set these variables in a local `.env` file. The Docker environment uses its own Ollama server. Both UI ports bind to loopback; the Ollama API is not published to the host.

## Local installation without Docker

Both applications can also be run directly using a local
Python environment and Ollama installation.

### Requirements

- Python 3.12
- uv
- Ollama

Run all commands from the repository root.

### 1. Install dependencies

```bash
uv sync
```

### 2. Prepare Ollama

Install Ollama using the
[official instructions](https://ollama.com/).

Download the models required for the two applications:

```bash
ollama pull qwen2.5-coder:3b
ollama pull qwen2.5:14b
```

The 3B model is used for Text-to-SQL and single-segment
tool-decision evaluation.

The 14B model is recommended for the bounded comparison
application and its end-to-end evaluation.

If only the Text-to-SQL application is required, downloading
the larger model is not necessary.

If Ollama is not already running as a service:

```bash
ollama serve
```

Check availability:

```bash
curl --fail --show-error http://localhost:11434/api/tags
```

### 3. Run the synthetic Text-to-SQL demo

Create the reproducible demo dataset:

```bash
uv run python -m customer_segmentation_assistant.demo.text_to_sql
```

Start the application:

```bash
OLLAMA_MODEL=qwen2.5-coder:3b \
CUSTOMER_DATABASE=data/text_sql_demo.duckdb \
SYNTHETIC_DEMO=1 \
uv run streamlit run streamlit_app.py \
  --server.address 127.0.0.1 \
  --server.port 8502
```

Open http://localhost:8502.

The generator reuses an existing database.

To regenerate the dataset, stop the application and remove
only `data/text_sql_demo.duckdb` before running the generator
again.

### 4. Run the bounded comparison demo

In a separate terminal:

```bash
OLLAMA_MODEL=qwen2.5:14b \
uv run streamlit run streamlit_agent_demo.py \
  --server.address 127.0.0.1 \
  --server.port 8503
```

Open http://localhost:8503.

The comparison database is created automatically when the
first comparison is executed, if it does not already exist.

No upstream churn dataset is required.

For an upstream scored dataset, see [Data](data.md).

## Configuration

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_MODEL` | `qwen2.5-coder:3b` | Model used by local Python processes and the Docker Text-to-SQL service |
| `COMPARISON_OLLAMA_MODEL` | `qwen2.5:14b` | Model selected for the Docker comparison service |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server address |
| `OLLAMA_TIMEOUT_SECONDS` | `180` | Positive finite network timeout in seconds for each model request |
| `CUSTOMER_DATABASE` | `data/customers.duckdb` | Text-to-SQL database |
| `SYNTHETIC_DEMO` | Unset | Enable synthetic-data notice when set to `1` |

All five model integrations use `config.py` and `llm/client.py`. The timeout is passed to both application containers. It is not an overall workflow deadline. The client does not automatically retry failed requests.

Within Docker, both applications connect to:

```text
http://ollama:11434
```

Docker Compose maps `COMPARISON_OLLAMA_MODEL` to the
`OLLAMA_MODEL` environment variable inside the comparison
container.

For local execution without Docker, use `OLLAMA_MODEL`
to select the model for each Python process independently.

The Docker Text-to-SQL service selects the generated
300-customer database and enables the synthetic-data notice.

### Shared application theme

Both Streamlit interfaces use a common visual configuration.

| File | Responsibility |
| --- | --- |
| `.streamlit/config.toml` | Native Streamlit theme and component colors |
| `src/customer_segmentation_assistant/ui/theme.py` | Shared typography and chat styling |

The visual theme is independent of query execution,
model interaction and comparison logic.

## Troubleshooting

- If Ollama cannot be reached, check its service and endpoint configuration.
- HTTP 404: verify the configured model and endpoint; server errors require checking logs and resources.
- For timeouts, avoid simultaneous inference, allow for model loading, or increase `OLLAMA_TIMEOUT_SECONDS`.
- An incomplete or invalid model response is rejected; retry manually or rephrase the request.
- For a missing database, generate the synthetic data or configure `CUSTOMER_DATABASE`.
- `docker compose down` preserves named volumes. Do not add `-v` unless you intend to delete their contents.

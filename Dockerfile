FROM python:3.12.9-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable
COPY streamlit_app.py ./
RUN useradd --create-home app && mkdir /app/data && chown app:app /app/data
USER app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
EXPOSE 8502
CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8502", "--server.headless=true"]

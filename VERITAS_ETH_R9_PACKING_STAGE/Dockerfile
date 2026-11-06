FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd -r -u 10001 app && mkdir -p /app/.veritas && chown 10001:10001 /app/.veritas
USER app
EXPOSE 8080
ENV VERITAS_AUDIT_DB=/app/.veritas/audit.sqlite3
CMD ["uvicorn", "veritas.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]

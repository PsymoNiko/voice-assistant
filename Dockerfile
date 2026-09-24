FROM python:3.11-slim AS base
WORKDIR /app
COPY pyproject.toml .
COPY apps ./apps
COPY packages ./packages
RUN pip install --no-cache-dir .

FROM base AS gateway
CMD ["uvicorn", "apps.gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]

FROM base AS worker
CMD ["python", "-m", "apps.worker.main"]

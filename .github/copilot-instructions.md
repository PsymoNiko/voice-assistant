# Copilot instructions for local-voice-assistant

## Repository overview

This repo is a compact Python 3.11 service for a local/self-hosted multilingual voice assistant. The code is deliberately small and organized around a few boundary points rather than a large framework:

- `apps/gateway/main.py` exposes the FastAPI API for health checks, response processing, and TTS job creation/query.
- `apps/worker/main.py` consumes Redis Streams jobs and updates the status of each TTS job.
- `packages/response_processor.py` turns Markdown into UI blocks plus a speech-safe text string.
- `packages/language.py` detects language and applies Persian-friendly replacements before TTS.
- `packages/models.py` defines the Pydantic request/response contracts used across the pipeline.
- `integrations/openwebui_tts_filter.py` connects completed Open WebUI responses to the speech pipeline.
- `docker-compose.yml` wires Redis, LiteLLM, Open WebUI, RustFS, the gateway, and the worker together.

The default Docker worker uses `espeak-ng` plus FFmpeg for local WAV/MP3 generation. The mock engine remains available for tests or environments without a TTS binary.

## Build, test, and lint commands

Use the project metadata in `pyproject.toml` and install dev dependencies before running checks:

```bash
python -m pip install -e '.[dev]'
```

Run the project test suite:

```bash
python -m pytest -q
```

Run a single file or a single test:

```bash
python -m pytest tests/test_pipeline.py -q
python -m pytest tests/test_pipeline.py -k markdown_policy -q
```

Run the gateway/worker container build and validate the Compose file:

```bash
docker compose config --quiet
docker compose build gateway worker
```

Run linting:

```bash
ruff check .
```

The repo currently has `ruff` findings in existing files (import ordering / broad exception handling), so treat lint as a validation step to keep changes clean rather than assuming the baseline is green.

Run the app stack locally:

```bash
cp .env.example .env
docker compose up --build
```

Directly run the services without Docker:

```bash
uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8080
python -m apps.worker.main
```

## High-level architecture

The main flow is:

1. A client or the Open WebUI filter submits a Markdown response to `/responses/speak`, or submits speech text directly to `/tts/jobs`.
2. `apps/gateway/main.py` preserves the original Markdown, derives speech-safe text, detects language, and writes job state to Redis.
3. Redis Streams (`tts:generate` by default) are consumed by the background worker.
4. The worker generates WAV audio, converts it to MP3 with FFmpeg, uploads it to RustFS, and updates Redis with a presigned URL.
5. The API exposes job status at `/tts/jobs/{job_id}`; completed audio is stored under `conversations/{conversation_id}/{message_id}/audio.mp3`.

The response-processing path is intentionally split from the transport path:

- `process_markdown()` parses Markdown with `markdown-it-py`.
- It emits structured UI blocks for text, headings, tables, and code fences.
- It also creates a `speech_text` string that is safer for TTS and avoids exposing raw code blocks verbatim.

Language handling is intentionally centralized:

- `detect_language()` uses `langdetect` and normalizes into BCP-47-style values such as `fa-IR` and `en-US`.
- `normalize_persian()` rewrites technical terms into Persian-friendly forms before TTS output.

The Open WebUI integration is a global outlet filter stored in Open WebUI's persistent database. It polls the gateway job until completion and appends an audio player/link to the assistant message. If the filter changes, update `integrations/openwebui_tts_filter.py` and reinstall/reload it in the Open WebUI database.

## Key conventions

- Keep the project in Python 3.11 style and favor small, explicit modules under `apps/` and `packages/` rather than adding new abstraction layers.
- Treat Redis as the integration boundary between the API and the worker; job state is stored in Redis hashes (`tts:job:<job_id>`) while the queue is a stream (`tts:generate`).
- Treat RustFS as the audio source of truth; Redis stores metadata and the presigned `audio_url`, not audio bytes.
- Include `conversation_id` and `message_id` on TTS requests when available so object keys follow the Part 24 layout: `conversations/{conversation_id}/{message_id}/audio.mp3`.
- Keep `TTS_ENGINE`, `TTS_AUDIO_DIR`, `RUSTFS_ENDPOINT`, `RUSTFS_PUBLIC_ENDPOINT`, `RUSTFS_BUCKET`, and Redis settings configurable through the environment.
- Keep the original Markdown response intact and derive speech-safe output separately; the TTS path is not supposed to mutate the source response.
- Use Pydantic models from `packages/models.py` as the canonical request/response shape for TTS jobs.
- The repo uses `REDIS_URL` and `TTS_STREAM` environment variables, so new features should respect those settings instead of hard-coding localhost assumptions.
- The existing tests in `tests/test_pipeline.py` act as the de facto contract for the Markdown and language behavior; keep those semantics stable when adjusting the speech pipeline.
- The Docker stack is configured around `gateway` and `worker` images from `Dockerfile`, and the app assumes the `me_network` Docker network is available for service-to-service communication.

## Useful references

- `README.md` documents the default local stack and the browser endpoints.
- `docker-compose.yml` defines the runtime architecture and service profiles.
- `tests/test_pipeline.py` is the smallest source of truth for expected output formatting and language detection behavior.
- `integrations/openwebui_tts_filter.py` is the Open WebUI outlet-filter integration for automatic speech jobs.

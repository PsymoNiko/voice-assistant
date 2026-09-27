# Copilot instructions for local-voice-assistant

## Repository overview

This repo is a compact Python 3.11 service for a local/self-hosted multilingual voice assistant. The code is deliberately small and organized around a few boundary points rather than a large framework:

- `apps/gateway/main.py` exposes the FastAPI API for health checks, response processing, and TTS job creation/query.
- `apps/worker/main.py` consumes Redis Streams jobs and updates the status of each TTS job.
- `apps/worker/tts.py` contains the mock, espeak-ng, and optional Chatterbox audio-generation paths.
- `packages/response_processor.py` turns Markdown into UI blocks plus a speech-safe text string.
- `packages/language.py` detects language and applies Persian-friendly replacements before TTS.
- `packages/models.py` defines the Pydantic request/response contracts used across the pipeline.
- `integrations/openwebui_tts_filter.py` connects completed Open WebUI responses to the speech pipeline.
- `docker-compose.yml` wires Redis, LiteLLM, Open WebUI, Qdrant, the gateway, and the worker together; ComfyUI is opt-in.
- n8n, SearXNG, and the Instance AI sandbox API/runner are opt-in services on the `automation` Compose profile; n8n data and sandbox mTLS certificates persist in named volumes.
- `opencode.json` and `.opencode/` configure the project-local OpenCode frontend agent and its reusable skills; they are client configuration, not application services.

The default Docker worker uses `espeak-ng` plus FFmpeg for local WAV/MP3 generation. The mock engine remains available for tests or environments without a TTS binary. Note that `apps/worker/tts.py` defaults to `mock` when run directly; Compose explicitly sets `TTS_ENGINE=espeak`.

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

Run Ruff after changes; distinguish any pre-existing findings from issues introduced by the current change.

Run the core app stack locally:

```bash
cp .env.example .env
docker compose up --build
```

The default stack starts the gateway and worker, not profile-gated services. Start LiteLLM and Open WebUI with `docker compose --profile ui --profile llm up --build`; Open WebUI is exposed at `http://localhost:3008` and LiteLLM at `http://localhost:4000`. The gateway is exposed at `http://localhost:8388` (container port 8080).

Directly run the services without Docker:

```bash
uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8080
python -m apps.worker.main
```

## High-level architecture

The main flow is:

1. A client or the Open WebUI filter submits a Markdown response to `/responses/speak`, or submits speech text directly to `/tts/jobs`.
2. `apps/gateway/main.py` preserves the original Markdown, derives speech-safe text, detects language, and writes job state to Redis. `/responses/process` performs the Markdown/language processing without queuing TTS.
3. Redis Streams (`tts:generate` by default) are consumed by the background worker.
4. The worker generates WAV audio, converts it to MP3 when requested, uploads it to RustFS, and updates Redis with a presigned URL.
5. The API exposes job status at `/tts/jobs/{job_id}`; completed audio is stored under `conversations/{conversation_id}/{message_id}/audio.<format>` when IDs are provided.

The worker marks generation/upload errors as `failed` in the Redis job hash and acknowledges the stream entry after handling it; failed entries are not automatically retried. Preserve that state transition if changing queue failure handling.

The response-processing path is intentionally split from the transport path:

- `process_markdown()` parses Markdown with `markdown-it-py`.
- It emits structured UI blocks for text, headings, tables, and code fences.
- It also creates a `speech_text` string that is safer for TTS and avoids exposing raw code blocks verbatim.

Language handling is intentionally centralized:

- `detect_language()` uses `langdetect` and normalizes into BCP-47-style values such as `fa-IR` and `en-US`.
- `normalize_persian()` rewrites technical terms into Persian-friendly forms before TTS output.

The Open WebUI integration is a global outlet filter stored in Open WebUI's persistent database. It polls the gateway job until completion and appends an audio player/link to the assistant message. If the filter changes, update `integrations/openwebui_tts_filter.py` and reinstall/reload it in the Open WebUI database.

Keep model serving and UI features separate from the voice-job pipeline:

- LiteLLM routes model groups to the Ollama service defined in the sibling automation repository. The Ollama service and this Compose stack must share the external `me_network`.
- Open WebUI owns agent/model presets, Markdown skills, and document knowledge/RAG. Its Qdrant vector store is distinct from LiteLLM's optional semantic cache.
- ComfyUI is available in the `image-gen` profile, uses the GPU, and is not part of the text or TTS pipeline. Open WebUI image generation calls ComfyUI directly; it uses a separately configured ComfyUI workflow and checkpoint, not a LiteLLM chat model group.
- n8n is available in the `automation` profile on localhost port 5678. SearXNG is internal-only and configured for Instance AI search through `http://searxng:8080`; keep `SEARXNG_SECRET` private. The Instance AI sandbox API and privileged Docker-in-Docker runner are private to the Compose network; do not publish their ports. Sandbox API and runner credentials must be configured as matching secrets in `.env`. Workflows running in n8n should use Compose service names (for example, `gateway:8080` or `litellm:4000`), not host `localhost` URLs. Its editor and webhooks are localhost-only unless explicitly reconfigured behind HTTPS.
- n8n Instance AI is a separate client of LiteLLM, configured by `N8N_INSTANCE_AI_MODEL`, `N8N_INSTANCE_AI_MODEL_URL`, and `N8N_INSTANCE_AI_MODEL_API_KEY` in Compose. Keep its selected model tool-capable; updating LiteLLM alone does not automatically make a LiteLLM-configured MCP server available to n8n's Instance AI tools. n8n workflows, credentials, and Instance AI settings persist in `n8n-data`; preserve that volume and change persisted settings through n8n rather than editing its database directly.
- OpenCode's `frontend` primary agent uses LiteLLM's `coding` model by default. Keep its project agent/skill instructions under `.opencode/`; do not confuse these with Open WebUI Workspace agents and skills.

## Key conventions

- Keep the project in Python 3.11 style and favor small, explicit modules under `apps/` and `packages/` rather than adding new abstraction layers.
- Treat Redis as the integration boundary between the API and the worker; job state is stored in Redis hashes (`tts:job:<job_id>`) while the queue is a stream (`tts:generate`).
- Treat RustFS as the audio source of truth; Redis stores metadata and the presigned `audio_url`, not audio bytes.
- Include `conversation_id` and `message_id` on TTS requests when available so object keys follow the layout `conversations/{conversation_id}/{message_id}/audio.<format>`.
- Keep `TTS_ENGINE`, `TTS_AUDIO_DIR`, `RUSTFS_ENDPOINT`, `RUSTFS_PUBLIC_ENDPOINT`, `RUSTFS_BUCKET`, and Redis settings configurable through the environment.
- Keep the original Markdown response intact and derive speech-safe output separately; the TTS path is not supposed to mutate the source response.
- Use Pydantic models from `packages/models.py` as the canonical request/response shape for TTS jobs.
- The repo uses `REDIS_URL`, `TTS_STREAM`, `TTS_CONSUMER_GROUP`, and `TTS_CONSUMER_NAME`; new queue behavior should respect those settings.
- Language detection and Persian normalization belong in `packages/language.py`; Markdown parsing and speech policy belong in `packages/response_processor.py`.
- The existing tests in `tests/test_pipeline.py` act as the de facto contract for the Markdown and language behavior; keep those semantics stable when adjusting the speech pipeline.
- The Docker stack is configured around `gateway` and `worker` images from `Dockerfile`, and the core app assumes the `me_network` Docker network is available for service-to-service communication.
- Open WebUI configuration persists in its data volume. Do not remove that volume to apply settings, since it contains accounts, chats, and workspace data; auth and RAG settings can be persisted in its database.
- Open WebUI image-generation settings and ComfyUI workflow are also persisted in its database. When changing checkpoints or workflow inputs, update the saved workflow as well as the ComfyUI model files.
- n8n workflows and credentials persist in the `n8n-data` volume; do not remove it when changing service configuration.
- The n8n sandbox runner requires privileged Docker-in-Docker. Keep the runner and sandbox API private and enable the `automation` profile only on trusted hosts.
- SearXNG requires `config/searxng/settings.yml` with JSON enabled for n8n search integration; keep the instance private unless a separate access-control plan is in place.

## Useful references

- `README.md` documents the local stack, API endpoints, Compose profiles, Open WebUI knowledge/skills, and ComfyUI.
- `docker-compose.yml` defines the runtime architecture, service ports, and profiles.
- `config/litellm.yaml` defines model groups and optional LiteLLM semantic caching.
- `opencode.json` and `.opencode/` configure the local OpenCode development agent and skills.
- `tests/test_pipeline.py` is the smallest source of truth for expected output formatting and language detection behavior.
- `integrations/openwebui_tts_filter.py` is the Open WebUI outlet-filter integration for automatic speech jobs.

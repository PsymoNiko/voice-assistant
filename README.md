# Local Voice Assistant

[![XERJ Corpus Hub contributor](https://hub.xerj.org/contributors/PsymoNiko/badge.svg)](https://hub.xerj.org/contributors/PsymoNiko)

A local/self-hosted multilingual voice assistant foundation.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

- Gateway API: http://localhost:8080/docs
- Open WebUI: http://localhost:3008 (with the `ui` and `llm` profiles)
- LiteLLM: http://localhost:4000
- n8n: http://localhost:5678 (with the `automation` profile)
- RustFS console: http://localhost:9001

## n8n workflow automation

n8n is an optional workflow automation service. Start it with:

```bash
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 32
```

Copy the three generated values into `.env` as `N8N_SANDBOX_SERVICE_API_KEY`, `N8N_SANDBOX_RUNNER_REGISTRATION_TOKEN`, and `N8N_SANDBOX_RUNNER_API_KEY`, respectively. Do not commit `.env` or reuse the example values. Then start the stack:

```bash
docker compose --profile automation up -d n8n
```

Before starting, also set `SEARXNG_SECRET` in `.env` to a separate random value (`openssl rand -hex 32`). SearXNG is connected to n8n at `http://searxng:8080`, has JSON search output enabled, and is internal-only (no host port is published). This enables n8n Instance AI web search; it does not route general n8n HTTP Request nodes through a search engine.

This starts n8n together with SearXNG, the sandbox certificate bootstrap, private sandbox API, and Docker-in-Docker runner. The n8n service is configured to use the n8n sandbox provider. The sandbox API and runner have no published host ports; do not expose them. The runner is privileged to run its isolated sandbox containers, so only enable this profile on a host you trust.

This sandbox is for n8n's Instance AI workflow-building workspace; it does not replace task runners for executing regular Code nodes.

Open http://localhost:5678 and create the initial owner account. The editor port is bound to localhost, and n8n's configuration and credentials persist in the `n8n-data` volume. The container is attached to `me_network`, so workflows can reach services using their Compose names—for example, call the gateway at `http://gateway:8080`, or LiteLLM at `http://litellm:4000/v1` when its `llm` profile is running. Do not use `localhost` inside an n8n workflow to refer to another container.

Check startup with `docker compose --profile automation ps`; inspect service startup problems with `docker compose --profile automation logs searxng sandbox-certs sandbox-api sandbox-runner-1 n8n`.

The example timezone is `Etc/UTC`; set `GENERIC_TIMEZONE` in `.env` to your IANA timezone if scheduled workflows should use local time. The local HTTP setup disables secure cookies and is intended only for localhost access. Put n8n behind HTTPS and configure its public editor/webhook URLs before exposing it outside the machine.

## Open WebUI agents, knowledge, and skills

LiteLLM serves the models; Open WebUI provides agent presets, reusable skills, and document retrieval. Open WebUI uses the Qdrant service for its RAG vectors and `nomic-embed-text` from the shared Ollama service for embeddings. This is separate from LiteLLM's optional semantic cache.

Pull the embedding model, then start the UI, LiteLLM, and Qdrant:

```bash
docker exec ollama ollama pull nomic-embed-text
docker compose --profile ui --profile llm up -d qdrant litellm open-webui
```

Open http://localhost:3008 and sign in. Authentication is enabled; on a fresh Open WebUI database, create the first account to become the administrator. The UI port is bound to localhost.

In **Workspace > Knowledge**, create a knowledge base and upload reference documents. In **Workspace > Skills**, create reusable Markdown instructions (for example, a frontend design or code-review guide). In **Workspace > Models**, create an agent preset, choose `coding` as its base model, add a system prompt, then attach relevant knowledge and skills. Enable built-in knowledge tools for focused retrieval. The `coding` model is local Qwen2.5-Coder through LiteLLM.

The Open WebUI database volume persists settings and user data. If this stack already has an `open-webui-data` volume, review **Admin Settings > Documents** for the Qdrant vector database and Ollama embedding model; don't remove the volume to apply config changes, since that would delete chats and workspace data.

### Route LiteLLM's Gemini requests through a host proxy

Set these in `.env` (replace `10808` if your proxy listens on another port):

```dotenv
LITELLM_HTTP_PROXY=http://host.docker.internal:10808
LITELLM_HTTPS_PROXY=http://host.docker.internal:10808
```

Compose maps `host.docker.internal` to the host gateway for Linux containers and passes these values to LiteLLM. The proxy must accept connections from Docker containers; a proxy bound only to the host's `127.0.0.1` will not be reachable this way. Configure it to listen on a Docker-reachable host interface and restrict access with your firewall rather than exposing an unrestricted proxy. Then recreate LiteLLM:

```bash
docker compose --profile llm up -d --force-recreate litellm
```

Leave both proxy values empty to connect directly. A proxy only changes LiteLLM's outbound network route; it does not change the Gemini API key or model configuration.

## OpenCode frontend agent

The project `opencode.json` uses LiteLLM's `coding` model group by default and keeps direct Ollama available as an alternative. `.opencode/agents/frontend.md` defines the frontend primary agent; reusable design, accessibility, testing, and cafe-research guidance lives under `.opencode/skills/`. These are OpenCode client features, while LiteLLM only provides model inference.

Start LiteLLM and run OpenCode with the active LiteLLM container key loaded into the process environment. This avoids saving the key in the OpenCode config:

```bash
docker compose --profile llm up -d litellm
LITELLM_MASTER_KEY="$(docker inspect litellm --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^LITELLM_MASTER_KEY=//p')" opencode
```

In OpenCode, use `/models` to select `litellm/coding` or `ollama/qwen2.5-coder:7b`, and **Tab** to select the `frontend` primary agent. The project agent allows edits and asks before running shell commands. Keep API keys out of `opencode.json` and source control.

### Cafe research MCP and persistent memory

When OpenCode is started from this repository, `opencode.json` enables the local `beans-cafe-research` MCP server. It searches cafes/restaurants in one user-specified bounded area using OpenStreetMap, stores reviewed leads, menu summaries, logo URLs, and source links in `../BEANS/beans-cafe-ads/data/cafe-research.sqlite3`, and reads the product facts from that repository's `memory/product-profile.json`. The database and map-response cache are local and gitignored. If the repository layout changes, update the two `CAFE_RESEARCH_*` paths in `opencode.json`.

Use `/cafe-growth-research` for the research and pitch workflow. Map data is discovery-only; verify current menus, logos, and contact details against official business sources. The tool does not crawl the world, download logo artwork, or send outreach. Follow the OpenStreetMap public-service limits and attribution documented in `../BEANS/beans-cafe-ads/README.md`. This MCP is for OpenCode and does not enable tools or memory in the Open WebUI voice runtime.

Create and poll a TTS job:

```bash
curl -X POST http://localhost:8080/tts/jobs \
  -H 'content-type: application/json' \
  -d '{"text":"سلام، این یک آزمایش است.","language":"fa-IR"}'
curl http://localhost:8080/tts/jobs/<job_id>
```

The pipeline preserves the original Markdown response, extracts speech-safe text, detects language, queues jobs through Redis Streams, and leaves TTS engine/storage adapters replaceable.

The LiteLLM `coding` model (`qwen2.5-coder:7b`) is text-only. For chats with images, pull the vision model into the shared Ollama service and select the `vision` model in Open WebUI:

```bash
docker exec ollama ollama pull qwen2.5vl:3b
```

The Ollama service must be connected to `me_network`, as configured in `../automation/infrastructure/ollama/compose.yaml`.

## Local image generation

ComfyUI runs as an opt-in service on the RTX 4060. LiteLLM and ComfyUI each have a 10-CPU Docker quota, which is half of this host's 20 logical CPUs. Adjust `LITELLM_CPUS` and `COMFYUI_CPUS` in `.env` on other hosts. Docker Compose cannot enforce a per-container GPU utilization percentage; ComfyUI remains GPU-uncapped and uses `--lowvram`.

Download the 5.2-GB SD-Turbo checkpoint, then start the service:

```bash
mkdir -p models/comfyui/models/checkpoints
curl -fL https://huggingface.co/stabilityai/sd-turbo/resolve/main/sd_turbo.safetensors \
  -o models/comfyui/models/checkpoints/sd_turbo.safetensors
docker compose --profile image-gen up -d comfyui
```

Open http://localhost:8188, choose `sd_turbo.safetensors` in a checkpoint-based workflow, and generate at 512x512 to start. Models and generated images persist under `models/comfyui/`, which is excluded from Git. ComfyUI is available only from this machine and requests `--lowvram` to reduce GPU memory use. The GPU is shared with Ollama, so stop Ollama while generating if you run out of VRAM; the two services can be started independently.

The Docker worker currently uses `espeak-ng` to generate local WAV audio. Poll the job until it is completed, then open its `audio_url` in a browser or audio player. The repository's TTS worker is separate from Open WebUI's built-in audio settings; an Open WebUI integration still needs to submit responses to `/tts/jobs`.

Chatterbox is available as an opt-in GPU worker image. It downloads its model on first use and can use an optional reference clip at `voices/ali/<language>/reference.wav` for voice cloning. Keep the default worker on `espeak` until the model has been downloaded and tested:

```bash
TTS_DOCKER_TARGET=worker-chatterbox TTS_ENGINE=chatterbox docker compose build worker
TTS_DOCKER_TARGET=worker-chatterbox TTS_ENGINE=chatterbox docker compose up worker
```

Set `CHATTERBOX_DEVICE=cpu` when GPU access is unavailable. Without a reference clip, Chatterbox uses its default voice.

To process a complete Markdown response and queue its speech-safe representation in one request:

```bash
curl -X POST http://localhost:8388/responses/speak \
  -H 'content-type: application/json' \
  -d '{"markdown":"Hello\\n\\n```python\\nprint(1)\\n```","conversation_id":"conv-1","message_id":"msg-1"}'
```

The response keeps `original_response` and `blocks` for the UI and returns a `tts_job` whose completed audio is stored in RustFS under `conversations/{conversation_id}/{message_id}/audio.mp3`.

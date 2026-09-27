# Local Voice Assistant

A local/self-hosted multilingual voice assistant foundation.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

- Gateway API: http://localhost:8080/docs
- Open WebUI: http://localhost:3008 (with the `ui` and `llm` profiles)
- LiteLLM: http://localhost:4000
- RustFS console: http://localhost:9001

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

ComfyUI runs as an opt-in service on the RTX 4060. Download the 5.2-GB SD-Turbo checkpoint, then start the service:

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

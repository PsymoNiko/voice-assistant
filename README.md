# Local Voice Assistant

A local/self-hosted multilingual voice assistant foundation.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

- Gateway API: http://localhost:8080/docs
- Open WebUI: http://localhost:3000 (with the `ui` and `llm` profiles)
- LiteLLM: http://localhost:4000
- RustFS console: http://localhost:9001

Create and poll a TTS job:

```bash
curl -X POST http://localhost:8080/tts/jobs \
  -H 'content-type: application/json' \
  -d '{"text":"سلام، این یک آزمایش است.","language":"fa-IR"}'
curl http://localhost:8080/tts/jobs/<job_id>
```

The pipeline preserves the original Markdown response, extracts speech-safe text, detects language, queues jobs through Redis Streams, and leaves TTS engine/storage adapters replaceable. The default worker uses a mock audio adapter so the development stack runs without a model or GPU.

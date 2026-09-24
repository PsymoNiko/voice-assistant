import os
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from redis.asyncio import Redis
from packages.language import detect_language, normalize_persian
from packages.models import TTSJob, TTSJobRequest
from packages.response_processor import process_markdown

app = FastAPI(title="Local Voice Assistant Gateway", version="0.1.0")
redis = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
stream = os.getenv("TTS_STREAM", "tts:generate")


@app.get("/health")
async def health() -> dict[str, str]:
    await redis.ping()
    return {"status": "ok"}


@app.post("/responses/process")
async def process_response(payload: dict[str, str]) -> dict:
    original = payload.get("markdown", "")
    blocks, speech = process_markdown(original)
    language = detect_language(speech)
    if language.startswith("fa"):
        speech = normalize_persian(speech)
    return {"original_response": original, "blocks": blocks, "speech_text": speech, "language": language}


@app.post("/tts/jobs", response_model=TTSJob, status_code=202)
async def create_job(request: TTSJobRequest) -> TTSJob:
    job_id = f"tts_{uuid.uuid4().hex}"
    language = request.language or detect_language(request.text)
    text = normalize_persian(request.text) if language.startswith("fa") else request.text
    job = TTSJob(job_id=job_id, status="queued", language=language, voice_id=request.voice_id, text=text)
    await redis.hset(f"tts:job:{job_id}", mapping={**job.model_dump(), "created_at": datetime.now(timezone.utc).isoformat()})
    await redis.xadd(stream, {"job_id": job_id})
    return job


@app.get("/tts/jobs/{job_id}", response_model=TTSJob)
async def get_job(job_id: str) -> TTSJob:
    data = await redis.hgetall(f"tts:job:{job_id}")
    if not data:
        raise HTTPException(status_code=404, detail="TTS job not found")
    return TTSJob(**{key: data[key] for key in TTSJob.model_fields if key in data})

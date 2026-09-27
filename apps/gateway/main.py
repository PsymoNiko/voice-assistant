import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from redis.asyncio import Redis

from packages.language import detect_language, normalize_persian
from packages.models import TTSJob, TTSJobRequest
from packages.response_processor import process_markdown

app = FastAPI(title="Local Voice Assistant Gateway", version="0.1.0")
redis = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
stream = os.getenv("TTS_STREAM", "tts:generate")
audio_dir = Path(os.getenv("TTS_AUDIO_DIR", "/tmp/tts-audio"))


async def enqueue_tts_job(request: TTSJobRequest, text: str) -> TTSJob:
    job_id = f"tts_{uuid.uuid4().hex}"
    language = request.language or detect_language(text)
    speech_text = normalize_persian(text) if language.startswith("fa") else text
    job = TTSJob(
        job_id=job_id,
        status="queued",
        language=language,
        voice_id=request.voice_id,
        text=speech_text,
        conversation_id=request.conversation_id,
        message_id=request.message_id,
        format=request.format,
    )
    await redis.hset(
        f"tts:job:{job_id}",
        mapping={
            **job.model_dump(exclude_none=True),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await redis.xadd(stream, {"job_id": job_id})
    return job


@app.get("/health")
async def health() -> dict[str, str]:
    await redis.ping()
    return {"status": "ok"}


@app.get("/tts/audio/{job_id}")
async def get_audio(job_id: str) -> FileResponse:
    audio_path = audio_dir / f"{job_id}.wav"
    if not audio_path.is_file():
        raise HTTPException(status_code=404, detail="TTS audio not found")
    return FileResponse(audio_path, media_type="audio/wav", filename=audio_path.name)


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
    return await enqueue_tts_job(request, request.text)


@app.post("/responses/speak", status_code=202)
async def speak_response(payload: dict[str, str | None]) -> dict:
    original = payload.get("markdown") or ""
    if not original.strip():
        raise HTTPException(status_code=422, detail="markdown must not be empty")

    blocks, speech_text = process_markdown(original)
    language = detect_language(speech_text)
    request = TTSJobRequest(
        text=speech_text,
        language=payload.get("language") or language,
        voice_id=payload.get("voice_id") or "ali",
        announcement_voice_id=payload.get("announcement_voice_id") or "system",
        conversation_id=payload.get("conversation_id"),
        message_id=payload.get("message_id"),
        format=payload.get("format") or "mp3",
    )
    job = await enqueue_tts_job(request, speech_text)
    return {
        "original_response": original,
        "blocks": blocks,
        "speech_text": job.text,
        "language": job.language,
        "tts_job": job,
    }


@app.get("/tts/jobs/{job_id}", response_model=TTSJob)
async def get_job(job_id: str) -> TTSJob:
    data = await redis.hgetall(f"tts:job:{job_id}")
    if not data:
        raise HTTPException(status_code=404, detail="TTS job not found")
    return TTSJob(**{key: data[key] for key in TTSJob.model_fields if key in data})

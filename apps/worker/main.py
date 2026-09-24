import asyncio
import os
import uuid
from pathlib import Path
from redis.asyncio import Redis

stream = os.getenv("TTS_STREAM", "tts:generate")
group = os.getenv("TTS_CONSUMER_GROUP", "tts-workers")
consumer = os.getenv("TTS_CONSUMER_NAME", f"worker-{uuid.uuid4().hex[:6]}")
redis = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)


async def handle(job_id: str) -> None:
    key = f"tts:job:{job_id}"
    data = await redis.hgetall(key)
    if not data:
        return
    await redis.hset(key, "status", "processing")
    try:
        # Replace this adapter with Chatterbox/Persian TTS and RustFS upload.
        output = Path("/tmp") / f"{job_id}.wav"
        output.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
        await redis.hset(key, mapping={"status": "completed", "audio_url": f"mock://{output.name}"})
    except Exception as exc:
        await redis.hset(key, mapping={"status": "failed", "error": str(exc)})


async def main() -> None:
    try:
        await redis.xgroup_create(stream, group, id="0", mkstream=True)
    except Exception as exc:
        if "BUSYGROUP" not in str(exc):
            raise
    while True:
        messages = await redis.xreadgroup(group, consumer, {stream: ">"}, count=1, block=5000)
        for _, entries in messages:
            for message_id, fields in entries:
                await handle(fields["job_id"])
                await redis.xack(stream, group, message_id)


if __name__ == "__main__":
    asyncio.run(main())

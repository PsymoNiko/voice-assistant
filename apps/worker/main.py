import asyncio
import os
import uuid
from pathlib import Path

import boto3
from redis.asyncio import Redis

from apps.worker.tts import generate_audio

stream = os.getenv("TTS_STREAM", "tts:generate")
group = os.getenv("TTS_CONSUMER_GROUP", "tts-workers")
consumer = os.getenv("TTS_CONSUMER_NAME", f"worker-{uuid.uuid4().hex[:6]}")
redis = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
public_base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8388").rstrip("/")
rustfs_endpoint = os.getenv("RUSTFS_ENDPOINT", "http://rustfs:9000")
rustfs_access_key = os.getenv("RUSTFS_ACCESS_KEY", "")
rustfs_secret_key = os.getenv("RUSTFS_SECRET_KEY", "")
rustfs_bucket = os.getenv("RUSTFS_BUCKET", "ai-audio")
rustfs_public_endpoint = os.getenv("RUSTFS_PUBLIC_ENDPOINT", "http://localhost:9000").rstrip("/")


def object_key(data: dict[str, str], job_id: str, audio_format: str) -> str:
    conversation_id = data.get("conversation_id") or "unassigned"
    message_id = data.get("message_id") or job_id
    return f"conversations/{conversation_id}/{message_id}/audio.{audio_format}"


def upload_audio(path: Path, key: str, audio_format: str) -> str:
    client = boto3.client(
        "s3",
        endpoint_url=rustfs_endpoint,
        aws_access_key_id=rustfs_access_key,
        aws_secret_access_key=rustfs_secret_key,
        region_name="us-east-1",
    )
    content_type = "audio/wav" if audio_format == "wav" else "audio/mpeg"
    client.upload_file(
        str(path),
        rustfs_bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": rustfs_bucket, "Key": key},
        ExpiresIn=86400,
    ).replace(rustfs_endpoint, rustfs_public_endpoint, 1)


async def handle(job_id: str) -> None:
    key = f"tts:job:{job_id}"
    data = await redis.hgetall(key)
    if not data:
        return
    await redis.hset(key, "status", "processing")
    try:
        audio_format = data.get("format", "mp3")
        if audio_format not in {"mp3", "wav"}:
            raise ValueError("Unsupported audio format")
        output = generate_audio(
            job_id,
            data["text"],
            data.get("language", "en-US"),
            audio_format,
            data.get("voice_id", "ali"),
        )
        audio_key = object_key(data, job_id, audio_format)
        audio_url = upload_audio(output, audio_key, audio_format)
        await redis.hset(
            key,
            mapping={
                "status": "completed",
                "audio_url": audio_url,
            },
        )
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

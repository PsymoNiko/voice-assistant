"""
title: Local Voice Assistant TTS
version: 0.1.0
description: Queues assistant responses in the local TTS pipeline and adds a playable audio link.
requirements: aiohttp
"""

import asyncio
import html
import os

import aiohttp
from pydantic import BaseModel, Field


class Filter:
    class Valves(BaseModel):
        gateway_url: str = Field(default="http://gateway:8080")
        poll_interval_seconds: float = Field(default=0.5, ge=0.1, le=5)
        poll_timeout_seconds: float = Field(default=60, ge=1, le=300)

    def __init__(self):
        self.valves = self.Valves(
            gateway_url=os.getenv("VOICE_ASSISTANT_GATEWAY_URL", "http://gateway:8080")
        )

    async def outlet(self, body: dict, __user__: dict | None = None) -> dict:
        messages = body.get("messages") or []
        assistant = next(
            (message for message in reversed(messages) if message.get("role") == "assistant"),
            None,
        )
        if not assistant or not isinstance(assistant.get("content"), str):
            return body

        request_body = {
            "markdown": assistant["content"],
            "conversation_id": body.get("chat_id"),
            "message_id": body.get("id"),
            "format": "mp3",
        }
        timeout = aiohttp.ClientTimeout(total=self.valves.poll_timeout_seconds + 10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self.valves.gateway_url.rstrip('/')}/responses/speak",
                json=request_body,
            ) as response:
                response.raise_for_status()
                result = await response.json()

            job = result["tts_job"]
            deadline = asyncio.get_running_loop().time() + self.valves.poll_timeout_seconds
            while job["status"] == "queued" or job["status"] == "processing":
                if asyncio.get_running_loop().time() >= deadline:
                    return body
                await asyncio.sleep(self.valves.poll_interval_seconds)
                async with session.get(
                    f"{self.valves.gateway_url.rstrip('/')}/tts/jobs/{job['job_id']}"
                ) as response:
                    response.raise_for_status()
                    job = await response.json()

        if job["status"] != "completed" or not job.get("audio_url"):
            return body

        audio_url = html.escape(job["audio_url"], quote=True)
        assistant["content"] += (
            f'\n\n<audio controls preload="none" src="{audio_url}">'
            f'<a href="{audio_url}">Play audio response</a></audio>'
        )
        return body

from pydantic import BaseModel, Field


class TTSJobRequest(BaseModel):
    text: str = Field(min_length=1)
    language: str | None = None
    voice_id: str = "ali"
    announcement_voice_id: str = "system"
    conversation_id: str | None = None
    message_id: str | None = None
    format: str = "mp3"


class TTSJob(BaseModel):
    job_id: str
    status: str
    language: str
    voice_id: str
    text: str
    conversation_id: str | None = None
    message_id: str | None = None
    format: str = "mp3"
    audio_url: str | None = None
    error: str | None = None

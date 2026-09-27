import os
import subprocess
from pathlib import Path


audio_dir = Path(os.getenv("TTS_AUDIO_DIR", "/tmp/tts-audio"))
tts_engine = os.getenv("TTS_ENGINE", "mock")
chatterbox_device = os.getenv("CHATTERBOX_DEVICE", "cuda")
chatterbox_reference_dir = Path(
    os.getenv("CHATTERBOX_REFERENCE_DIR", "/app/voices")
)
_chatterbox_model = None


def voice_for_language(language: str) -> str:
    return {"fa-IR": "fa", "ru-RU": "ru", "tr-TR": "tr"}.get(language, "en")


def chatterbox_reference(language: str) -> Path | None:
    language_code = language.split("-", 1)[0]
    reference = chatterbox_reference_dir / "ali" / language_code / "reference.wav"
    return reference if reference.is_file() else None


def generate_chatterbox(
    output: Path, text: str, language: str, voice_id: str
) -> None:
    global _chatterbox_model
    try:
        import torchaudio
        from chatterbox.tts import ChatterboxTTS
    except ImportError as exc:
        raise RuntimeError(
            "TTS_ENGINE=chatterbox requires chatterbox-tts and torchaudio"
        ) from exc

    if _chatterbox_model is None:
        _chatterbox_model = ChatterboxTTS.from_pretrained(device=chatterbox_device)

    reference = chatterbox_reference(language) if voice_id == "ali" else None
    kwargs = {"audio_prompt_path": str(reference)} if reference else {}
    waveform = _chatterbox_model.generate(text, **kwargs)
    torchaudio.save(str(output), waveform.cpu(), _chatterbox_model.sr)


def generate_audio(
    job_id: str, text: str, language: str, audio_format: str, voice_id: str
) -> Path:
    audio_dir.mkdir(parents=True, exist_ok=True)
    wav_output = audio_dir / f"{job_id}.wav"
    if tts_engine == "mock":
        wav_output.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
        return wav_output
    if tts_engine == "chatterbox":
        generate_chatterbox(wav_output, text, language, voice_id)
    elif tts_engine == "espeak":
        subprocess.run(
            [
                "espeak-ng",
                "-v",
                voice_for_language(language),
                "-w",
                str(wav_output),
                text,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    else:
        raise RuntimeError(f"Unsupported TTS_ENGINE: {tts_engine}")

    if audio_format == "wav":
        return wav_output
    output = audio_dir / f"{job_id}.{audio_format}"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(wav_output),
            "-codec:a",
            "libmp3lame",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return output

import io
import tempfile
from pathlib import Path

import numpy as np
import soundfile
import torch
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydub import AudioSegment

from app.tts.model import get_tts_model

STORAGE_DIR = Path("voice_profiles")
STORAGE_DIR.mkdir(exist_ok=True)

router = APIRouter()


def convert_audio_to_wav(
    audio_bytes: bytes, content_type: str | None
) -> tuple[np.ndarray, int]:
    """Convert various audio formats to WAV numpy array."""
    audio_buffer = io.BytesIO(audio_bytes)

    # Determine format from content type
    format_map = {
        "audio/x-m4a": "m4a",
        "audio/m4a": "m4a",
        "audio/mp4": "m4a",
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/ogg": "ogg",
        "audio/webm": "webm",
        "audio/aac": "aac",
    }

    fmt = format_map.get(content_type) if content_type else None

    try:
        # Try soundfile first (supports wav, flac, ogg, etc.)
        audio_buffer.seek(0)
        wav_data, sample_rate = soundfile.read(audio_buffer)
        return wav_data, sample_rate
    except Exception:
        # Fall back to pydub for other formats (m4a, mp3, etc.)
        audio_buffer.seek(0)
        audio = AudioSegment.from_file(audio_buffer, format=fmt)
        audio = audio.set_channels(1)  # Convert to mono

        sample_rate = audio.frame_rate
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        samples = samples / (2**15)  # Normalize int16 to float32

        return samples, sample_rate


@router.post("/save")
async def clone_voice(
    name: str = Form(...),
    audio_file: UploadFile = File(...),
):
    reference_audio = await audio_file.read()
    reference_wav, sample_rate = convert_audio_to_wav(
        reference_audio, audio_file.content_type
    )

    # Save to temp file as workaround for library bug with tuple input
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        soundfile.write(tmp.name, reference_wav, sample_rate)
        tmp_path = tmp.name

    model = get_tts_model()
    prompt = model.create_voice_clone_prompt(
        ref_audio=tmp_path,
        x_vector_only_mode=True,  # Don't require transcript
    )

    # Clean up temp file
    Path(tmp_path).unlink(missing_ok=True)

    file_path = STORAGE_DIR / f"{name}.pt"
    torch.save(prompt, file_path)  # 영구 저장
    return {"status": "success", "profile": name}


@router.get("/list")
async def get_voices():
    # 폴더 내 .pt 파일 목록 반환
    return [f.stem for f in STORAGE_DIR.iterdir() if f.suffix == ".pt"]


@router.post("/generate")
async def generate_cloned_tts(
    text: str, voice_name: str, language: str = "Korean"
):
    file_path = STORAGE_DIR / f"{voice_name}.pt"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Voice profile not found")

    # 저장된 특징 벡터 로드 (weights_only=False for custom VoiceClonePromptItem class)
    voice_clone_prompt = torch.load(
        file_path, map_location="cpu", weights_only=False
    )

    # generate_voice_clone
    model = get_tts_model()
    wavs, sr = model.generate_voice_clone(
        text=text,
        voice_clone_prompt=voice_clone_prompt,
        language=language,
    )

    buffer = io.BytesIO()
    soundfile.write(buffer, wavs[0], sr, format="WAV")
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="audio/wav")

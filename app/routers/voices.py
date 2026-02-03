import io
import tempfile
from pathlib import Path

import soundfile
import torch
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app import services
from app.tts.model import get_tts_model
from app.utils.audio import convert_audio_to_wav

STORAGE_DIR = Path("voice_profiles")
STORAGE_DIR.mkdir(exist_ok=True)

router = APIRouter()


# Minimum audio duration in seconds required for voice cloning
# The speech tokenizer uses convolution kernels that need sufficient input length
MIN_AUDIO_DURATION_SECONDS = 1.0


@router.post("/save")
async def clone_voice(
    name: str = Form(...),
    reference_audio: UploadFile = File(...),
    reference_text: str = Form(...),
):
    reference_audio_bytes = await reference_audio.read()

    # Debug logging
    print(f"[DEBUG] filename: {reference_audio.filename}")
    print(f"[DEBUG] content_type: {reference_audio.content_type}")
    print(f"[DEBUG] bytes length: {len(reference_audio_bytes)}")

    reference_wav, sample_rate = convert_audio_to_wav(
        reference_audio_bytes,
        reference_audio.content_type,
        reference_audio.filename,
    )

    print(
        f"[DEBUG] wav shape: {reference_wav.shape}, sample_rate: {sample_rate}"
    )

    # Validate audio duration - too short audio causes kernel size errors in speech tokenizer
    audio_duration = len(reference_wav) / sample_rate
    if audio_duration < MIN_AUDIO_DURATION_SECONDS:
        raise HTTPException(
            status_code=400,
            detail=f"Audio is too short ({audio_duration:.2f}s). "
            f"Please provide at least {MIN_AUDIO_DURATION_SECONDS}s of audio for voice cloning.",
        )

    # Save to temp file as workaround for library bug with tuple input
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        soundfile.write(tmp.name, reference_wav, sample_rate)
        tmp_path = tmp.name

    await services.save_voice_clone(
        base_path=STORAGE_DIR,
        voice_name=name,
        reference_text=reference_text,
        tmp_path=Path(tmp_path),
    )

    # Clean up temp file
    Path(tmp_path).unlink(missing_ok=True)

    return {"status": "success", "profile": name}


@router.get("/list")
async def get_voices():
    # 폴더 내 .pt 파일 목록 반환
    return [f.stem for f in STORAGE_DIR.iterdir() if f.suffix == ".pt"]


@router.get("/generate")
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

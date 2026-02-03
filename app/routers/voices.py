import tempfile
from pathlib import Path

import soundfile
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app import services
from app.schemas.voices import BatchVoiceGenerateRequest, VoiceGenerateRequest
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
) -> dict[str, str]:
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
async def get_voices() -> list[str]:
    """Retrieve the list of saved voice clone profiles.

    Returns
    -------
    list[str]
        List of voice clone profile names.
    """
    # 폴더 내 .pt 파일 목록 반환
    return [f.stem for f in STORAGE_DIR.iterdir() if f.suffix == ".pt"]


@router.post("/generate", response_model=None)
async def generate_cloned_tts(data: VoiceGenerateRequest):
    """Generate TTS audio using a voice clone profile.

    Parameters
    ----------
    data : VoiceGenerateRequest
        Voice generation request data.

    Returns
    -------
    StreamingResponse
        Streaming response containing the generated audio.

    Raises
    ------
    HTTPException
        Raised when the specified voice profile is not found.
    """
    file_path = STORAGE_DIR / f"{data.voice_name}.pt"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Voice profile not found")

    buffer = await services.text_to_speech_generation(
        voice_clone_path=file_path, text=data.text, language=data.language
    )
    return StreamingResponse(content=buffer, media_type="audio/wav")


@router.post("/generate/batch", response_model=None)
async def batch_generate_cloned_tts(
    data: BatchVoiceGenerateRequest,
):
    """Generate TTS audio using a voice clone profile.

    Parameters
    ----------
    data : BatchVoiceGenerateRequest
        Voice generation request data.

    Returns
    -------
    list[StreamingResponse]
        List of streaming responses containing the generated audio.

    Raises
    ------
    HTTPException
        Raised when the specified voice profile is not found.
    """
    file_path = STORAGE_DIR / f"{data.voice_name}.pt"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Voice profile not found")

    buffers = await services.batch_text_to_speech_generation(
        voice_clone_path=file_path, texts=data.texts, language=data.language
    )
    return [
        StreamingResponse(content=buffer, media_type="audio/wav")
        for buffer in buffers
    ]

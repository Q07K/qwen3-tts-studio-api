import base64
import tempfile
from pathlib import Path

import soundfile
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Body
from fastapi.responses import StreamingResponse, FileResponse
import os
import time

from app import services
from app.schemas.voices import BatchVoiceGenerateRequest, VoiceGenerateRequest
from app.utils.audio import convert_audio_to_wav

STORAGE_DIR = Path("voice_profiles")
STORAGE_DIR.mkdir(exist_ok=True)

# 테스트 음성 텍스트 (한국어)
TEST_PREVIEW_TEXT = "이것은 테스트 음성입니다."

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

    # Cleanly truncate audio if it is extremely long to prevent OOM / hanging
    MAX_AUDIO_DURATION_SECONDS = 30.0
    if audio_duration > MAX_AUDIO_DURATION_SECONDS:
        print(f"[INFO] Truncating audio from {audio_duration:.2f}s to {MAX_AUDIO_DURATION_SECONDS}s")
        max_samples = int(MAX_AUDIO_DURATION_SECONDS * sample_rate)
        reference_wav = reference_wav[:max_samples]

    # Save to temp file as workaround for library bug with tuple input
    print(f"[DEBUG] Saving temp wav file: {audio_duration:.2f}s")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        soundfile.write(tmp.name, reference_wav, sample_rate)
        tmp_path = tmp.name

    print(f"[DEBUG] Calling services.save_voice_clone with {tmp_path}")
    await services.save_voice_clone(
        base_path=STORAGE_DIR,
        voice_name=name,
        reference_text=reference_text,
        tmp_path=Path(tmp_path),
    )
    print(f"[DEBUG] services.save_voice_clone returned")

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
        voice_clone_path=file_path,
        text=data.text,
        language=data.language.value,
    )
    return StreamingResponse(content=buffer, media_type="audio/wav")


@router.post("/generate/batch", response_model=None)
async def batch_generate_cloned_tts(
    data: BatchVoiceGenerateRequest,
) -> dict:
    """Generate TTS audio using a voice clone profile.

    Parameters
    ----------
    data : BatchVoiceGenerateRequest
        Voice generation request data.

    Returns
    -------
    dict
        Dictionary containing list of base64-encoded audio data.

    Raises
    ------
    HTTPException
        Raised when the specified voice profile is not found.
    """
    file_path = STORAGE_DIR / f"{data.voice_name}.pt"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Voice profile not found")

    buffers = await services.batch_text_to_speech_generation(
        voice_clone_path=file_path,
        texts=data.texts,
        language=data.language.value,
    )
    return {
        "audio_files": [
            {
                "data": base64.b64encode(buffer.getvalue()).decode("utf-8"),
                "media_type": "audio/wav",
            }
            for buffer in buffers
        ]
    }


@router.get("/{name}/preview", response_model=None)
async def get_voice_preview(name: str):
    """Get or generate a preview audio for a voice profile.

    If a preview audio file exists, return it. Otherwise, generate one
    using the test text and save it for future use.

    Parameters
    ----------
    name : str
        Name of the voice profile.

    Returns
    -------
    FileResponse
        The preview audio file.

    Raises
    ------
    HTTPException
        Raised when the specified voice profile is not found.
    """
    profile_path = STORAGE_DIR / f"{name}.pt"
    preview_path = STORAGE_DIR / f"{name}_preview.wav"

    if not profile_path.exists():
        raise HTTPException(status_code=404, detail="Voice profile not found")

    # 프리뷰 파일이 없으면 생성
    if not preview_path.exists():
        buffer = await services.text_to_speech_generation(
            voice_clone_path=profile_path,
            text=TEST_PREVIEW_TEXT,
            language="korean",
        )
        # 파일로 저장
        with open(preview_path, "wb") as f:
            f.write(buffer.getvalue())

    return FileResponse(
        path=preview_path,
        media_type="audio/wav",
        filename=f"{name}_preview.wav",
    )


@router.delete("/{name}")
async def delete_voice(name: str) -> dict[str, str]:
    """Delete a voice profile and its associated files.

    Parameters
    ----------
    name : str
        Name of the voice profile to delete.

    Returns
    -------
    dict[str, str]
        Status message.

    Raises
    ------
    HTTPException
        Raised when the specified voice profile is not found.
    """
    profile_path = STORAGE_DIR / f"{name}.pt"
    preview_path = STORAGE_DIR / f"{name}_preview.wav"

    if not profile_path.exists():
        raise HTTPException(status_code=404, detail="Voice profile not found")

    # 프로필 파일 삭제
    profile_path.unlink()

    # 프리뷰 파일도 있으면 삭제
    if preview_path.exists():
        preview_path.unlink()

    return {"status": "success", "message": f"Voice profile '{name}' deleted"}


@router.put("/{name}/rename")
async def rename_voice(name: str, new_name: str = Body(..., embed=True)) -> dict[str, str]:
    """Rename a voice profile.

    Parameters
    ----------
    name : str
        Current name of the voice profile.
    new_name : str
        New name for the voice profile.

    Returns
    -------
    dict[str, str]
        Status message and new name.

    Raises
    ------
    HTTPException
        If profile not found or new name already exists.
    """
    current_profile_path = STORAGE_DIR / f"{name}.pt"
    new_profile_path = STORAGE_DIR / f"{new_name}.pt"
    
    current_preview_path = STORAGE_DIR / f"{name}_preview.wav"
    new_preview_path = STORAGE_DIR / f"{new_name}_preview.wav"

    if not current_profile_path.exists():
        raise HTTPException(status_code=404, detail="Voice profile not found")
        
    if new_profile_path.exists():
        raise HTTPException(status_code=400, detail=f"Voice profile '{new_name}' already exists")

    # Rename profile
    current_profile_path.rename(new_profile_path)
    
    # Rename preview if exists
    if current_preview_path.exists():
        current_preview_path.rename(new_preview_path)

    return {"status": "success", "name": new_name}


@router.get("/{name}/export")
async def export_voice(name: str):
    """Export a voice profile as a .pt file.

    Parameters
    ----------
    name : str
        Name of the voice profile to export.

    Returns
    -------
    FileResponse
        The .pt file.
    """
    profile_path = STORAGE_DIR / f"{name}.pt"
    
    if not profile_path.exists():
        raise HTTPException(status_code=404, detail="Voice profile not found")

    return FileResponse(
        path=profile_path,
        media_type="application/octet-stream",
        filename=f"{name}.pt",
    )


@router.get("/{name}/details")
async def get_voice_details(name: str) -> dict:
    """Get details of a voice profile.

    Parameters
    ----------
    name : str
        Name of the voice profile.

    Returns
    -------
    dict
        Dictionary containing file size, creation time, etc.
    """
    profile_path = STORAGE_DIR / f"{name}.pt"
    
    if not profile_path.exists():
        raise HTTPException(status_code=404, detail="Voice profile not found")

    stats = profile_path.stat()
    
    return {
        "name": name,
        "size_bytes": stats.st_size,
        "created_at": stats.st_ctime,
        "modified_at": stats.st_mtime,
    }

import io
import tempfile
from pathlib import Path

import numpy as np
import soundfile
from pydub import AudioSegment


def convert_audio_to_wav(
    audio_bytes: bytes, content_type: str | None, filename: str | None = None
) -> tuple[np.ndarray, int]:
    """Convert various audio formats to WAV numpy array."""
    audio_buffer = io.BytesIO(audio_bytes)

    # Determine format from content type
    content_type_map = {
        "audio/x-m4a": "m4a",
        "audio/m4a": "m4a",
        "audio/mp4": "m4a",
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/ogg": "ogg",
        "audio/webm": "webm",
        "audio/aac": "aac",
    }

    # Determine format from file extension as fallback
    ext_map = {
        ".m4a": "m4a",
        ".mp4": "m4a",
        ".mp3": "mp3",
        ".ogg": "ogg",
        ".webm": "webm",
        ".aac": "aac",
        ".wav": "wav",
        ".flac": "flac",
    }

    fmt = content_type_map.get(content_type) if content_type else None

    # Fallback to extension if content_type didn't match
    if fmt is None and filename:
        ext = Path(filename).suffix.lower()
        fmt = ext_map.get(ext)

    # For formats that need pydub (m4a, mp3, aac, etc.), save to temp file first
    # pydub has issues reading some formats from BytesIO
    if fmt in ("m4a", "mp3", "aac", "webm"):
        with tempfile.NamedTemporaryFile(
            suffix=f".{fmt}", delete=False
        ) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            audio = AudioSegment.from_file(tmp_path, format=fmt)
            audio = audio.set_channels(1)  # Convert to mono
            audio = audio.set_sample_width(2)  # Ensure 16-bit

            sample_rate = audio.frame_rate
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            samples = samples / (2**15)  # Normalize int16 to float32

            return samples, sample_rate
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    try:
        # Try soundfile for wav, flac, ogg, etc.
        audio_buffer.seek(0)
        wav_data, sample_rate = soundfile.read(audio_buffer)
        return wav_data, sample_rate
    except Exception:
        # Fall back to pydub for unknown formats (let pydub auto-detect)
        audio_buffer.seek(0)
        audio = AudioSegment.from_file(audio_buffer)
        audio = audio.set_channels(1)  # Convert to mono
        audio = audio.set_sample_width(2)  # Ensure 16-bit

        sample_rate = audio.frame_rate
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        samples = samples / (2**15)  # Normalize int16 to float32

        return samples, sample_rate

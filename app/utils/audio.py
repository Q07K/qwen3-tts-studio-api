import io
import tempfile
from pathlib import Path

import numpy as np
import subprocess
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

        wav_tmp_path = tmp_path + ".wav"

        try:
            print(f"[DEBUG] converting {tmp_path} to wav using ffmpeg directly")
            # Convert directly to wav using ffmpeg
            # -y: overwrite output
            # -ac 1: convert to mono
            # -vn: disable video
            process = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    tmp_path,
                    "-ac",
                    "1",
                    "-vn",
                    "-f",
                    "wav",
                    wav_tmp_path,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                timeout=60,  # 60 seconds timeout
            )

            if process.returncode != 0:
                print(f"[ERROR] ffmpeg failed: {process.stderr.decode()}")
                raise RuntimeError(
                    f"ffmpeg conversion failed: {process.stderr.decode()}"
                )

            print("[DEBUG] ffmpeg conversion success")
            
            # Read back using soundfile
            samples, sample_rate = soundfile.read(wav_tmp_path)
            
            # Ensure float32
            if samples.dtype != np.float32:
                samples = samples.astype(np.float32)

            return samples, sample_rate
        except subprocess.TimeoutExpired:
            print("[ERROR] ffmpeg timed out")
            raise RuntimeError("Audio conversion timed out")
        finally:
            Path(tmp_path).unlink(missing_ok=True)
            if Path(wav_tmp_path).exists():
                Path(wav_tmp_path).unlink()

    try:
        # Try soundfile for wav, flac, ogg, etc.
        audio_buffer.seek(0)
        wav_data, sample_rate = soundfile.read(audio_buffer)

        # Ensure mono
        if len(wav_data.shape) > 1 and wav_data.shape[1] > 1:
            wav_data = np.mean(wav_data, axis=1)

        # Ensure float32
        if wav_data.dtype != np.float32:
            wav_data = wav_data.astype(np.float32)

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

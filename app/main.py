import os
from pathlib import Path

from fastapi import FastAPI
from pydub import AudioSegment

from app.routers import voices

# Configure ffmpeg path for pydub (Windows)
_ffmpeg_path = (
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages"
)
for _ffmpeg_dir in _ffmpeg_path.glob("Gyan.FFmpeg*"):
    _bin_path = _ffmpeg_dir / "ffmpeg-8.0.1-full_build" / "bin"
    if not _bin_path.exists():
        for _subdir in _ffmpeg_dir.iterdir():
            if _subdir.is_dir() and (_subdir / "bin" / "ffmpeg.exe").exists():
                _bin_path = _subdir / "bin"
                break
    if _bin_path.exists():
        AudioSegment.converter = str(_bin_path / "ffmpeg.exe")
        AudioSegment.ffprobe = str(_bin_path / "ffprobe.exe")
        break

app = FastAPI()

app.include_router(prefix="/api/voices", router=voices.router)

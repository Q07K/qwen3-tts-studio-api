"""Service for generating TTS audio using voice clone profiles."""

import io
from pathlib import Path

import soundfile
import torch
import functools  # Explicit import though it was used in replacement block context
from fastapi.concurrency import run_in_threadpool

from app.tts.model import get_tts_model

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


async def text_to_speech_generation(
    voice_clone_path: Path, text: str, language: str = "Korean"
) -> io.BytesIO:
    """Generate TTS audio using a voice clone profile.

    Parameters
    ----------
    voice_clone_path : Path
        Path to the voice clone profile file.
    text : str
        Text to be synthesized.
    language : str, optional
        Language of the text, by default "Korean"

    Returns
    -------
    io.BytesIO
        Audio data in WAV format as a BytesIO object.
    """
import functools
from fastapi.concurrency import run_in_threadpool

# Cache recently used voice prompts to avoid disk I/O and deserialization overhead
@functools.lru_cache(maxsize=10)
def load_voice_prompt(path: Path):
    return torch.load(path, map_location=DEVICE, weights_only=False)


def _generate_sync(voice_clone_prompt, text, language):
    model = get_tts_model()
    audio_waveforms, sample_rate = model.generate_voice_clone(
        text=text,
        voice_clone_prompt=voice_clone_prompt,
        language=language,
    )
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return audio_waveforms, sample_rate


async def text_to_speech_generation(
    voice_clone_path: Path, text: str, language: str = "Korean"
) -> io.BytesIO:
    """Generate TTS audio using a voice clone profile.

    Parameters
    ----------
    voice_clone_path : Path
        Path to the voice clone profile file.
    text : str
        Text to be synthesized.
    language : str, optional
        Language of the text, by default "Korean"

    Returns
    -------
    io.BytesIO
        Audio data in WAV format as a BytesIO object.
    """
    # Load prompt (cached)
    # Using run_in_threadpool for load might be overkill if cached, but safe for first load
    voice_clone_prompt = await run_in_threadpool(load_voice_prompt, voice_clone_path)

    # Run inference in threadpool to avoid blocking the async event loop
    audio_waveforms, sample_rate = await run_in_threadpool(
        _generate_sync, voice_clone_prompt, text, language
    )

    buffer = io.BytesIO()
    soundfile.write(
        file=buffer,
        data=audio_waveforms[0],
        samplerate=sample_rate,
        format="WAV",
    )
    buffer.seek(0)
    return buffer


async def batch_text_to_speech_generation(
    voice_clone_path: Path, texts: list[str], language: str = "Korean"
) -> list[io.BytesIO]:
    """Generate TTS audio for a batch of texts using a voice clone profile.

    Parameters
    ----------
    voice_clone_path : Path
        Path to the voice clone profile file.
    texts : list[str]
        List of texts to be synthesized.
    language : str, optional
        Language of the texts, by default "Korean"
    Returns
    -------
    list[io.BytesIO]
        List of audio data in WAV format as BytesIO objects.
    """
    voice_clone_prompt = await run_in_threadpool(load_voice_prompt, voice_clone_path)

    languages = [language] * len(texts)
    
    # Run inference in threadpool
    audio_waveforms, sample_rate = await run_in_threadpool(
        _generate_sync, voice_clone_prompt, texts, languages
    )

    buffers: list[io.BytesIO] = []
    for audio_waveform in audio_waveforms:
        buffer = io.BytesIO()
        soundfile.write(
            file=buffer,
            data=audio_waveform,
            samplerate=sample_rate,
            format="WAV",
        )
        buffer.seek(0)
        buffers.append(buffer)
    return buffers

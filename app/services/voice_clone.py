"""Voice cloning service module."""

from pathlib import Path

import torch

from app.tts.model import get_tts_model


async def save_voice_clone(
    base_path: Path, voice_name: str, reference_text: str, tmp_path: Path
) -> None:
    """Qwen TTS voice cloning saving function.

    Parameters
    ----------
    base_path : Path
        Base directory to save the voice clone profile.
    voice_name : str
        Name of the voice clone profile.
    reference_text : str
        Reference text used for voice cloning.
    tmp_path : Path
        Path to the temporary audio file used for voice cloning.
    """
    model = get_tts_model()
    prompt = model.create_voice_clone_prompt(
        ref_audio=tmp_path,
        ref_text=reference_text,
        # x_vector_only_mode=True,  # Don't require transcript
        x_vector_only_mode=False,  # Use custom VoiceClonePromptItem class
    )

    # Save the voice clone prompt
    file_path = base_path / f"{voice_name}.pt"
    torch.save(prompt, file_path)

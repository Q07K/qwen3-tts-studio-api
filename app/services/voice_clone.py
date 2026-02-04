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

    from fastapi.concurrency import run_in_threadpool
    
    def _create_prompt(tmp_path_str, ref_text):
        print(f"[DEBUG] _create_prompt started for {tmp_path_str}")
        try:
            model = get_tts_model()
            print("[DEBUG] model retrieved, calling create_voice_clone_prompt")
            res = model.create_voice_clone_prompt(
                ref_audio=tmp_path_str,
                ref_text=ref_text,
                # x_vector_only_mode=True,  # Don't require transcript
                x_vector_only_mode=False,  # Use custom VoiceClonePromptItem class
            )
            print("[DEBUG] create_voice_clone_prompt finished")
            return res
        except Exception as e:
            print(f"[DEBUG] _create_prompt failed: {e}")
            raise e

    # Run blocking inference in a threadpool
    print("[DEBUG] queuing _create_prompt in threadpool")
    prompt = await run_in_threadpool(_create_prompt, str(tmp_path), reference_text)
    print("[DEBUG] threadpool task finished")

    # Save the voice clone prompt
    file_path = base_path / f"{voice_name}.pt"
    torch.save(prompt, file_path)

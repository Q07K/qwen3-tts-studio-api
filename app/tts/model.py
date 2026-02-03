from functools import lru_cache

from qwen_tts import Qwen3TTSModel

_model: Qwen3TTSModel | None = None


def get_tts_model() -> Qwen3TTSModel:
    """Lazy load the TTS model to avoid memory issues during startup."""
    global _model
    if _model is None:
        _model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            device_map="cuda",
        )
    return _model

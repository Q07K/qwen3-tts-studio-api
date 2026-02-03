from functools import lru_cache

from qwen_tts import Qwen3TTSModel

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda",
)


@lru_cache
def get_tts_model() -> Qwen3TTSModel:
    return model

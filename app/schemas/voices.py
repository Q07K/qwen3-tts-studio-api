from enum import Enum

from pydantic import BaseModel, Field


class VoiceLanguageEnum(str, Enum):
    """Enumeration of supported voice languages."""

    KOREAN = "Korean"
    ENGLISH = "English"
    JAPANESE = "Japanese"
    CHINESE = "Chinese"


class VoiceGenerateRequest(BaseModel):
    """Request model for generating TTS with a voice clone profile."""

    text: str = Field(..., description="The text to be synthesized.")
    voice_name: str = Field(
        ..., description="The name of the voice profile to use."
    )
    language: VoiceLanguageEnum = Field(
        VoiceLanguageEnum.KOREAN, description="The language of the text."
    )


class BatchVoiceGenerateRequest(BaseModel):
    """Request model for batch TTS generation with a voice clone profile."""

    texts: list[str] = Field(
        ..., description="List of texts to be synthesized."
    )
    voice_name: str = Field(
        ..., description="The name of the voice profile to use."
    )
    language: VoiceLanguageEnum = Field(
        VoiceLanguageEnum.KOREAN, description="The language of the texts."
    )

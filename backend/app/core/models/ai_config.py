from __future__ import annotations

import json
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel

_PRESETS_PATH = Path(__file__).resolve().parent.parent.parent / "model_presets.json"


class ModelTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@lru_cache(maxsize=1)
def _load_presets() -> dict[str, dict[str, Any]]:
    with open(_PRESETS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


class AIServiceConfig(BaseModel):
    """Configuration bag sent alongside every AI call.

    Build manually or use the ``from_tier`` factory to load a preset
    and optionally override individual fields.
    """

    model: str = "gemini-2.0-flash"
    system_prompt: str = ""
    instructions: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    response_format: str = "text"

    @classmethod
    def from_tier(cls, tier: ModelTier, **overrides: Any) -> AIServiceConfig:
        """Load a named preset, then apply caller overrides on top."""
        presets = _load_presets()
        preset = presets[tier.value]
        base = {
            "model": preset["model"],
            "temperature": preset["temperature"],
            "max_tokens": preset["max_tokens"],
        }
        base.update(overrides)
        return cls(**base)

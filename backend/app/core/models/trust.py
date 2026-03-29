from __future__ import annotations

from typing import Any

from pydantic import BaseModel, model_validator

from app.core.models.resume import _strip_nones


class _SafeBase(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _drop_nones(cls, values: Any) -> Any:
        return _strip_nones(values)


class TrustCategory(_SafeBase):
    """Score breakdown for one verification category."""

    name: str
    score: float
    evidence: str = ""


class TrustIndex(_SafeBase):
    """Final output of the Trust Evaluator agent."""

    overall_score: float
    categories: list[TrustCategory] = []
    flags: list[str] = []
    reasoning: str = ""

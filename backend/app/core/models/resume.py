from __future__ import annotations

from typing import Any

from pydantic import BaseModel, model_validator


def _strip_nones(data: Any) -> Any:
    """Remove keys with None values so Pydantic uses field defaults."""
    if isinstance(data, dict):
        return {k: _strip_nones(v) for k, v in data.items() if v is not None}
    if isinstance(data, list):
        return [_strip_nones(item) for item in data]
    return data


class _SafeBase(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _drop_nones(cls, values: Any) -> Any:
        return _strip_nones(values)


class Education(_SafeBase):
    institution: str = ""
    degree: str = ""
    field: str = ""
    year: str = ""


class Experience(_SafeBase):
    company: str = ""
    title: str = ""
    duration: str = ""
    description: str = ""


class PersonProfile(_SafeBase):
    """Structured data extracted from a resume by the Classifier agent."""

    full_name: str
    title: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    skills: list[str] = []
    experience: list[Experience] = []
    education: list[Education] = []
    links: list[str] = []
    certifications: list[str] = []

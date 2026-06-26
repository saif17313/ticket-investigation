"""Uniform error response model.

Every error returned by the API uses this exact shape so clients can parse
it predictably. Internal details (stack traces, secrets, environment
variables, file paths) are **never** included.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """One row in the ``details`` list."""

    model_config = ConfigDict(extra="forbid")

    field: str | None = Field(default=None, description="Field path that caused the error, if applicable.")
    message: str = Field(..., min_length=1, description="Human-readable, sanitized error message.")


class ErrorResponse(BaseModel):
    """Uniform error envelope.

    Always wrapped in ``{"error": {...}}`` so success and failure payloads
    are visually distinct.
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Machine-readable error code (e.g. 'validation_error').")
    message: str = Field(..., min_length=1, description="Safe, user-facing summary.")
    details: list[ErrorDetail] = Field(default_factory=list, description="Optional structured details.")

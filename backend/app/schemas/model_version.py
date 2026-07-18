"""Schemas for model version management."""

from pydantic import BaseModel, Field


class ModelActivationRequest(BaseModel):
    traffic_percent: int = Field(100, ge=0, le=100)

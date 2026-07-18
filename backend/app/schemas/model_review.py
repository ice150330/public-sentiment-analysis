"""Schemas for sentiment review queue endpoints."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


SentimentLabel = Literal["positive", "negative", "neutral"]
ReviewStatus = Literal["pending", "reviewed", "ignored"]


class SentimentReviewUpdateRequest(BaseModel):
    status: ReviewStatus = "reviewed"
    corrected_label: SentimentLabel | None = None
    note: str | None = Field(None, max_length=1000)

    @model_validator(mode="after")
    def require_label_for_review(self):
        if self.status == "reviewed" and not self.corrected_label:
            raise ValueError("corrected_label is required when status is reviewed")
        return self

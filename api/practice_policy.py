"""Transparent synthetic practice-policy settings, separate from model quality."""

import json
import os
from pathlib import Path
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, model_validator


class PracticePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    policy_version: Literal["transparent-ranking-v2"] = "transparent-ranking-v2"
    challenge_lower: StrictFloat = Field(default=.6, ge=0, le=1, allow_inf_nan=False)
    challenge_upper: StrictFloat = Field(default=.8, ge=0, le=1, allow_inf_nan=False)
    need_weight: StrictFloat = Field(default=.2, ge=0, le=1, allow_inf_nan=False)
    prerequisite_penalty: StrictFloat = Field(default=.1, ge=0, le=1, allow_inf_nan=False)
    repeat_penalty: StrictFloat = Field(default=.3, ge=0, le=1, allow_inf_nan=False)
    prerequisite_threshold: StrictFloat = Field(default=.6, ge=0, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def ordered_range(self):
        if self.challenge_lower >= self.challenge_upper:
            raise ValueError("Challenge bounds must form an increasing range")
        return self


def _unique_fields(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate practice-policy field")
        value[key] = item
    return value


def configured_policy() -> PracticePolicy:
    path = os.environ.get("PRACTICE_POLICY_CONFIG")
    if not path:
        return PracticePolicy()
    try:
        return PracticePolicy.model_validate(json.loads(Path(path).read_bytes(), object_pairs_hook=_unique_fields))
    except (OSError, ValueError, TypeError, RecursionError):
        raise HTTPException(status_code=503, detail="practice_policy_unavailable") from None

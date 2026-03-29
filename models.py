"""
Data models for:

- Milon API responses
- Database rows
"""

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Milon API response models
# ---------------------------------------------------------------------------


class DeviceInfo(BaseModel):
    """
    Entry from the device name catalogue (GET /api/devices/en_GB)
    """

    name: str | None = None
    device_type: str | None = Field(default=None, alias="type")
    muscle_group: str | None = Field(default=None, alias="mg")

    model_config = {"populate_by_name": True}


class DeviceRecord(BaseModel):
    """
    Per-machine record within a training session
    """

    device_id: int = Field(alias="id")
    timestamp: int = Field(alias="t")
    concentric_weight: float | None = Field(default=None, alias="aw")
    eccentric_weight: float | None = Field(default=None, alias="adw")
    quality_score: int | None = Field(default=None, alias="tr_q")
    reps: int | None = Field(default=None, alias="moves")
    actid: str | None = None
    ngid: int | None = None

    model_config = {"populate_by_name": True}


class TrainingInfo(BaseModel):
    """Top-level metadata for a single training session."""

    timestamp: int = Field(alias="t")
    iteration: int | None = None

    model_config = {"populate_by_name": True}


class SessionData(BaseModel):
    """A single training session as returned by the stats endpoint."""

    training: TrainingInfo
    devices: list[DeviceRecord] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Database row models
# ---------------------------------------------------------------------------


@dataclass
class DeviceNameRow:
    """Row for the device_names table."""

    device_id: int
    name: str | None
    device_type: str | None
    muscle_group: str | None


@dataclass
class TrainingSessionRow:
    """Row for the training_sessions table."""

    session_ts: datetime
    iteration: int | None
    device_id: int
    device_name: str | None
    muscle_group: str | None
    circuit: int
    concentric_weight: float | None
    eccentric_weight: float | None
    quality_score: int | None
    reps: int | None
    actid: str | None
    ngid: int | None
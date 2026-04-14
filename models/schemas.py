"""Pydantic schemas for Sentinel Path MVP."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Task(BaseModel):
    """Project task with deterministic and PERT duration estimates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    duration: float = Field(gt=0)
    optimistic_duration: float
    pessimistic_duration: float

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        """Ensure task id is not empty."""
        if not value.strip():
            raise ValueError("Task id must not be empty.")
        return value

    @model_validator(mode="after")
    def validate_duration_bounds(self) -> "Task":
        """Validate PERT bounds against base duration."""
        if self.optimistic_duration <= 0:
            raise ValueError("optimistic_duration must be > 0.")
        if self.pessimistic_duration <= 0:
            raise ValueError("pessimistic_duration must be > 0.")
        if self.optimistic_duration > self.duration:
            raise ValueError("optimistic_duration must be <= duration.")
        if self.pessimistic_duration < self.duration:
            raise ValueError("pessimistic_duration must be >= duration.")
        return self


class Dependency(BaseModel):
    """Task dependency relation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    from_id: str
    to_id: str
    type: Literal["FS"] = "FS"
    lag: float = 0.0

    @field_validator("from_id", "to_id")
    @classmethod
    def validate_task_ref(cls, value: str) -> str:
        """Ensure dependency references are not empty."""
        if not value.strip():
            raise ValueError("Dependency task reference must not be empty.")
        return value

    @model_validator(mode="after")
    def validate_non_self_dependency(self) -> "Dependency":
        """Prevent self-dependencies."""
        if self.from_id == self.to_id:
            raise ValueError("Self-dependency is not allowed.")
        return self


class ProjectConfig(BaseModel):
    """Configuration for deterministic and Monte-Carlo analysis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mc_iterations: int = Field(default=1000, ge=1)
    convergence_threshold_pct: float = Field(default=0.10, ge=0.0, le=1.0)


class FragilityPoint(BaseModel):
    """Detected fragility point for convergence risk."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str
    incoming_critical_paths: int
    pci_score: float


class SentinelReport(BaseModel):
    """Final report produced by the Sentinel engine."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_duration_base: float
    critical_path_base: list[str]
    fragility_points: list[FragilityPoint]
    cruciality_metrics: dict[str, float]
    project_confidence: float
    sensitivity_spearman: dict[str, float] = Field(default_factory=dict)
    tornado_impact: dict[str, float] = Field(default_factory=dict)

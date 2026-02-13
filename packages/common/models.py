"""Shared pydantic models and enums for Growpad."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageId(str, Enum):
    INTAKE = "INTAKE"
    SYNTHESIZE = "SYNTHESIZE"
    SELECT_FEATURE = "SELECT_FEATURE"
    GENERATE_PRD = "GENERATE_PRD"
    GENERATE_DESIGN = "GENERATE_DESIGN"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    GENERATE_TICKETS = "GENERATE_TICKETS"
    IMPLEMENT = "IMPLEMENT"
    VERIFY = "VERIFY"
    SELF_HEAL = "SELF_HEAL"
    EXPORT = "EXPORT"


class Guardrails(BaseModel):
    max_retries: int = Field(default=2, ge=0, le=2)
    mode: Literal["read_only", "pr"] = "read_only"
    forbidden_paths: list[str] = Field(default_factory=lambda: ["/infra", "/payments"])


class OKRConfig(BaseModel):
    """Optional OKR and strategic context for feature alignment."""

    okrs: list[str] = Field(default_factory=list)
    north_star_metric: str | None = None


class WorkspaceCreateRequest(BaseModel):
    team_name: str
    repo_url: str = "local://target-repo"
    branch: str = "main"
    guardrails: Guardrails = Field(default_factory=Guardrails)
    okr_config: OKRConfig | None = None
    approval_workflow_enabled: bool = False
    approvers: list[str] = Field(default_factory=list)
    linear_url: str | None = None
    jira_url: str | None = None
    team_roles: dict[str, str] = Field(default_factory=dict)
    integration_config: dict[str, dict[str, str]] = Field(default_factory=dict)
    competitor_urls: list[str] = Field(default_factory=list)


class WorkspaceConfig(WorkspaceCreateRequest):
    workspace_id: str
    github_token_encrypted: str | None = None
    created_at: datetime
    updated_at: datetime


class StageHistoryItem(BaseModel):
    stage_id: str
    status: Literal["done", "failed", "skipped"]
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


class RunState(BaseModel):
    run_id: str
    workspace_id: str
    status: RunStatus = RunStatus.PENDING
    current_stage: str | None = None
    retry_count: int = 0
    approval_approved: bool | None = None
    approval_state: dict[str, str] = Field(default_factory=dict)
    selected_feature: dict[str, Any] | None = None
    selected_feature_index: int | None = None
    top_features: list[dict[str, Any]] = Field(default_factory=list)
    stage_history: list[StageHistoryItem] = Field(default_factory=list)
    timestamps: dict[str, datetime | None]
    inputs_hash: str
    outputs_index: dict[str, str | None]
    stack_detected: Literal["python", "javascript", "other"] = "python"


class RunCreateRequest(BaseModel):
    workspace_id: str
    use_sample: bool = True
    evidence_dir: str | None = None
    goal_statement: str | None = None
    fast_mode: bool = True
    selected_feature_index: int | None = Field(default=None, ge=0, le=2)
    design_system_tokens: str | None = None


class RunFeatureSelectRequest(BaseModel):
    selected_feature_index: int = Field(ge=0, le=2)


class RunSummary(BaseModel):
    run_id: str
    status: RunStatus
    current_stage: str | None
    retry_count: int
    outputs_index: dict[str, str | None]
    summary: dict[str, Any] | None = None
    approval_state: dict[str, str] | None = None


class ApiError(BaseModel):
    code: str
    message: str
    stage: str | None = None
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class GithubAuthRequest(BaseModel):
    workspace_id: str
    github_token: str


class GithubAuthResponse(BaseModel):
    workspace_id: str
    connected: bool
    token_hint: str

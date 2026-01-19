"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# === Agent Schemas ===


class AgentResponse(BaseModel):
    """Response for a single agent."""

    id: str
    type: str
    status: str
    currentTask: str | None = None
    startedAt: datetime | None = None
    finishedAt: datetime | None = None
    filesModified: list[str] = Field(default_factory=list)
    toolsUsed: int = 0
    outputLines: int = 0
    error: str | None = None


class AgentOutputLine(BaseModel):
    """A single line of agent output."""

    timestamp: datetime
    content: str
    type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentOutputResponse(BaseModel):
    """Response for agent output."""

    agentId: str
    lines: list[AgentOutputLine]
    totalLines: int


class SpawnAgentRequest(BaseModel):
    """Request to spawn a new agent."""

    type: str = Field(..., pattern="^(coordinator|worker|evaluator)$")
    agentId: str | None = None


class GuidanceRequest(BaseModel):
    """Request to inject guidance into an agent."""

    content: str = Field(..., min_length=1)


# === Cycle Schemas ===


class CycleResponse(BaseModel):
    """Response for a single cycle."""

    cycle: int
    taskType: str
    description: str
    success: bool
    filesModified: list[str] = Field(default_factory=list)
    toolsUsed: dict[str, int] = Field(default_factory=dict)
    durationSeconds: float
    commitHash: str | None = None
    error: str | None = None


class CycleListResponse(BaseModel):
    """Response for list of cycles."""

    cycles: list[CycleResponse]
    total: int


# === Prompt Schemas ===


class PromptResponse(BaseModel):
    """Response for a prompt template."""

    name: str
    content: str
    isCustom: bool
    lastModified: datetime | None = None


class PromptUpdateRequest(BaseModel):
    """Request to update a prompt."""

    content: str = Field(..., min_length=1)


class PromptListResponse(BaseModel):
    """Response for list of prompts."""

    prompts: list[PromptResponse]


# === Status Schemas ===


class AgentPoolStatus(BaseModel):
    """Status of the agent pool."""

    totalAgents: int
    runningAgents: int
    agents: dict[str, list[AgentResponse]]


class StatusResponse(BaseModel):
    """Overall system status."""

    running: bool
    cycle: int
    phase: str
    agentPool: AgentPoolStatus
    recentCycles: list[CycleResponse] = Field(default_factory=list)
    connectionCount: int = 0


# === Orchestrator Schemas ===


class StartOrchestratorRequest(BaseModel):
    """Request to start the orchestrator."""

    maxCycles: int | None = None
    dryRun: bool = False


class OrchestratorResponse(BaseModel):
    """Response for orchestrator operations."""

    success: bool
    message: str

"""Agent Manager - manages pool of agents and their lifecycle."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import TYPE_CHECKING, Any, Callable

from evolution_suite.core.agent import (
    Agent,
    AgentStatus,
    AgentType,
    OutputLine,
    ToolUse,
    UsageMetrics,
)

if TYPE_CHECKING:
    from evolution_suite.core.config import Config


@dataclass
class AgentRelationship:
    """Represents a relationship between two agents."""

    source_id: str
    target_id: str
    relationship_type: str  # 'delegation', 'waiting', 'data_flow', 'completed'
    task_description: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sourceId": self.source_id,
            "targetId": self.target_id,
            "type": self.relationship_type,
            "taskDescription": self.task_description,
            "createdAt": self.created_at.isoformat(),
        }


@dataclass
class DailyUsage:
    """Aggregated usage for a single day."""

    date: date
    metrics: UsageMetrics = field(default_factory=UsageMetrics)
    by_agent_type: dict[str, UsageMetrics] = field(default_factory=dict)
    by_model: dict[str, UsageMetrics] = field(default_factory=dict)
    cycles: int = 0
    successful_cycles: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "metrics": self.metrics.to_dict(),
            "byAgentType": {k: v.to_dict() for k, v in self.by_agent_type.items()},
            "byModel": {k: v.to_dict() for k, v in self.by_model.items()},
            "cycles": self.cycles,
            "successRate": (self.successful_cycles / self.cycles * 100) if self.cycles > 0 else 0,
        }


class AgentManager:
    """Manages pool of agents, lifecycle, and communication."""

    def __init__(
        self,
        config: Config,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.config = config
        self.agents: dict[str, Agent] = {}
        self._on_event = on_event
        self._lock = asyncio.Lock()

        # Relationship tracking
        self.relationships: list[AgentRelationship] = []

        # Usage tracking
        self.total_usage = UsageMetrics()
        self.daily_usage: dict[date, DailyUsage] = {}

    def _emit_event(self, event_type: str, **data: Any) -> None:
        """Emit an event to listeners."""
        if self._on_event:
            self._on_event({
                "type": event_type,
                "timestamp": datetime.now().isoformat(),
                **data,
            })

    def _make_output_callback(self, agent_id: str) -> Callable[[OutputLine], None]:
        """Create output callback for an agent."""
        def callback(line: OutputLine) -> None:
            self._emit_event(
                "agent_output",
                agentId=agent_id,
                line=line.to_dict(),
            )
        return callback

    def _make_tool_callback(self, agent_id: str) -> Callable[[ToolUse], None]:
        """Create tool use callback for an agent."""
        def callback(tool: ToolUse) -> None:
            self._emit_event(
                "agent_tool_use",
                agentId=agent_id,
                tool=tool.to_dict(),
            )
        return callback

    def _make_status_callback(self, agent_id: str) -> Callable[[AgentStatus], None]:
        """Create status change callback for an agent."""
        def callback(status: AgentStatus) -> None:
            self._emit_event(
                "agent_status",
                agentId=agent_id,
                status=status.value,
            )
        return callback

    def _make_usage_callback(self, agent_id: str) -> Callable[[UsageMetrics], None]:
        """Create usage callback for an agent."""
        def callback(metrics: UsageMetrics) -> None:
            agent = self.agents.get(agent_id)
            if agent:
                # Update daily aggregates
                today = date.today()
                if today not in self.daily_usage:
                    self.daily_usage[today] = DailyUsage(date=today)

                daily = self.daily_usage[today]
                daily.metrics.add(metrics)

                # By agent type
                agent_type = agent.type.value
                if agent_type not in daily.by_agent_type:
                    daily.by_agent_type[agent_type] = UsageMetrics()
                daily.by_agent_type[agent_type].add(metrics)

                # By model
                model = agent.model
                if model not in daily.by_model:
                    daily.by_model[model] = UsageMetrics()
                daily.by_model[model].add(metrics)

                # Update total
                self.total_usage.add(metrics)

            # Emit event
            self._emit_event(
                "usage_update",
                agentId=agent_id,
                metrics=metrics.to_dict(),
            )
        return callback

    async def spawn_agent(
        self,
        agent_type: AgentType,
        agent_id: str | None = None,
        assigned_by: str | None = None,
    ) -> Agent:
        """Spawn a new agent of the given type."""
        async with self._lock:
            agent = Agent(
                agent_type=agent_type,
                config=self.config,
                agent_id=agent_id,
                on_output=self._make_output_callback(agent_id or ""),
                on_tool_use=self._make_tool_callback(agent_id or ""),
                on_status_change=self._make_status_callback(agent_id or ""),
                on_usage=self._make_usage_callback(agent_id or ""),
            )

            # Update callbacks with actual ID
            agent._on_output = self._make_output_callback(agent.id)
            agent._on_tool_use = self._make_tool_callback(agent.id)
            agent._on_status_change = self._make_status_callback(agent.id)
            agent._on_usage = self._make_usage_callback(agent.id)

            # Set relationship if assigned by another agent
            if assigned_by:
                agent.assigned_by = assigned_by
                assigner = self.agents.get(assigned_by)
                if assigner:
                    assigner.delegated_to.append(agent.id)

            self.agents[agent.id] = agent

            self._emit_event(
                "agent_spawned",
                agent=agent.to_dict(),
            )

            return agent

    async def start_agent(self, agent_id: str, prompt: str) -> None:
        """Start an agent with a prompt."""
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        # Run in background
        asyncio.create_task(agent.start(prompt))

    async def get_agent(self, agent_id: str) -> Agent | None:
        """Get an agent by ID."""
        return self.agents.get(agent_id)

    async def list_agents(self, agent_type: AgentType | None = None) -> list[Agent]:
        """List all agents, optionally filtered by type."""
        agents = list(self.agents.values())
        if agent_type:
            agents = [a for a in agents if a.type == agent_type]
        return agents

    async def inject_guidance(self, agent_id: str, content: str) -> None:
        """Inject guidance into an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        agent.inject_guidance(content)

        self._emit_event(
            "guidance_injected",
            agentId=agent_id,
            contentLength=len(content),
        )

    async def pause_agent(self, agent_id: str) -> None:
        """Pause an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        agent.pause()

    async def resume_agent(self, agent_id: str) -> None:
        """Resume a paused agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        agent.resume()

    async def stop_agent(self, agent_id: str) -> None:
        """Stop an agent gracefully."""
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        await agent.stop()

    async def kill_agent(self, agent_id: str) -> None:
        """Kill an agent immediately and remove from pool."""
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        await agent.kill()

        async with self._lock:
            del self.agents[agent_id]

        self._emit_event(
            "agent_killed",
            agentId=agent_id,
        )

    async def get_idle_agent(self, agent_type: AgentType) -> Agent | None:
        """Get an idle agent of the given type, or None if none available."""
        for agent in self.agents.values():
            if agent.type == agent_type and agent.status == AgentStatus.IDLE:
                return agent
        return None

    async def get_or_spawn_agent(self, agent_type: AgentType) -> Agent:
        """Get an idle agent or spawn a new one."""
        agent = await self.get_idle_agent(agent_type)
        if agent:
            return agent
        return await self.spawn_agent(agent_type)

    async def stop_all(self) -> None:
        """Stop all agents."""
        tasks = [self.stop_agent(agent_id) for agent_id in list(self.agents.keys())]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def kill_all(self) -> None:
        """Kill all agents immediately."""
        tasks = [self.kill_agent(agent_id) for agent_id in list(self.agents.keys())]
        await asyncio.gather(*tasks, return_exceptions=True)

    def get_status(self) -> dict[str, Any]:
        """Get overall status of the agent pool."""
        agents_by_type: dict[str, list[dict]] = {
            "coordinator": [],
            "worker": [],
            "evaluator": [],
        }

        for agent in self.agents.values():
            agents_by_type[agent.type.value].append(agent.to_dict())

        running_count = sum(
            1 for a in self.agents.values()
            if a.status == AgentStatus.RUNNING
        )

        return {
            "totalAgents": len(self.agents),
            "runningAgents": running_count,
            "agents": agents_by_type,
            "relationships": [r.to_dict() for r in self.relationships],
            "totalUsage": self.total_usage.to_dict(),
        }

    # Relationship management

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        task_description: str | None = None,
    ) -> AgentRelationship:
        """Add a relationship between two agents."""
        relationship = AgentRelationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            task_description=task_description,
        )
        self.relationships.append(relationship)

        # Update agent waiting_for if this is a waiting relationship
        if relationship_type == "waiting":
            agent = self.agents.get(source_id)
            if agent:
                agent.waiting_for = target_id

        self._emit_event(
            "relationship_changed",
            relationship=relationship.to_dict(),
        )

        return relationship

    def clear_waiting(self, agent_id: str) -> None:
        """Clear the waiting status for an agent."""
        agent = self.agents.get(agent_id)
        if agent:
            agent.waiting_for = None

        # Update relationship to completed
        for rel in self.relationships:
            if rel.source_id == agent_id and rel.relationship_type == "waiting":
                rel.relationship_type = "completed"
                self._emit_event(
                    "relationship_changed",
                    relationship=rel.to_dict(),
                )

    def get_active_relationships(self) -> list[AgentRelationship]:
        """Get all active (non-completed) relationships."""
        return [r for r in self.relationships if r.relationship_type != "completed"]

    # Usage reporting

    def get_today_usage(self) -> DailyUsage:
        """Get today's usage statistics."""
        today = date.today()
        if today not in self.daily_usage:
            self.daily_usage[today] = DailyUsage(date=today)
        return self.daily_usage[today]

    def get_usage_history(self, days: int = 7) -> list[DailyUsage]:
        """Get usage history for the past N days."""
        today = date.today()
        result = []
        for i in range(days):
            d = date(today.year, today.month, today.day)
            d = date.fromordinal(d.toordinal() - i)
            if d in self.daily_usage:
                result.append(self.daily_usage[d])
            else:
                result.append(DailyUsage(date=d))
        return result

    def record_cycle(self, success: bool) -> None:
        """Record a completed cycle for today's statistics."""
        today = date.today()
        if today not in self.daily_usage:
            self.daily_usage[today] = DailyUsage(date=today)
        self.daily_usage[today].cycles += 1
        if success:
            self.daily_usage[today].successful_cycles += 1

"""Agent Manager - manages pool of agents and their lifecycle."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

from evolution_suite.core.agent import Agent, AgentStatus, AgentType, OutputLine, ToolUse

if TYPE_CHECKING:
    from evolution_suite.core.config import Config


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

    async def spawn_agent(
        self,
        agent_type: AgentType,
        agent_id: str | None = None,
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
            )

            # Update callbacks with actual ID
            agent._on_output = self._make_output_callback(agent.id)
            agent._on_tool_use = self._make_tool_callback(agent.id)
            agent._on_status_change = self._make_status_callback(agent.id)

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
        }

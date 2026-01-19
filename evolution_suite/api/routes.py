"""API routes for evolution suite."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

from evolution_suite.api.schemas import (
    AgentOutputResponse,
    AgentResponse,
    CycleListResponse,
    CycleResponse,
    GuidanceRequest,
    OrchestratorResponse,
    PromptListResponse,
    PromptResponse,
    PromptUpdateRequest,
    SpawnAgentRequest,
    StartOrchestratorRequest,
    StatusResponse,
)
from evolution_suite.core.agent import AgentType

if TYPE_CHECKING:
    from evolution_suite.core.config import Config
    from evolution_suite.core.orchestrator import Orchestrator
    from evolution_suite.comms.file_channel import FileChannel
    from evolution_suite.comms.websocket import WebSocketManager


def create_router(
    orchestrator: Orchestrator,
    file_channel: FileChannel,
    ws_manager: WebSocketManager,
    config: Config,
) -> APIRouter:
    """Create the API router with all endpoints."""

    router = APIRouter(prefix="/api")

    # === Status ===

    @router.get("/status", response_model=StatusResponse)
    async def get_status() -> StatusResponse:
        """Get overall system status."""
        status = orchestrator.get_status()
        status["connectionCount"] = ws_manager.get_connection_count()
        return StatusResponse(**status)

    # === Agents ===

    @router.get("/agents", response_model=list[AgentResponse])
    async def list_agents(agent_type: str | None = None):
        """List all agents."""
        type_filter = AgentType(agent_type) if agent_type else None
        agents = await orchestrator.agent_manager.list_agents(type_filter)
        return [AgentResponse(**a.to_dict()) for a in agents]

    @router.get("/agents/{agent_id}", response_model=AgentResponse)
    async def get_agent(agent_id: str):
        """Get a specific agent."""
        agent = await orchestrator.agent_manager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return AgentResponse(**agent.to_dict())

    @router.get("/agents/{agent_id}/output", response_model=AgentOutputResponse)
    async def get_agent_output(
        agent_id: str,
        limit: int = 100,
        offset: int = 0,
    ):
        """Get agent output buffer."""
        agent = await orchestrator.agent_manager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        lines = agent.get_output(limit=limit, offset=offset)
        return AgentOutputResponse(
            agentId=agent_id,
            lines=[
                {
                    "timestamp": line.timestamp,
                    "content": line.content,
                    "type": line.line_type,
                    "metadata": line.metadata,
                }
                for line in lines
            ],
            totalLines=len(agent.output_buffer),
        )

    @router.post("/agents", response_model=AgentResponse)
    async def spawn_agent(request: SpawnAgentRequest):
        """Spawn a new agent."""
        try:
            agent_type = AgentType(request.type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid agent type")

        agent = await orchestrator.agent_manager.spawn_agent(
            agent_type,
            agent_id=request.agentId,
        )
        return AgentResponse(**agent.to_dict())

    @router.post("/agents/{agent_id}/inject", response_model=OrchestratorResponse)
    async def inject_guidance(agent_id: str, request: GuidanceRequest):
        """Inject guidance into an agent."""
        try:
            await orchestrator.agent_manager.inject_guidance(agent_id, request.content)
            return OrchestratorResponse(
                success=True,
                message=f"Guidance injected into {agent_id}",
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/agents/{agent_id}/pause", response_model=OrchestratorResponse)
    async def pause_agent(agent_id: str):
        """Pause an agent."""
        try:
            await orchestrator.agent_manager.pause_agent(agent_id)
            return OrchestratorResponse(success=True, message=f"Agent {agent_id} paused")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/agents/{agent_id}/resume", response_model=OrchestratorResponse)
    async def resume_agent(agent_id: str):
        """Resume a paused agent."""
        try:
            await orchestrator.agent_manager.resume_agent(agent_id)
            return OrchestratorResponse(success=True, message=f"Agent {agent_id} resumed")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.delete("/agents/{agent_id}", response_model=OrchestratorResponse)
    async def kill_agent(agent_id: str):
        """Kill an agent."""
        try:
            await orchestrator.agent_manager.kill_agent(agent_id)
            return OrchestratorResponse(success=True, message=f"Agent {agent_id} killed")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # === Cycles ===

    @router.get("/cycles", response_model=CycleListResponse)
    async def list_cycles(limit: int = 20, offset: int = 0):
        """List evolution cycles."""
        cycles = orchestrator.cycles_history
        total = len(cycles)
        cycles = cycles[offset : offset + limit]
        return CycleListResponse(
            cycles=[CycleResponse(**c.to_dict()) for c in reversed(cycles)],
            total=total,
        )

    @router.get("/cycles/{cycle_num}", response_model=CycleResponse)
    async def get_cycle(cycle_num: int):
        """Get a specific cycle."""
        for cycle in orchestrator.cycles_history:
            if cycle.cycle == cycle_num:
                return CycleResponse(**cycle.to_dict())
        raise HTTPException(status_code=404, detail="Cycle not found")

    # === Prompts ===

    @router.get("/prompts", response_model=PromptListResponse)
    async def list_prompts():
        """List all prompt templates."""
        prompts = []
        prompt_names = ["coordinator", "worker", "evaluator"]

        for name in prompt_names:
            custom_path = config.get_prompt_path(name)
            if custom_path and custom_path.exists():
                prompts.append(PromptResponse(
                    name=name,
                    content=custom_path.read_text(),
                    isCustom=True,
                    lastModified=datetime.fromtimestamp(custom_path.stat().st_mtime),
                ))
            else:
                # Use default
                default_path = Path(__file__).parent.parent.parent / "templates" / "prompts" / f"{name}.md"
                if default_path.exists():
                    prompts.append(PromptResponse(
                        name=name,
                        content=default_path.read_text(),
                        isCustom=False,
                        lastModified=None,
                    ))

        return PromptListResponse(prompts=prompts)

    @router.get("/prompts/{name}", response_model=PromptResponse)
    async def get_prompt(name: str):
        """Get a prompt template."""
        if name not in ["coordinator", "worker", "evaluator"]:
            raise HTTPException(status_code=404, detail="Prompt not found")

        custom_path = config.get_prompt_path(name)
        if custom_path and custom_path.exists():
            return PromptResponse(
                name=name,
                content=custom_path.read_text(),
                isCustom=True,
                lastModified=datetime.fromtimestamp(custom_path.stat().st_mtime),
            )

        default_path = Path(__file__).parent.parent.parent / "templates" / "prompts" / f"{name}.md"
        if default_path.exists():
            return PromptResponse(
                name=name,
                content=default_path.read_text(),
                isCustom=False,
                lastModified=None,
            )

        raise HTTPException(status_code=404, detail="Prompt not found")

    @router.put("/prompts/{name}", response_model=PromptResponse)
    async def update_prompt(name: str, request: PromptUpdateRequest):
        """Update a prompt template."""
        if name not in ["coordinator", "worker", "evaluator"]:
            raise HTTPException(status_code=404, detail="Prompt not found")

        # Write to custom location
        prompts_dir = config.get_state_dir() / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = prompts_dir / f"{name}.md"
        prompt_path.write_text(request.content)

        # Broadcast update
        await ws_manager.broadcast({
            "type": "prompt_updated",
            "name": name,
        })

        return PromptResponse(
            name=name,
            content=request.content,
            isCustom=True,
            lastModified=datetime.now(),
        )

    # === Orchestrator ===

    @router.post("/orchestrator/start", response_model=OrchestratorResponse)
    async def start_orchestrator(request: StartOrchestratorRequest):
        """Start the evolution orchestrator."""
        if orchestrator.running:
            raise HTTPException(status_code=400, detail="Orchestrator already running")

        import asyncio
        asyncio.create_task(orchestrator.run(
            max_cycles=request.maxCycles,
            dry_run=request.dryRun,
        ))

        return OrchestratorResponse(
            success=True,
            message="Orchestrator started",
        )

    @router.post("/orchestrator/stop", response_model=OrchestratorResponse)
    async def stop_orchestrator():
        """Stop the orchestrator after current cycle."""
        if not orchestrator.running:
            raise HTTPException(status_code=400, detail="Orchestrator not running")

        await orchestrator.stop()
        return OrchestratorResponse(
            success=True,
            message="Stop requested - will stop after current cycle",
        )

    @router.post("/orchestrator/force-stop", response_model=OrchestratorResponse)
    async def force_stop_orchestrator():
        """Force stop the orchestrator immediately."""
        await orchestrator.force_stop()
        return OrchestratorResponse(
            success=True,
            message="Orchestrator force stopped",
        )

    return router

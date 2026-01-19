"""API routes for evolution suite."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

from evolution_suite.api.schemas import (
    AgentOutputResponse,
    AgentRelationshipResponse,
    AgentResponse,
    BulkActionRequest,
    BulkGuidanceRequest,
    CycleListResponse,
    CycleResponse,
    DailyUsageResponse,
    GuidanceRequest,
    OrchestratorResponse,
    PromptListResponse,
    PromptResponse,
    PromptUpdateRequest,
    RelationshipListResponse,
    SpawnAgentRequest,
    StartOrchestratorRequest,
    StateFileListResponse,
    StateFileResponse,
    StateFileUpdateRequest,
    StatusResponse,
    UsageHistoryResponse,
    UsageMetricsResponse,
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

    # === Usage ===

    @router.get("/usage", response_model=UsageHistoryResponse)
    async def get_usage(days: int = 7):
        """Get usage statistics."""
        today_usage = orchestrator.agent_manager.get_today_usage()
        history = orchestrator.agent_manager.get_usage_history(days)

        return UsageHistoryResponse(
            today=DailyUsageResponse(**today_usage.to_dict()),
            history=[DailyUsageResponse(**d.to_dict()) for d in history],
            total=UsageMetricsResponse(**orchestrator.agent_manager.total_usage.to_dict()),
        )

    @router.get("/usage/today", response_model=DailyUsageResponse)
    async def get_today_usage():
        """Get today's usage statistics."""
        usage = orchestrator.agent_manager.get_today_usage()
        return DailyUsageResponse(**usage.to_dict())

    # === State Files ===

    @router.get("/state-files", response_model=StateFileListResponse)
    async def list_state_files():
        """List all state files in the evolution directory."""
        state_dir = config.get_state_dir()
        files = []

        # Main state files
        for pattern in ["*.md", "*.json", ".agent-state/*.json", ".guidance/*.md"]:
            for path in state_dir.glob(pattern):
                if path.is_file():
                    try:
                        content = path.read_text()
                        mtime = datetime.fromtimestamp(path.stat().st_mtime)
                        files.append(StateFileResponse(
                            name=path.name,
                            path=str(path.relative_to(state_dir)),
                            content=content,
                            lastModified=mtime,
                            lockedBy=None,  # TODO: Parse lock info if applicable
                        ))
                    except Exception:
                        continue

        return StateFileListResponse(files=files)

    @router.get("/state-files/{file_path:path}", response_model=StateFileResponse)
    async def get_state_file(file_path: str):
        """Get a specific state file."""
        state_dir = config.get_state_dir()
        full_path = state_dir / file_path

        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail="State file not found")

        # Security check - ensure path is within state dir
        try:
            full_path.resolve().relative_to(state_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")

        content = full_path.read_text()
        mtime = datetime.fromtimestamp(full_path.stat().st_mtime)

        return StateFileResponse(
            name=full_path.name,
            path=file_path,
            content=content,
            lastModified=mtime,
            lockedBy=None,
        )

    @router.put("/state-files/{file_path:path}", response_model=StateFileResponse)
    async def update_state_file(file_path: str, request: StateFileUpdateRequest):
        """Update a state file."""
        state_dir = config.get_state_dir()
        full_path = state_dir / file_path

        # Security check
        try:
            full_path.resolve().relative_to(state_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        full_path.write_text(request.content)

        # Broadcast update
        await ws_manager.broadcast({
            "type": "state_file_changed",
            "file": {
                "name": full_path.name,
                "path": file_path,
                "lastModified": datetime.now().isoformat(),
            },
        })

        return StateFileResponse(
            name=full_path.name,
            path=file_path,
            content=request.content,
            lastModified=datetime.now(),
            lockedBy=None,
        )

    # === Relationships ===

    @router.get("/relationships", response_model=RelationshipListResponse)
    async def list_relationships(active_only: bool = True):
        """List agent relationships."""
        if active_only:
            relationships = orchestrator.agent_manager.get_active_relationships()
        else:
            relationships = orchestrator.agent_manager.relationships

        return RelationshipListResponse(
            relationships=[AgentRelationshipResponse(**r.to_dict()) for r in relationships]
        )

    # === Bulk Operations ===

    @router.post("/agents/bulk/guidance", response_model=OrchestratorResponse)
    async def bulk_inject_guidance(request: BulkGuidanceRequest):
        """Inject guidance into multiple agents."""
        success_count = 0
        for agent_id in request.agentIds:
            try:
                await orchestrator.agent_manager.inject_guidance(agent_id, request.content)
                success_count += 1
            except ValueError:
                continue

        return OrchestratorResponse(
            success=success_count > 0,
            message=f"Guidance injected into {success_count}/{len(request.agentIds)} agents",
        )

    @router.post("/agents/bulk/action", response_model=OrchestratorResponse)
    async def bulk_agent_action(request: BulkActionRequest):
        """Perform an action on multiple agents."""
        success_count = 0
        for agent_id in request.agentIds:
            try:
                if request.action == "pause":
                    await orchestrator.agent_manager.pause_agent(agent_id)
                elif request.action == "resume":
                    await orchestrator.agent_manager.resume_agent(agent_id)
                elif request.action == "kill":
                    await orchestrator.agent_manager.kill_agent(agent_id)
                success_count += 1
            except ValueError:
                continue

        return OrchestratorResponse(
            success=success_count > 0,
            message=f"{request.action.capitalize()} executed on {success_count}/{len(request.agentIds)} agents",
        )

    return router

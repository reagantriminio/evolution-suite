"""Orchestrator - coordinates evolution cycles across agent pool."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from evolution_suite.core.agent import AgentStatus, AgentType
from evolution_suite.core.agent_manager import AgentManager

if TYPE_CHECKING:
    from evolution_suite.core.config import Config


class TaskType(str, Enum):
    """Types of evolution tasks."""

    EVOLVE = "EVOLVE"
    CLEANUP = "CLEANUP"
    BUGFIX = "BUGFIX"
    DONE = "DONE"


class CyclePhase(str, Enum):
    """Phases of an evolution cycle."""

    IDLE = "IDLE"
    COORDINATING = "COORDINATING"
    WORKING = "WORKING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class CoordinatorDecision:
    """Decision from coordinator agent."""

    task_type: TaskType
    description: str
    task_xml: str
    files: list[str]
    skills: list[str]


@dataclass
class CycleResult:
    """Result of an evolution cycle."""

    cycle: int
    task_type: TaskType
    description: str
    success: bool
    files_modified: list[str]
    tools_used: dict[str, int]
    duration_seconds: float
    commit_hash: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle": self.cycle,
            "taskType": self.task_type.value,
            "description": self.description,
            "success": self.success,
            "filesModified": self.files_modified,
            "toolsUsed": self.tools_used,
            "durationSeconds": self.duration_seconds,
            "commitHash": self.commit_hash,
            "error": self.error,
        }


class Orchestrator:
    """Coordinates evolution cycles across the agent pool."""

    def __init__(
        self,
        config: Config,
        project_root: Path,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.config = config
        self.project_root = project_root
        self.agent_manager = AgentManager(config, on_event=on_event)
        self._on_event = on_event

        self.cycle = 0
        self.phase = CyclePhase.IDLE
        self.running = False
        self.cycles_history: list[CycleResult] = []

        self._stop_requested = False

    def _emit_event(self, event_type: str, **data: Any) -> None:
        """Emit an event to listeners."""
        if self._on_event:
            self._on_event({
                "type": event_type,
                "timestamp": datetime.now().isoformat(),
                **data,
            })

    def _set_phase(self, phase: CyclePhase) -> None:
        """Update phase and emit event."""
        self.phase = phase
        self._emit_event("phase_changed", phase=phase.value)

    async def run(
        self,
        max_cycles: int | None = None,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        """Run the evolution loop."""
        self.running = True
        self._stop_requested = False
        consecutive_failures = 0
        max_consecutive_failures = 3

        self._emit_event("orchestrator_started", maxCycles=max_cycles)

        try:
            while self.running and not self._stop_requested:
                self.cycle += 1

                # Check limits
                if max_cycles and self.cycle > max_cycles:
                    self._emit_event("max_cycles_reached", cycles=max_cycles)
                    break

                if consecutive_failures >= max_consecutive_failures:
                    self._emit_event(
                        "too_many_failures",
                        failures=consecutive_failures,
                    )
                    break

                # Run cycle
                result = await self.run_cycle(dry_run=dry_run)

                if result.success:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1

                # Check for DONE
                if result.task_type == TaskType.DONE:
                    self._emit_event("evolution_complete", reason=result.description)
                    break

        finally:
            self.running = False
            self._set_phase(CyclePhase.IDLE)
            self._emit_event("orchestrator_stopped", cycle=self.cycle)

    async def run_cycle(self, dry_run: bool = False) -> CycleResult:
        """Run a single evolution cycle."""
        start_time = datetime.now()

        self._emit_event("cycle_started", cycle=self.cycle)

        try:
            # Phase 1: Coordinator decides what to do
            self._set_phase(CyclePhase.COORDINATING)
            decision = await self._run_coordinator(dry_run)

            if decision is None:
                return self._make_failure_result(
                    "Could not parse coordinator decision",
                    start_time,
                )

            # Check for DONE
            if decision.task_type == TaskType.DONE:
                result = CycleResult(
                    cycle=self.cycle,
                    task_type=TaskType.DONE,
                    description=decision.description,
                    success=True,
                    files_modified=[],
                    tools_used={},
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                )
                self.cycles_history.append(result)
                self._emit_event("cycle_completed", cycle=self.cycle, result=result.to_dict())
                return result

            # Phase 2: Worker executes the task
            self._set_phase(CyclePhase.WORKING)
            worker_result = await self._run_worker(decision, dry_run)

            if not worker_result["success"]:
                await self._rollback()
                result = self._make_failure_result(
                    worker_result.get("error", "Worker failed"),
                    start_time,
                    decision,
                )
                self.cycles_history.append(result)
                self._emit_event("cycle_failed", cycle=self.cycle, result=result.to_dict())
                return result

            # Phase 3: Evaluator validates (optional)
            self._set_phase(CyclePhase.EVALUATING)
            # For now, skip evaluation - can be added later

            # Success
            result = CycleResult(
                cycle=self.cycle,
                task_type=decision.task_type,
                description=decision.description,
                success=True,
                files_modified=worker_result.get("files_modified", []),
                tools_used=worker_result.get("tools_used", {}),
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                commit_hash=await self._get_last_commit_hash(),
            )

            self.cycles_history.append(result)
            self._set_phase(CyclePhase.COMPLETED)
            self._emit_event("cycle_completed", cycle=self.cycle, result=result.to_dict())

            # Update state file
            await self._update_state(result)

            return result

        except Exception as e:
            result = self._make_failure_result(str(e), start_time)
            self.cycles_history.append(result)
            self._emit_event("cycle_failed", cycle=self.cycle, error=str(e))
            return result

    async def _run_coordinator(self, dry_run: bool) -> CoordinatorDecision | None:
        """Run the coordinator agent to decide what to do."""
        prompt = await self._build_coordinator_prompt()

        if dry_run:
            return CoordinatorDecision(
                task_type=TaskType.DONE,
                description="Dry run - no action",
                task_xml="",
                files=[],
                skills=[],
            )

        # Get or spawn a coordinator
        agent = await self.agent_manager.get_or_spawn_agent(AgentType.COORDINATOR)
        agent.current_task = "Deciding next evolution task"

        # Start and wait for completion
        await agent.start(prompt)

        # Wait for agent to finish
        while agent.status == AgentStatus.RUNNING:
            await asyncio.sleep(0.5)

        if agent.status == AgentStatus.FAILED:
            return None

        # Parse decision from output
        output = "\n".join(line.content for line in agent.output_buffer if line.line_type in ("text", "result"))
        return self._parse_coordinator_decision(output)

    async def _run_worker(self, decision: CoordinatorDecision, dry_run: bool) -> dict[str, Any]:
        """Run the worker agent to execute the task."""
        prompt = await self._build_worker_prompt(decision)

        if dry_run:
            return {"success": True, "files_modified": [], "tools_used": {}}

        # Get or spawn a worker
        agent = await self.agent_manager.get_or_spawn_agent(AgentType.WORKER)
        agent.current_task = decision.description

        # Start and wait for completion
        await agent.start(prompt)

        # Wait for agent to finish
        while agent.status == AgentStatus.RUNNING:
            await asyncio.sleep(0.5)

        # Collect results
        tools_used: dict[str, int] = {}
        for tool in agent.tools_used:
            tools_used[tool.tool_name] = tools_used.get(tool.tool_name, 0) + 1

        return {
            "success": agent.status != AgentStatus.FAILED and agent.error is None,
            "files_modified": agent.files_modified,
            "tools_used": tools_used,
            "error": agent.error,
        }

    async def _build_coordinator_prompt(self) -> str:
        """Build the coordinator prompt."""
        template = await self._load_prompt("coordinator")

        state_content = self._read_file(self.config.get_state_file())
        log_content = self._get_recent_log_entries(10)
        project_content = self._read_file(self.config.get_state_dir() / "EVOLUTION_PROJECT.md")

        prompt = template.replace("{{STATE}}", state_content)
        prompt = prompt.replace("{{LOG}}", log_content)
        prompt = prompt.replace("{{PROJECT}}", project_content)

        # Inject guidance if available
        guidance = self._read_guidance("coordinator")
        if guidance:
            prompt = prompt.replace("{{INJECTED_GUIDANCE}}", f"\n## Injected Guidance\n\n{guidance}\n")
        else:
            prompt = prompt.replace("{{INJECTED_GUIDANCE}}", "")

        return prompt

    async def _build_worker_prompt(self, decision: CoordinatorDecision) -> str:
        """Build the worker prompt."""
        template = await self._load_prompt("worker")

        project_content = self._read_file(self.config.get_state_dir() / "EVOLUTION_PROJECT.md")

        prompt = template.replace("{{TASK_TYPE}}", decision.task_type.value)
        prompt = prompt.replace("{{TASK_XML}}", decision.task_xml)
        prompt = prompt.replace("{{PROJECT}}", project_content)

        # Inject guidance if available
        guidance = self._read_guidance("worker")
        if guidance:
            prompt = prompt.replace("{{INJECTED_GUIDANCE}}", f"\n## Injected Guidance\n\n{guidance}\n")
        else:
            prompt = prompt.replace("{{INJECTED_GUIDANCE}}", "")

        return prompt

    async def _load_prompt(self, name: str) -> str:
        """Load a prompt template."""
        # Check for custom prompt in config
        custom_path = self.config.get_prompt_path(name)
        if custom_path and custom_path.exists():
            return custom_path.read_text()

        # Fall back to default template
        default_path = Path(__file__).parent.parent.parent / "templates" / "prompts" / f"{name}.md"
        if default_path.exists():
            return default_path.read_text()

        raise FileNotFoundError(f"Prompt template not found: {name}")

    def _read_file(self, path: Path) -> str:
        """Read file contents."""
        if path.exists():
            return path.read_text()
        return ""

    def _read_guidance(self, agent_type: str) -> str | None:
        """Read injected guidance for an agent type."""
        guidance_dir = self.config.get_guidance_dir()
        # Look for any guidance file matching the type
        for f in guidance_dir.glob(f"{agent_type}*.md"):
            content = f.read_text().strip()
            if content:
                return content
        return None

    def _get_recent_log_entries(self, max_entries: int) -> str:
        """Get recent log entries."""
        log_content = self._read_file(self.config.get_log_file())
        if not log_content:
            return ""

        cycles = re.split(r"(?=## Cycle \d+:)", log_content)
        header = cycles[0] if cycles and not cycles[0].startswith("## Cycle") else ""
        recent = cycles[-max_entries:] if len(cycles) > max_entries else cycles

        if len(cycles) > max_entries:
            note = f"\n\n*[Showing last {max_entries} of {len(cycles) - 1} cycles]*\n\n"
            return header + note + "".join(recent)

        return log_content

    def _parse_coordinator_decision(self, output: str) -> CoordinatorDecision | None:
        """Parse coordinator decision from output."""
        for task_type in TaskType:
            pattern = rf"{task_type.value}:\s*(.+?)(?=\n\n|\Z)"
            match = re.search(pattern, output, re.DOTALL)
            if match:
                description = match.group(1).strip()

                # Extract XML task if present
                xml_match = re.search(r"<task>.*?</task>", output, re.DOTALL)
                task_xml = xml_match.group(0) if xml_match else description

                # Extract files
                files_match = re.search(r"<files>(.*?)</files>", task_xml, re.DOTALL)
                files = []
                if files_match:
                    files = [f.strip() for f in files_match.group(1).split("\n") if f.strip()]

                # Extract skills
                skills_match = re.search(r"<skills>(.*?)</skills>", task_xml, re.DOTALL)
                skills = []
                if skills_match:
                    skills = [s.strip() for s in skills_match.group(1).split(",") if s.strip()]

                return CoordinatorDecision(
                    task_type=task_type,
                    description=description,
                    task_xml=task_xml,
                    files=files,
                    skills=skills,
                )

        return None

    async def _rollback(self) -> None:
        """Rollback changes on failure."""
        import subprocess

        try:
            subprocess.run(
                ["git", "reset", "--hard", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["git", "clean", "-fd"],
                cwd=self.project_root,
                capture_output=True,
                check=False,
            )
        except Exception:
            pass

    async def _get_last_commit_hash(self) -> str | None:
        """Get the last commit hash."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()[:8]
        except Exception:
            return None

    async def _update_state(self, result: CycleResult) -> None:
        """Update the state file after a cycle."""
        state_file = self.config.get_state_file()
        content = self._read_file(state_file)

        # Update cycle number
        content = re.sub(r"\*\*Cycle\*\*: \d+", f"**Cycle**: {self.cycle}", content)

        # Update timestamp
        content = re.sub(
            r"\*\*Last Updated\*\*: .*",
            f"**Last Updated**: {datetime.now().isoformat()}",
            content,
        )

        state_file.write_text(content)

    def _make_failure_result(
        self,
        error: str,
        start_time: datetime,
        decision: CoordinatorDecision | None = None,
    ) -> CycleResult:
        """Create a failure result."""
        return CycleResult(
            cycle=self.cycle,
            task_type=decision.task_type if decision else TaskType.EVOLVE,
            description=decision.description if decision else "Unknown",
            success=False,
            files_modified=[],
            tools_used={},
            duration_seconds=(datetime.now() - start_time).total_seconds(),
            error=error,
        )

    async def stop(self) -> None:
        """Stop the orchestrator after current cycle."""
        self._stop_requested = True
        self._emit_event("stop_requested")

    async def force_stop(self) -> None:
        """Force stop immediately."""
        self._stop_requested = True
        self.running = False
        await self.agent_manager.stop_all()
        self._emit_event("force_stopped")

    def get_status(self) -> dict[str, Any]:
        """Get orchestrator status."""
        return {
            "running": self.running,
            "cycle": self.cycle,
            "phase": self.phase.value,
            "agentPool": self.agent_manager.get_status(),
            "recentCycles": [r.to_dict() for r in self.cycles_history[-10:]],
        }

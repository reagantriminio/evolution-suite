"""Agent class - wraps Claude subprocess with streaming output."""

from __future__ import annotations

import asyncio
import json
import subprocess
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable

if TYPE_CHECKING:
    from evolution_suite.core.config import Config


class AgentType(str, Enum):
    """Types of agents in the evolution system."""

    COORDINATOR = "coordinator"
    WORKER = "worker"
    EVALUATOR = "evaluator"


class AgentStatus(str, Enum):
    """Status of an agent."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class OutputLine:
    """A single line of agent output."""

    timestamp: datetime
    content: str
    line_type: str  # thinking, text, tool_use, tool_result, error
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "type": self.line_type,
            "metadata": self.metadata,
        }


@dataclass
class ToolUse:
    """Record of a tool invocation."""

    tool_name: str
    tool_input: dict[str, Any]
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool_name,
            "input": self.tool_input,
            "timestamp": self.timestamp.isoformat(),
        }


class Agent:
    """Wraps a Claude subprocess with streaming output and lifecycle management."""

    def __init__(
        self,
        agent_type: AgentType,
        config: Config,
        agent_id: str | None = None,
        on_output: Callable[[OutputLine], None] | None = None,
        on_tool_use: Callable[[ToolUse], None] | None = None,
        on_status_change: Callable[[AgentStatus], None] | None = None,
    ):
        self.id = agent_id or f"{agent_type.value}-{uuid.uuid4().hex[:8]}"
        self.type = agent_type
        self.config = config
        self.status = AgentStatus.IDLE
        self.process: subprocess.Popen | None = None
        self.output_buffer: deque[OutputLine] = deque(maxlen=10000)
        self.tools_used: list[ToolUse] = []
        self.files_modified: list[str] = []
        self.current_task: str | None = None
        self.started_at: datetime | None = None
        self.finished_at: datetime | None = None
        self.error: str | None = None

        # Callbacks
        self._on_output = on_output
        self._on_tool_use = on_tool_use
        self._on_status_change = on_status_change

        # Control flags
        self._should_stop = False
        self._paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially

    def _set_status(self, status: AgentStatus) -> None:
        """Update status and notify callback."""
        self.status = status
        if self._on_status_change:
            self._on_status_change(status)

    def _add_output(self, line: OutputLine) -> None:
        """Add output line and notify callback."""
        self.output_buffer.append(line)
        if self._on_output:
            self._on_output(line)

    def _add_tool_use(self, tool: ToolUse) -> None:
        """Record tool use and notify callback."""
        self.tools_used.append(tool)
        if self._on_tool_use:
            self._on_tool_use(tool)

        # Track file modifications
        if tool.tool_name in ("Edit", "Write"):
            file_path = tool.tool_input.get("file_path", "")
            if file_path:
                filename = Path(file_path).name
                if filename not in self.files_modified:
                    self.files_modified.append(filename)

    def get_guidance_file(self) -> Path:
        """Get path to this agent's guidance file."""
        return self.config.get_guidance_dir() / f"{self.id}.md"

    def read_guidance(self) -> str | None:
        """Read injected guidance for this agent."""
        guidance_file = self.get_guidance_file()
        if guidance_file.exists():
            content = guidance_file.read_text().strip()
            return content if content else None
        return None

    def clear_guidance(self) -> None:
        """Clear the guidance file after reading."""
        guidance_file = self.get_guidance_file()
        if guidance_file.exists():
            guidance_file.unlink()

    def inject_guidance(self, content: str) -> None:
        """Write guidance to be picked up by the agent."""
        guidance_dir = self.config.get_guidance_dir()
        guidance_dir.mkdir(parents=True, exist_ok=True)
        self.get_guidance_file().write_text(content)

    async def start(self, prompt: str) -> None:
        """Start the agent with the given prompt."""
        if self.status == AgentStatus.RUNNING:
            raise RuntimeError(f"Agent {self.id} is already running")

        self._set_status(AgentStatus.STARTING)
        self._should_stop = False
        self._paused = False
        self._pause_event.set()
        self.started_at = datetime.now()
        self.finished_at = None
        self.error = None
        self.tools_used = []
        self.files_modified = []

        # Get agent-specific timeout
        agent_config = getattr(self.config.agents, self.type.value)
        timeout_minutes = agent_config.timeout_minutes

        try:
            cmd = [
                "claude",
                "--dangerously-skip-permissions",
                "--verbose",
                "--output-format",
                "stream-json",
                "-p",
                prompt,
            ]

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.config.project_root,
            )

            self._set_status(AgentStatus.RUNNING)

            # Stream output
            await self._stream_output(timeout_minutes * 60)

        except Exception as e:
            self.error = str(e)
            self._set_status(AgentStatus.FAILED)
            self._add_output(OutputLine(
                timestamp=datetime.now(),
                content=f"Agent failed: {e}",
                line_type="error",
            ))

        finally:
            self.finished_at = datetime.now()
            if self.status == AgentStatus.RUNNING:
                self._set_status(AgentStatus.STOPPED)

    async def _stream_output(self, timeout_seconds: float) -> None:
        """Stream output from the subprocess."""
        if not self.process or not self.process.stdout:
            return

        start_time = time.time()

        while True:
            # Check for stop request
            if self._should_stop:
                self.process.terminate()
                break

            # Check for pause
            if self._paused:
                self._set_status(AgentStatus.PAUSED)
                await self._pause_event.wait()
                if self.status == AgentStatus.PAUSED:
                    self._set_status(AgentStatus.RUNNING)

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                self.process.kill()
                self.error = f"Timed out after {timeout_seconds/60:.0f} minutes"
                self._set_status(AgentStatus.FAILED)
                break

            # Check if process finished
            retcode = self.process.poll()
            if retcode is not None:
                # Read remaining output
                remaining = self.process.stdout.read()
                if remaining:
                    await self._process_output(remaining)
                break

            # Read available output (non-blocking via asyncio)
            try:
                line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, self.process.stdout.readline
                    ),
                    timeout=0.5,
                )
                if line:
                    await self._process_output(line)
            except asyncio.TimeoutError:
                continue

    async def _process_output(self, output: str) -> None:
        """Process raw output and emit structured events."""
        for line in output.strip().split("\n"):
            if not line:
                continue

            try:
                event = json.loads(line)
                await self._handle_event(event)
            except json.JSONDecodeError:
                # Not JSON, emit as raw text
                self._add_output(OutputLine(
                    timestamp=datetime.now(),
                    content=line,
                    line_type="text",
                ))

    async def _handle_event(self, event: dict[str, Any]) -> None:
        """Handle a parsed JSON event from Claude."""
        event_type = event.get("type", "")

        if event_type == "assistant":
            message = event.get("message", {})
            for content in message.get("content", []):
                content_type = content.get("type", "")

                if content_type == "thinking":
                    thinking = content.get("thinking", "")
                    if thinking:
                        self._add_output(OutputLine(
                            timestamp=datetime.now(),
                            content=thinking,
                            line_type="thinking",
                        ))

                elif content_type == "text":
                    text = content.get("text", "")
                    if text:
                        self._add_output(OutputLine(
                            timestamp=datetime.now(),
                            content=text,
                            line_type="text",
                        ))

                elif content_type == "tool_use":
                    tool_name = content.get("name", "unknown")
                    tool_input = content.get("input", {})

                    self._add_tool_use(ToolUse(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        timestamp=datetime.now(),
                    ))

                    # Also add to output stream
                    self._add_output(OutputLine(
                        timestamp=datetime.now(),
                        content=f"Using tool: {tool_name}",
                        line_type="tool_use",
                        metadata={"tool": tool_name, "input": tool_input},
                    ))

        elif event_type == "content_block_delta":
            delta = event.get("delta", {})
            delta_type = delta.get("type", "")

            if delta_type == "thinking_delta":
                thinking = delta.get("thinking", "")
                if thinking:
                    self._add_output(OutputLine(
                        timestamp=datetime.now(),
                        content=thinking,
                        line_type="thinking_delta",
                    ))

            elif delta_type == "text_delta":
                text = delta.get("text", "")
                if text:
                    self._add_output(OutputLine(
                        timestamp=datetime.now(),
                        content=text,
                        line_type="text_delta",
                    ))

        elif event_type == "result":
            result = event.get("result", "")
            if result:
                self._add_output(OutputLine(
                    timestamp=datetime.now(),
                    content=result,
                    line_type="result",
                ))

    def pause(self) -> None:
        """Pause the agent."""
        self._paused = True
        self._pause_event.clear()

    def resume(self) -> None:
        """Resume the agent."""
        self._paused = False
        self._pause_event.set()

    async def stop(self) -> None:
        """Stop the agent gracefully."""
        self._should_stop = True
        self._set_status(AgentStatus.STOPPING)

        if self._paused:
            self.resume()  # Unpause so it can stop

        # Wait for process to finish
        if self.process:
            try:
                self.process.terminate()
                await asyncio.sleep(2)
                if self.process.poll() is None:
                    self.process.kill()
            except Exception:
                pass

        self._set_status(AgentStatus.STOPPED)

    async def kill(self) -> None:
        """Kill the agent immediately."""
        self._should_stop = True

        if self.process:
            try:
                self.process.kill()
            except Exception:
                pass

        self._set_status(AgentStatus.STOPPED)

    def get_output(self, limit: int | None = None, offset: int = 0) -> list[OutputLine]:
        """Get output buffer contents."""
        output = list(self.output_buffer)
        if offset:
            output = output[offset:]
        if limit:
            output = output[:limit]
        return output

    def to_dict(self) -> dict[str, Any]:
        """Convert agent state to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "status": self.status.value,
            "currentTask": self.current_task,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "finishedAt": self.finished_at.isoformat() if self.finished_at else None,
            "filesModified": self.files_modified,
            "toolsUsed": len(self.tools_used),
            "outputLines": len(self.output_buffer),
            "error": self.error,
        }

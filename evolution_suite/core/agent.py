"""Agent class - wraps Claude subprocess with streaming output."""

from __future__ import annotations

import asyncio
import json
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
class UsageMetrics:
    """Token usage and cost metrics."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cost_usd: float = 0.0
    requests: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "cacheReadTokens": self.cache_read_tokens,
            "cacheCreationTokens": self.cache_creation_tokens,
            "costUsd": self.cost_usd,
            "requests": self.requests,
        }

    def add(self, other: "UsageMetrics") -> None:
        """Add another UsageMetrics to this one."""
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_tokens += other.cache_read_tokens
        self.cache_creation_tokens += other.cache_creation_tokens
        self.cost_usd += other.cost_usd
        self.requests += other.requests


# Pricing per million tokens (as of 2025)
MODEL_PRICING = {
    "claude-opus-4-5-20251101": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-3-5-20241022": {"input": 0.80, "output": 4.0},
    # Fallback for unknown models
    "default": {"input": 3.0, "output": 15.0},
}


def calculate_cost(input_tokens: int, output_tokens: int, model: str = "default") -> float:
    """Calculate cost in USD for given token counts."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


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
        on_usage: Callable[["UsageMetrics"], None] | None = None,
    ):
        self.id = agent_id or f"{agent_type.value}-{uuid.uuid4().hex[:8]}"
        self.type = agent_type
        self.config = config
        self.status = AgentStatus.IDLE
        self.process: asyncio.subprocess.Process | None = None
        self.output_buffer: deque[OutputLine] = deque(maxlen=10000)
        self.tools_used: list[ToolUse] = []
        self.files_modified: list[str] = []
        self.current_task: str | None = None
        self.goal: str | None = None  # The overarching objective for this agent
        self.started_at: datetime | None = None
        self.finished_at: datetime | None = None
        self.error: str | None = None

        # Usage tracking
        self.usage_metrics = UsageMetrics()
        self.model: str = "default"

        # Relationship tracking
        self.assigned_by: str | None = None  # ID of agent that delegated to this one
        self.delegated_to: list[str] = []  # IDs of agents this one assigned work to
        self.waiting_for: str | None = None  # ID of agent blocking this one

        # Callbacks
        self._on_output = on_output
        self._on_tool_use = on_tool_use
        self._on_status_change = on_status_change
        self._on_usage = on_usage

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

    def _update_usage(self, usage_data: dict[str, Any]) -> None:
        """Update usage metrics from Claude API response."""
        input_tokens = usage_data.get("input_tokens", 0)
        output_tokens = usage_data.get("output_tokens", 0)
        cache_read = usage_data.get("cache_read_input_tokens", 0)
        cache_creation = usage_data.get("cache_creation_input_tokens", 0)

        # Calculate cost
        cost = calculate_cost(input_tokens, output_tokens, self.model)

        # Create metrics for this request
        request_metrics = UsageMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
            cost_usd=cost,
            requests=1,
        )

        # Add to cumulative metrics
        self.usage_metrics.add(request_metrics)

        # Notify callback
        if self._on_usage:
            self._on_usage(request_metrics)

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
        """Store guidance for the agent's next continuation.

        With -p mode, we can't inject into a running process.
        The guidance is stored and will be included when the agent is continued.
        """
        guidance_dir = self.config.get_guidance_dir()
        guidance_dir.mkdir(parents=True, exist_ok=True)

        # Append to existing guidance if any
        guidance_file = self.get_guidance_file()
        existing = guidance_file.read_text() if guidance_file.exists() else ""
        if existing:
            content = existing + "\n\n---\n\n" + content
        guidance_file.write_text(content)

        self._add_output(OutputLine(
            timestamp=datetime.now(),
            content=f"[Guidance queued for next continuation: {content[:100]}...]",
            line_type="text",
            metadata={"queued_guidance": True},
        ))

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

        # Include any pending guidance in the prompt
        pending_guidance = self.read_guidance()
        if pending_guidance:
            prompt = prompt + "\n\n## Additional Context/Guidance\n\n" + pending_guidance
            self.clear_guidance()

        # Set goal from prompt (first line or truncated)
        first_line = prompt.strip().split('\n')[0]
        goal_value = first_line[:200] if len(first_line) > 200 else first_line
        self.goal = goal_value
        self.current_task = goal_value

        # Get agent-specific timeout
        agent_config = getattr(self.config.agents, self.type.value)
        timeout_minutes = agent_config.timeout_minutes

        try:
            # Build command arguments
            cmd_args = [
                "claude",
                "--dangerously-skip-permissions",
                "--verbose",
                "--output-format", "stream-json",
                "--permission-mode", "bypassPermissions",  # Run fully autonomously
                "-p",  # Print mode for non-interactive output
            ]

            # For coordinators, disable the Task tool so they use HTTP API instead
            if self.type == AgentType.COORDINATOR:
                # Disable Task tool - coordinator should use curl to spawn real agents via HTTP API
                cmd_args.extend([
                    "--tools", "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch",
                ])

            # Add prompt as argument
            cmd_args.append(prompt)

            # Use asyncio subprocess for proper async handling
            self.process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
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
        """Stream output from the subprocess using chunk-based reading."""
        if not self.process or not self.process.stdout:
            return

        start_time = time.time()
        buffer = b""

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

            # Read chunks and process complete lines
            try:
                chunk = await asyncio.wait_for(
                    self.process.stdout.read(65536),  # Read up to 64KB at a time
                    timeout=0.5,
                )
                if chunk:
                    buffer += chunk
                    # Process complete lines
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        await self._process_output(line.decode("utf-8", errors="replace"))
                elif self.process.returncode is not None:
                    # Process finished - handle remaining buffer
                    if buffer:
                        await self._process_output(buffer.decode("utf-8", errors="replace"))
                    break
            except asyncio.TimeoutError:
                # Check if process is still running
                if self.process.returncode is not None:
                    # Process remaining buffer
                    if buffer:
                        await self._process_output(buffer.decode("utf-8", errors="replace"))
                    break
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

        # Capture model from system init event
        if event_type == "system" and event.get("subtype") == "init":
            model = event.get("model", "")
            if model:
                self.model = model
            return

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

            # Capture usage metrics from result
            usage = event.get("usage", {})
            if usage:
                self._update_usage(usage)

            # Capture model info
            model = event.get("model", "")
            if model:
                self.model = model

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
                # Wait up to 2 seconds for graceful termination
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await self.process.wait()
            except Exception:
                pass

        self._set_status(AgentStatus.STOPPED)

    async def kill(self) -> None:
        """Kill the agent immediately."""
        self._should_stop = True

        if self.process:
            try:
                self.process.kill()
                await self.process.wait()
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
        result = {
            "id": self.id,
            "type": self.type.value,
            "status": self.status.value,
            "currentTask": self.current_task,
            "goal": self.goal,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "finishedAt": self.finished_at.isoformat() if self.finished_at else None,
            "filesModified": self.files_modified,
            "toolsUsed": len(self.tools_used),
            "outputLines": len(self.output_buffer),
            "error": self.error,
            # Usage metrics
            "usage": self.usage_metrics.to_dict(),
            "model": self.model,
            # Relationship tracking
            "assignedBy": self.assigned_by,
            "delegatedTo": self.delegated_to,
            "waitingFor": self.waiting_for,
        }
        return result

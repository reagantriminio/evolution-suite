"""File-based communication channel for agents."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class GuidanceMessage(BaseModel):
    """A guidance message for an agent."""

    content: str
    timestamp: datetime
    source: str = "user"  # user, system, or another agent
    priority: int = 0  # Higher = more important


class FileChannel:
    """File-based communication channel for agents.

    Provides a simple, debuggable way for the backend to communicate
    with running agent subprocesses via the filesystem.
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.guidance_dir = base_dir / ".guidance"
        self.state_dir = base_dir / ".agent-state"

        # Ensure directories exist
        self.guidance_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def write_guidance(self, agent_id: str, content: str, source: str = "user") -> None:
        """Write guidance for a specific agent."""
        guidance_file = self.guidance_dir / f"{agent_id}.md"

        # Create structured guidance with metadata
        header = f"""<!--
  Injected: {datetime.now().isoformat()}
  Source: {source}
-->

"""
        guidance_file.write_text(header + content)

    def read_guidance(self, agent_id: str) -> str | None:
        """Read guidance for a specific agent."""
        guidance_file = self.guidance_dir / f"{agent_id}.md"
        if guidance_file.exists():
            content = guidance_file.read_text()
            # Strip metadata comments
            lines = content.split("\n")
            content_lines = []
            in_comment = False
            for line in lines:
                if line.strip().startswith("<!--"):
                    in_comment = True
                elif "-->" in line:
                    in_comment = False
                    continue
                elif not in_comment:
                    content_lines.append(line)
            return "\n".join(content_lines).strip() or None
        return None

    def clear_guidance(self, agent_id: str) -> None:
        """Clear guidance for a specific agent."""
        guidance_file = self.guidance_dir / f"{agent_id}.md"
        if guidance_file.exists():
            guidance_file.unlink()

    def has_guidance(self, agent_id: str) -> bool:
        """Check if an agent has pending guidance."""
        guidance_file = self.guidance_dir / f"{agent_id}.md"
        return guidance_file.exists() and guidance_file.stat().st_size > 0

    def list_guidance(self) -> dict[str, str]:
        """List all pending guidance."""
        result = {}
        for f in self.guidance_dir.glob("*.md"):
            agent_id = f.stem
            content = self.read_guidance(agent_id)
            if content:
                result[agent_id] = content
        return result

    def save_agent_state(self, agent_id: str, state: dict[str, Any]) -> None:
        """Save agent state for recovery."""
        state_file = self.state_dir / f"{agent_id}.json"
        state["_saved_at"] = datetime.now().isoformat()
        state_file.write_text(json.dumps(state, indent=2, default=str))

    def load_agent_state(self, agent_id: str) -> dict[str, Any] | None:
        """Load agent state."""
        state_file = self.state_dir / f"{agent_id}.json"
        if state_file.exists():
            return json.loads(state_file.read_text())
        return None

    def clear_agent_state(self, agent_id: str) -> None:
        """Clear agent state."""
        state_file = self.state_dir / f"{agent_id}.json"
        if state_file.exists():
            state_file.unlink()

    def broadcast_guidance(self, agent_type: str, content: str, source: str = "user") -> None:
        """Write guidance to all agents of a given type."""
        # Find all agents of this type by checking state files
        for state_file in self.state_dir.glob("*.json"):
            try:
                state = json.loads(state_file.read_text())
                if state.get("type") == agent_type:
                    agent_id = state_file.stem
                    self.write_guidance(agent_id, content, source)
            except Exception:
                continue

    def cleanup(self) -> None:
        """Clean up all guidance and state files."""
        for f in self.guidance_dir.glob("*"):
            f.unlink()
        for f in self.state_dir.glob("*"):
            f.unlink()

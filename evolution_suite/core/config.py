"""Configuration loading and validation for evolution suite."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    """Project-level configuration."""

    name: str
    description: str = ""
    branch: str = "main"


class PromptsConfig(BaseModel):
    """Prompt template paths."""

    coordinator: str | None = None
    worker: str | None = None
    evaluator: str | None = None


class StateConfig(BaseModel):
    """State directory configuration."""

    directory: str = "./evolution"


class AgentTypeConfig(BaseModel):
    """Configuration for a specific agent type."""

    timeout_minutes: int = 30
    model: str | None = None


class AgentsConfig(BaseModel):
    """Agent pool configuration."""

    coordinator: AgentTypeConfig = Field(default_factory=AgentTypeConfig)
    worker: AgentTypeConfig = Field(default_factory=AgentTypeConfig)
    evaluator: AgentTypeConfig = Field(default_factory=AgentTypeConfig)


class ServerConfig(BaseModel):
    """Server configuration."""

    port: int = 8420
    host: str = "127.0.0.1"


class ProtectionConfig(BaseModel):
    """Data protection configuration."""

    forbidden_files: list[str] = Field(default_factory=list)
    dangerous_patterns: list[str] = Field(default_factory=list)


class Config(BaseModel):
    """Complete evolution suite configuration."""

    project: ProjectConfig
    prompts: PromptsConfig = Field(default_factory=PromptsConfig)
    state: StateConfig = Field(default_factory=StateConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    protection: ProtectionConfig = Field(default_factory=ProtectionConfig)

    # Runtime fields (not from config file)
    project_root: Path = Field(default=Path.cwd(), exclude=True)
    config_path: Path | None = Field(default=None, exclude=True)

    def get_state_dir(self) -> Path:
        """Get absolute path to state directory."""
        state_path = Path(self.state.directory)
        if state_path.is_absolute():
            return state_path
        return self.project_root / state_path

    def get_guidance_dir(self) -> Path:
        """Get path to guidance files directory."""
        return self.get_state_dir() / ".guidance"

    def get_agent_state_dir(self) -> Path:
        """Get path to agent state directory."""
        return self.get_state_dir() / ".agent-state"

    def get_cycle_logs_dir(self) -> Path:
        """Get path to cycle logs directory."""
        return self.get_state_dir() / "cycle_logs"

    def get_prompt_path(self, prompt_type: str) -> Path | None:
        """Get path to a prompt template, or None to use default."""
        prompt_config = getattr(self.prompts, prompt_type, None)
        if prompt_config is None:
            return None
        prompt_path = Path(prompt_config)
        if prompt_path.is_absolute():
            return prompt_path
        return self.project_root / prompt_path

    def get_state_file(self) -> Path:
        """Get path to evolution state file."""
        return self.get_state_dir() / "EVOLUTION_STATE.md"

    def get_log_file(self) -> Path:
        """Get path to evolution log file."""
        return self.get_state_dir() / "EVOLUTION_LOG.md"


def load_config(config_path: Path) -> Config:
    """Load configuration from YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    config = Config(**data)
    config.project_root = config_path.parent
    config.config_path = config_path

    return config


def get_default_config(project_name: str = "my-project") -> Config:
    """Get a default configuration."""
    return Config(
        project=ProjectConfig(name=project_name),
    )

# Evolution Suite

RTS-style command center for autonomous AI agent pools that evolve codebases.

## Features

- **Agent Pool Management** - Spawn, pause, resume, and kill multiple coordinator, worker, and evaluator agents
- **Real-time Visibility** - Live streaming of agent thinking and actions via WebSocket
- **Guidance Injection** - Inject context into running agents to guide their behavior
- **Live Prompt Editing** - View and modify prompt templates on the fly
- **Cycle History** - Track evolution cycles with success/failure indicators and logs

## Installation

### From GitHub (recommended)

```bash
# Install latest from main branch
pip install git+https://github.com/reagantriminio/evolution-suite.git

# Install a specific version/tag
pip install git+https://github.com/reagantriminio/evolution-suite.git@v0.1.0

# Install with browser automation support
pip install "evolution-suite[browser] @ git+https://github.com/reagantriminio/evolution-suite.git"
```

### Add to your project's dependencies

**pyproject.toml:**
```toml
[project]
dependencies = [
    "evolution-suite @ git+https://github.com/reagantriminio/evolution-suite.git",
]

# Or with extras
[project.optional-dependencies]
agents = [
    "evolution-suite[browser] @ git+https://github.com/reagantriminio/evolution-suite.git",
]
```

**requirements.txt:**
```
evolution-suite @ git+https://github.com/reagantriminio/evolution-suite.git
```

### From PyPI (when published)

```bash
pip install evolution-suite

# With browser automation
pip install evolution-suite[browser]
```

## Quick Start

```bash
# Initialize in your project
cd your-project
evolution init

# Start the dashboard
evolution start
```

This opens a browser with the command center dashboard.

## CLI Commands

```bash
evolution init        # Initialize evolution-suite in a project
evolution start       # Start the dashboard + orchestrator
evolution run         # Run headless (no UI)
evolution status      # Show current status
evolution agents      # List running agents
```

## Configuration

Create `evolution.yaml` in your project root:

```yaml
project:
  name: "my-project"
  description: "Project description"
  branch: "experimental"

state:
  directory: "./evolution"

agents:
  coordinator:
    timeout_minutes: 15
  worker:
    timeout_minutes: 45
  evaluator:
    timeout_minutes: 30

server:
  port: 8420
  host: "127.0.0.1"
```

## Development

### Backend

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (proxies to backend)
npm run dev

# Build for production
npm run build
```

## Programmatic Usage

You can import and use evolution-suite components in your own code:

```python
from evolution_suite.core import (
    Agent, AgentStatus, AgentType,
    AgentManager,
    Config, load_config,
    Orchestrator,
)
from evolution_suite.comms import FileChannel, WebSocketManager
from evolution_suite.api import create_router

# Load config from evolution.yaml
config = load_config()

# Create an agent manager
manager = AgentManager(config)

# Spawn agents programmatically
coordinator = await manager.spawn_agent(AgentType.COORDINATOR)
worker = await manager.spawn_agent(AgentType.WORKER)
```

## Architecture

```
evolution-suite/
├── evolution_suite/       # Python package
│   ├── cli.py            # CLI commands
│   ├── server.py         # FastAPI server
│   ├── core/             # Agent management, orchestrator
│   ├── comms/            # WebSocket, file channel
│   └── api/              # REST endpoints
├── frontend/             # React dashboard
└── templates/            # Default prompt templates
```

## License

MIT

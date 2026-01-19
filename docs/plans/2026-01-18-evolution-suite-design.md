# Evolution Suite - Design Document

**Date**: 2026-01-18
**Status**: Approved

## Overview

Evolution Suite is a standalone package for managing autonomous AI agent pools that evolve codebases. It provides an RTS-style command center UI for real-time monitoring, guidance injection, and control of coordinator, worker, and evaluator agents.

## Goals

1. **Agent Pool Management** - Spawn, pause, resume, kill multiple agents of each type
2. **Real-time Visibility** - Live streaming of agent thinking and actions
3. **Guidance Injection** - Inject context into running agents to guide their behavior
4. **Live Prompt Editing** - View and modify prompt templates on the fly
5. **Cycle History** - Track evolution cycles with success/failure, logs, and retry capability
6. **Portable Package** - Install via pip, works with any Python project

## Architecture

### Package Structure

```
evolution-suite/
├── pyproject.toml
├── evolution_suite/
│   ├── __init__.py
│   ├── cli.py                  # CLI: `evolution` command
│   ├── server.py               # FastAPI server
│   ├── core/
│   │   ├── agent.py            # Agent class (wraps Claude subprocess)
│   │   ├── agent_manager.py    # Pool management
│   │   ├── orchestrator.py     # Cycle coordination
│   │   └── config.py           # Configuration loading
│   ├── comms/
│   │   ├── file_channel.py     # File-based agent communication
│   │   └── websocket.py        # WebSocket manager
│   ├── api/
│   │   ├── routes.py           # API endpoints
│   │   └── schemas.py          # Pydantic models
│   └── static/                 # Built React frontend
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── index.css
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── AgentPool.tsx
│       │   ├── AgentCard.tsx
│       │   ├── OutputPanel.tsx
│       │   ├── GuidancePanel.tsx
│       │   ├── PromptEditor.tsx
│       │   ├── CycleHistory.tsx
│       │   └── StatusBar.tsx
│       ├── hooks/
│       │   ├── useWebSocket.ts
│       │   └── useAgents.ts
│       ├── stores/
│       │   └── agentStore.ts
│       └── lib/
│           ├── api.ts
│           └── types.ts
├── templates/
│   └── prompts/
│       ├── coordinator.md
│       ├── worker.md
│       └── evaluator.md
└── tests/
```

### Communication Model

```
                    WebSocket (real-time)
Frontend <─────────────────────────────────> FastAPI Server
                                                   │
                                                   │ manages
                                                   ▼
                                            AgentManager
                                                   │
                              ┌────────────────────┼────────────────────┐
                              ▼                    ▼                    ▼
                         Agent-1              Agent-2              Agent-3
                      (subprocess)         (subprocess)         (subprocess)
                              │                    │                    │
                              └────────────────────┴────────────────────┘
                                                   │
                                            File Channel
                                         (.guidance/*.md)
```

- **WebSocket**: Real-time UI updates, immediate response to user actions
- **File Channel**: Agents poll guidance files, robust and debuggable

### API Endpoints

```
GET  /api/status              # System status
GET  /api/agents              # List all agents
GET  /api/agents/{id}         # Agent details
GET  /api/agents/{id}/output  # Agent output buffer
POST /api/agents              # Spawn new agent
POST /api/agents/{id}/inject  # Inject guidance
POST /api/agents/{id}/pause   # Pause agent
POST /api/agents/{id}/resume  # Resume agent
DELETE /api/agents/{id}       # Kill agent

GET  /api/cycles              # List cycles
GET  /api/cycles/{n}          # Cycle details

GET  /api/prompts             # List prompts
GET  /api/prompts/{name}      # Get prompt content
PUT  /api/prompts/{name}      # Update prompt

POST /api/orchestrator/start  # Start evolution
POST /api/orchestrator/stop   # Stop after current cycle
```

### WebSocket Events

```typescript
// Server → Client
{ type: "agent_spawned", agent: Agent }
{ type: "agent_output", agentId: string, line: OutputLine }
{ type: "agent_tool_use", agentId: string, tool: string, input: object }
{ type: "agent_status", agentId: string, status: AgentStatus }
{ type: "cycle_started", cycle: number }
{ type: "cycle_completed", cycle: number, result: CycleResult }
{ type: "guidance_injected", agentId: string }
{ type: "prompt_updated", name: string }

// Client → Server
{ type: "inject_guidance", agentId: string, content: string }
{ type: "update_prompt", name: string, content: string }
```

## Configuration

Projects create `evolution.yaml`:

```yaml
project:
  name: "my-project"
  description: "Project description for agent context"
  branch: "experimental"

prompts:
  coordinator: "./evolution/prompts/coordinator.md"
  worker: "./evolution/prompts/worker.md"
  evaluator: "./evolution/prompts/evaluator.md"

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

protection:
  forbidden_files:
    - ".env"
  dangerous_patterns:
    - "DROP DATABASE"
```

## Visual Design

### Color Palette

```
Background:     #09090b (zinc-950)
Surface:        #18181b (zinc-900)
Surface Hover:  #27272a (zinc-800)
Border:         #3f3f46 (zinc-700)

Primary:        #fafafa (white)
Secondary:      #a1a1aa (zinc-400)
Muted:          #52525b (zinc-600)

Status Active:  #22c55e (green-500)
Status Paused:  #eab308 (yellow-500)
Status Failed:  #ef4444 (red-500)
```

### Typography

- UI Font: Inter
- Code Font: JetBrains Mono
- Base size: 14px

### Animation Principles

- Subtle, purposeful animations (100-200ms)
- No flashy effects or neon colors
- Typewriter effect for thinking streams
- Smooth transitions between states
- Staggered reveals for lists

## CLI Usage

```bash
# Install
pip install evolution-suite

# Initialize project
evolution init

# Start dashboard + orchestrator
evolution start

# Run headless
evolution run --max-cycles 10

# View status
evolution status
```

## Implementation Phases

1. **Phase 1**: Core Python package (agent management, file channel, basic orchestrator)
2. **Phase 2**: FastAPI server with WebSocket support
3. **Phase 3**: React frontend with full UI
4. **Phase 4**: Integration, bundling, polish

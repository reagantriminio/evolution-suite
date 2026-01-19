# Agent Network Graph & Usage Dashboard Design

## Overview

This document describes the design for two major frontend features:
1. **Agent Network Graph** - A real-time visualization showing agents as nodes in fixed lanes, with state files visible and relationships (delegation, blocking, data flow) shown as edges
2. **Usage Dashboard** - A live-updating page showing token usage, costs, and metrics with daily/weekly breakdowns

## Agent Network Graph

### Layout: Fixed Lanes

```
COORDINATORS    │    STATE FILES    │    WORKERS    │    EVALUATORS
                │                   │               │
   ┌───┐        │    ┌─────────┐    │    ┌───┐      │    ┌───┐
   │ C1│───────────▶│  STATE  │◀────────│ W1│─────────▶│ E1│
   └───┘        │    │  .md    │    │    └───┘      │    └───┘
                │    └─────────┘    │               │
   ┌───┐        │    ┌─────────┐    │    ┌───┐      │    ┌───┐
   │ C2│───────────▶│  LOCK   │◀────────│ W2│─────────▶│ E2│
   └───┘        │    └─────────┘    │    └───┘      │    └───┘
```

### Node Types

#### Agent Nodes
- Status indicator (color-coded: green=running, red=failed, yellow=starting/paused, gray=idle/stopped)
- Agent type icon and ID
- Current task (truncated)
- Mini stats: runtime, tools used
- Quick action buttons on hover

#### State File Nodes
- File icon with name (EVOLUTION_STATE.md, LOCK.json, etc.)
- Last modified timestamp
- Current lock holder (if applicable)
- Click to view/edit contents

### Edge Types

| Color | Animation | Meaning |
|-------|-----------|---------|
| Green | Flowing dots | Active data/task flowing |
| Orange | Pulsing | Blocked/waiting |
| Blue | Solid | Delegation relationship |
| Gray | Dashed | Historical/completed |
| Red | Thick pulse | Error/needs attention |

### Interactions

#### Node Click
- Opens slide-out panel with full details
- Shows output stream, prompt editor, controls

#### Edge Click
- Shows delegated task details
- Data being passed between agents

#### Multi-select
- Shift+click or drag to select multiple
- Bulk action toolbar appears
- Actions: Edit Prompts, Inject Guidance, Pause All, Kill All

### Slide-out Panel (400-500px, right side)

```
┌─────────────────────────────┐
│  AGENT: worker-a1b2    [×]  │
│  ─────────────────────────  │
│  Status: ● running          │
│  Runtime: 2m 34s            │
│  Tools: 5 | Files: 3        │
│                             │
│  ┌─ PROMPT ───────────────┐ │
│  │ [Template: worker_v1 ▾]│ │
│  │                        │ │
│  │ You are a worker...    │ │
│  │                        │ │
│  │ [Syntax highlighting]  │ │
│  └────────────────────────┘ │
│  [Save] [Reset] [Detach]    │
│                             │
│  ┌─ OUTPUT ───────────────┐ │
│  │ > Analyzing codebase   │ │
│  │ > Found 3 files...     │ │
│  │ [Auto-scroll ✓]        │ │
│  └────────────────────────┘ │
│                             │
│  ┌─ ACTIONS ──────────────┐ │
│  │ [Inject Guidance]      │ │
│  │ [Pause] [Kill]         │ │
│  └────────────────────────┘ │
└─────────────────────────────┘
```

### Prompt Templates

- Templates stored in backend, editable via UI
- Agents can inherit from template or use custom prompt
- Edit template → all linked agents update
- Templates: coordinator_default, worker_default, evaluator_default

## Usage Dashboard

### Summary Cards (Top Row)

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   $12.47    │  │   847.2K    │  │    23       │  │   94.2%     │
│  Today's    │  │   Tokens    │  │   Cycles    │  │  Success    │
│    Cost     │  │   Today     │  │   Today     │  │    Rate     │
│  ↑ 15%      │  │  ↓ 8%       │  │  ↑ 4        │  │  ↑ 2.1%     │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

### Daily Usage Chart

- Bar chart showing daily token usage
- Stacked: input tokens, output tokens, cache hits
- Selectable range: 7d, 30d, 90d
- Hover for detailed breakdown

### Breakdown Charts

- By Agent Type: Pie/bar showing Coordinator vs Worker vs Evaluator usage
- By Model: Distribution across claude-opus, claude-sonnet, etc.

### Weekly Table

| Week | Tokens | Cost | Cycles | Agents | Success |
|------|--------|------|--------|--------|---------|
| Jan 13-19 | 5.2M | $84.21 | 156 | 12 | 91.0% |

### Live Activity Feed

Real-time stream of usage events:
```
12:34:21  worker-a1b2   +2,847 tokens   Edit tool   $0.04
12:34:18  worker-a1b2   +1,203 tokens   Read tool   $0.02
```

### Budget & Alerts

- Set daily/weekly budgets
- Progress bars showing current spend vs budget
- Alerts at 75%, 90%, 100% thresholds
- Optional auto-pause when exceeded

## Data Model Changes

### Backend: New Usage Tracking

```python
@dataclass
class UsageMetrics:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cost_usd: float = 0.0
    requests: int = 0

@dataclass
class AgentRelationship:
    source_id: str
    target_id: str
    relationship_type: str  # 'delegation', 'waiting', 'data_flow'
    task_description: str | None = None
    created_at: datetime
```

### Frontend: New Types

```typescript
interface UsageMetrics {
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens: number;
  cacheCreationTokens: number;
  costUsd: number;
  requests: number;
}

interface AgentRelationship {
  sourceId: string;
  targetId: string;
  type: 'delegation' | 'waiting' | 'data_flow' | 'completed';
  taskDescription?: string;
  createdAt: string;
}

interface StateFile {
  name: string;
  path: string;
  content: string;
  lastModified: string;
  lockedBy?: string;
}

interface DailyUsage {
  date: string;
  inputTokens: number;
  outputTokens: number;
  cacheTokens: number;
  costUsd: number;
  cycles: number;
  successRate: number;
  byAgentType: Record<AgentType, UsageMetrics>;
  byModel: Record<string, UsageMetrics>;
}
```

### WebSocket Events

```typescript
// New events
type UsageEvent = {
  type: 'usage_update';
  agentId: string;
  metrics: UsageMetrics;
};

type RelationshipEvent = {
  type: 'relationship_changed';
  relationship: AgentRelationship;
};

type StateFileEvent = {
  type: 'state_file_changed';
  file: StateFile;
};
```

## Implementation Plan

1. Backend: Add usage tracking to Agent class
2. Backend: Add relationship tracking to AgentManager
3. Backend: Create state file watcher
4. Backend: Add new WebSocket events
5. Backend: Create usage aggregation endpoints
6. Frontend: Create AgentNetworkGraph component using React Flow
7. Frontend: Create StateFileNode and AgentNode components
8. Frontend: Create SlideOutPanel component
9. Frontend: Add multi-select and bulk actions
10. Frontend: Create UsageDashboard page
11. Frontend: Add usage store with real-time updates
12. Integration testing

## Technology Choices

- **Graph Rendering**: React Flow (reactflow.dev) - mature, performant, good DX
- **Charts**: Recharts or Victory - lightweight, React-native
- **State Management**: Zustand (already in use)
- **Animations**: Framer Motion (already in use)

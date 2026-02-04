// Agent types
export type AgentType = 'coordinator' | 'worker' | 'evaluator';
export type AgentStatus = 'idle' | 'starting' | 'running' | 'paused' | 'stopping' | 'stopped' | 'failed';

export interface UsageMetrics {
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens: number;
  cacheCreationTokens: number;
  costUsd: number;
  requests: number;
}

export interface Agent {
  id: string;
  type: AgentType;
  status: AgentStatus;
  currentTask: string | null;
  goal: string | null;  // The overarching objective for this agent
  startedAt: string | null;
  finishedAt: string | null;
  filesModified: string[];
  toolsUsed: number;
  outputLines: number;
  error: string | null;
  // New fields
  usage?: UsageMetrics;
  model?: string;
  assignedBy?: string | null;
  delegatedTo?: string[];
  waitingFor?: string | null;
}

export interface AgentRelationship {
  sourceId: string;
  targetId: string;
  type: 'delegation' | 'waiting' | 'data_flow' | 'completed';
  taskDescription?: string;
  createdAt: string;
}

export interface OutputLine {
  timestamp: string;
  content: string;
  type: 'thinking' | 'thinking_delta' | 'text' | 'text_delta' | 'tool_use' | 'tool_result' | 'error' | 'result';
  metadata: Record<string, unknown>;
}

// Cycle types
export type TaskType = 'EVOLVE' | 'CLEANUP' | 'BUGFIX' | 'DONE';

export interface Cycle {
  cycle: number;
  taskType: TaskType;
  description: string;
  success: boolean;
  filesModified: string[];
  toolsUsed: Record<string, number>;
  durationSeconds: number;
  commitHash: string | null;
  error: string | null;
}

// Prompt types
export interface Prompt {
  name: string;
  content: string;
  isCustom: boolean;
  lastModified: string | null;
}

// Status types
export type CyclePhase = 'IDLE' | 'COORDINATING' | 'WORKING' | 'EVALUATING' | 'COMPLETED' | 'FAILED';

export interface AgentPoolStatus {
  totalAgents: number;
  runningAgents: number;
  agents: {
    coordinator: Agent[];
    worker: Agent[];
    evaluator: Agent[];
  };
}

export interface Status {
  running: boolean;
  cycle: number;
  phase: CyclePhase;
  agentPool: AgentPoolStatus;
  recentCycles: Cycle[];
  connectionCount: number;
}

// WebSocket event types
export type WebSocketEventType =
  | 'connected'
  | 'agent_spawned'
  | 'agent_output'
  | 'agent_tool_use'
  | 'agent_status'
  | 'agent_killed'
  | 'cycle_started'
  | 'cycle_completed'
  | 'cycle_failed'
  | 'phase_changed'
  | 'guidance_injected'
  | 'prompt_updated'
  | 'orchestrator_started'
  | 'orchestrator_stopped'
  | 'usage_update'
  | 'relationship_changed'
  | 'state_file_changed'
  | 'error';

export interface WebSocketEvent {
  type: WebSocketEventType;
  timestamp: string;
  [key: string]: unknown;
}

// State file types
export interface StateFile {
  name: string;
  path: string;
  content: string;
  lastModified: string | null;
  lockedBy?: string | null;
}

// Usage types
export interface DailyUsage {
  date: string;
  metrics: UsageMetrics;
  byAgentType: Record<AgentType, UsageMetrics>;
  byModel: Record<string, UsageMetrics>;
  cycles: number;
  successRate: number;
}

export interface UsageHistory {
  today: DailyUsage;
  history: DailyUsage[];
  total: UsageMetrics;
}

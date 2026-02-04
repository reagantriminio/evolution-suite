import type { Agent, AgentRelationship, Cycle, OutputLine, Prompt, StateFile, Status, UsageHistory, DailyUsage } from './types';

const API_BASE = '/api';

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Status
export async function getStatus(): Promise<Status> {
  return request<Status>('/status');
}

// Agents
export async function listAgents(type?: string): Promise<Agent[]> {
  const params = type ? `?agent_type=${type}` : '';
  return request<Agent[]>(`/agents${params}`);
}

export async function getAgent(agentId: string): Promise<Agent> {
  return request<Agent>(`/agents/${agentId}`);
}

export async function getAgentOutput(
  agentId: string,
  limit = 100,
  offset = 0
): Promise<{ agentId: string; lines: OutputLine[]; totalLines: number }> {
  return request(`/agents/${agentId}/output?limit=${limit}&offset=${offset}`);
}

export async function spawnAgent(
  type: string,
  agentId?: string
): Promise<Agent> {
  return request<Agent>('/agents', {
    method: 'POST',
    body: JSON.stringify({ type, agentId }),
  });
}

export async function startAgent(
  agentId: string,
  prompt: string
): Promise<{ success: boolean; message: string }> {
  return request(`/agents/${agentId}/start`, {
    method: 'POST',
    body: JSON.stringify({ content: prompt }),
  });
}

export async function injectGuidance(
  agentId: string,
  content: string
): Promise<{ success: boolean; message: string }> {
  return request(`/agents/${agentId}/inject`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

export async function pauseAgent(
  agentId: string
): Promise<{ success: boolean; message: string }> {
  return request(`/agents/${agentId}/pause`, { method: 'POST' });
}

export async function resumeAgent(
  agentId: string
): Promise<{ success: boolean; message: string }> {
  return request(`/agents/${agentId}/resume`, { method: 'POST' });
}

export async function killAgent(
  agentId: string
): Promise<{ success: boolean; message: string }> {
  return request(`/agents/${agentId}`, { method: 'DELETE' });
}

// Cycles
export async function listCycles(
  limit = 20,
  offset = 0
): Promise<{ cycles: Cycle[]; total: number }> {
  return request(`/cycles?limit=${limit}&offset=${offset}`);
}

export async function getCycle(cycleNum: number): Promise<Cycle> {
  return request<Cycle>(`/cycles/${cycleNum}`);
}

// Prompts
export async function listPrompts(): Promise<{ prompts: Prompt[] }> {
  return request('/prompts');
}

export async function getPrompt(name: string): Promise<Prompt> {
  return request<Prompt>(`/prompts/${name}`);
}

export async function updatePrompt(
  name: string,
  content: string
): Promise<Prompt> {
  return request<Prompt>(`/prompts/${name}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  });
}

// Orchestrator
export async function startOrchestrator(
  maxCycles?: number,
  dryRun = false
): Promise<{ success: boolean; message: string }> {
  return request('/orchestrator/start', {
    method: 'POST',
    body: JSON.stringify({ maxCycles, dryRun }),
  });
}

export async function stopOrchestrator(): Promise<{ success: boolean; message: string }> {
  return request('/orchestrator/stop', { method: 'POST' });
}

export async function forceStopOrchestrator(): Promise<{ success: boolean; message: string }> {
  return request('/orchestrator/force-stop', { method: 'POST' });
}

// Usage
export async function getUsage(days = 7): Promise<UsageHistory> {
  return request<UsageHistory>(`/usage?days=${days}`);
}

export async function getTodayUsage(): Promise<DailyUsage> {
  return request<DailyUsage>('/usage/today');
}

// State Files
export async function listStateFiles(): Promise<{ files: StateFile[] }> {
  return request('/state-files');
}

export async function getStateFile(filePath: string): Promise<StateFile> {
  return request<StateFile>(`/state-files/${filePath}`);
}

export async function updateStateFile(
  filePath: string,
  content: string
): Promise<StateFile> {
  return request<StateFile>(`/state-files/${filePath}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  });
}

// Relationships
export async function listRelationships(
  activeOnly = true
): Promise<{ relationships: AgentRelationship[] }> {
  return request(`/relationships?active_only=${activeOnly}`);
}

// Bulk Operations
export async function bulkInjectGuidance(
  agentIds: string[],
  content: string
): Promise<{ success: boolean; message: string }> {
  return request('/agents/bulk/guidance', {
    method: 'POST',
    body: JSON.stringify({ agentIds, content }),
  });
}

export async function bulkAgentAction(
  agentIds: string[],
  action: 'pause' | 'resume' | 'kill'
): Promise<{ success: boolean; message: string }> {
  return request('/agents/bulk/action', {
    method: 'POST',
    body: JSON.stringify({ agentIds, action }),
  });
}

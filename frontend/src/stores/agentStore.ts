import { create } from 'zustand';
import type { Agent, Cycle, CyclePhase, OutputLine, Prompt, WebSocketEvent } from '@/lib/types';

interface AgentOutputBuffer {
  lines: OutputLine[];
  maxLines: number;
}

interface AgentStore {
  // Connection state
  connected: boolean;
  setConnected: (connected: boolean) => void;

  // Orchestrator state
  running: boolean;
  cycle: number;
  phase: CyclePhase;
  setOrchestratorState: (running: boolean, cycle: number, phase: CyclePhase) => void;

  // Agents
  agents: Record<string, Agent>;
  setAgent: (agent: Agent) => void;
  removeAgent: (agentId: string) => void;
  updateAgentStatus: (agentId: string, status: Agent['status']) => void;

  // Agent output buffers
  outputBuffers: Record<string, AgentOutputBuffer>;
  addOutputLine: (agentId: string, line: OutputLine) => void;
  clearOutput: (agentId: string) => void;

  // Selected agent for output view
  selectedAgentId: string | null;
  setSelectedAgentId: (agentId: string | null) => void;

  // Cycles
  cycles: Cycle[];
  addCycle: (cycle: Cycle) => void;
  setCycles: (cycles: Cycle[]) => void;

  // Prompts
  prompts: Record<string, Prompt>;
  setPrompt: (prompt: Prompt) => void;
  setPrompts: (prompts: Prompt[]) => void;

  // Handle WebSocket events
  handleEvent: (event: WebSocketEvent) => void;
}

const MAX_OUTPUT_LINES = 1000;

export const useAgentStore = create<AgentStore>((set, get) => ({
  // Connection state
  connected: false,
  setConnected: (connected) => set({ connected }),

  // Orchestrator state
  running: false,
  cycle: 0,
  phase: 'IDLE',
  setOrchestratorState: (running, cycle, phase) => set({ running, cycle, phase }),

  // Agents
  agents: {},
  setAgent: (agent) =>
    set((state) => ({
      agents: { ...state.agents, [agent.id]: agent },
    })),
  removeAgent: (agentId) =>
    set((state) => {
      const { [agentId]: _, ...rest } = state.agents;
      return { agents: rest };
    }),
  updateAgentStatus: (agentId, status) =>
    set((state) => {
      const agent = state.agents[agentId];
      if (!agent) return state;
      return {
        agents: { ...state.agents, [agentId]: { ...agent, status } },
      };
    }),

  // Agent output buffers
  outputBuffers: {},
  addOutputLine: (agentId, line) =>
    set((state) => {
      const buffer = state.outputBuffers[agentId] || { lines: [], maxLines: MAX_OUTPUT_LINES };
      const newLines = [...buffer.lines, line];
      // Trim if over max
      if (newLines.length > buffer.maxLines) {
        newLines.splice(0, newLines.length - buffer.maxLines);
      }
      return {
        outputBuffers: {
          ...state.outputBuffers,
          [agentId]: { ...buffer, lines: newLines },
        },
      };
    }),
  clearOutput: (agentId) =>
    set((state) => ({
      outputBuffers: {
        ...state.outputBuffers,
        [agentId]: { lines: [], maxLines: MAX_OUTPUT_LINES },
      },
    })),

  // Selected agent
  selectedAgentId: null,
  setSelectedAgentId: (agentId) => set({ selectedAgentId: agentId }),

  // Cycles
  cycles: [],
  addCycle: (cycle) =>
    set((state) => ({
      cycles: [cycle, ...state.cycles].slice(0, 50), // Keep last 50
    })),
  setCycles: (cycles) => set({ cycles }),

  // Prompts
  prompts: {},
  setPrompt: (prompt) =>
    set((state) => ({
      prompts: { ...state.prompts, [prompt.name]: prompt },
    })),
  setPrompts: (prompts) =>
    set({
      prompts: prompts.reduce(
        (acc, p) => ({ ...acc, [p.name]: p }),
        {}
      ),
    }),

  // Handle WebSocket events
  handleEvent: (event) => {
    const state = get();

    switch (event.type) {
      case 'connected':
        set({ connected: true });
        break;

      case 'agent_spawned':
        if (event.agent) {
          state.setAgent(event.agent as Agent);
          // Auto-select if first agent
          if (!state.selectedAgentId) {
            set({ selectedAgentId: (event.agent as Agent).id });
          }
        }
        break;

      case 'agent_output':
        if (event.agentId && event.line) {
          state.addOutputLine(event.agentId as string, event.line as OutputLine);
        }
        break;

      case 'agent_status':
        if (event.agentId && event.status) {
          state.updateAgentStatus(event.agentId as string, event.status as Agent['status']);
        }
        break;

      case 'agent_killed':
        if (event.agentId) {
          state.removeAgent(event.agentId as string);
          // Clear selection if killed agent was selected
          if (state.selectedAgentId === event.agentId) {
            const remainingIds = Object.keys(state.agents).filter(
              (id) => id !== event.agentId
            );
            set({ selectedAgentId: remainingIds[0] || null });
          }
        }
        break;

      case 'cycle_started':
        if (typeof event.cycle === 'number') {
          set({ cycle: event.cycle });
        }
        break;

      case 'cycle_completed':
      case 'cycle_failed':
        if (event.result) {
          state.addCycle(event.result as Cycle);
        }
        break;

      case 'phase_changed':
        if (event.phase) {
          set({ phase: event.phase as CyclePhase });
        }
        break;

      case 'orchestrator_started':
        set({ running: true });
        break;

      case 'orchestrator_stopped':
        set({ running: false, phase: 'IDLE' });
        break;

      case 'prompt_updated':
        // Refetch prompts when one is updated
        break;
    }
  },
}));

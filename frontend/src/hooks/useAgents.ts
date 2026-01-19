import { useEffect, useCallback } from 'react';
import { useAgentStore } from '@/stores/agentStore';
import * as api from '@/lib/api';

export function useInitialData() {
  const { setAgent, setCycles, setPrompts, setOrchestratorState } = useAgentStore();

  const fetchData = useCallback(() => {
    // Fetch current status
    api.getStatus().then((status) => {
      setOrchestratorState(status.running, status.cycle, status.phase);

      // Set agents from pool
      const allAgents = [
        ...status.agentPool.agents.coordinator,
        ...status.agentPool.agents.worker,
        ...status.agentPool.agents.evaluator,
      ];
      allAgents.forEach(setAgent);

      // Set cycles
      setCycles(status.recentCycles);
    }).catch(console.error);
  }, [setAgent, setCycles, setOrchestratorState]);

  useEffect(() => {
    // Fetch initial data
    fetchData();

    // Fetch prompts (only once)
    api.listPrompts().then(({ prompts }) => {
      setPrompts(prompts);
    }).catch(console.error);

    // Periodically refresh agent data (every 5 seconds as fallback, WebSocket handles real-time)
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData, setPrompts]);
}

export function useAgentOutput(agentId: string | null) {
  const { outputBuffers, addOutputLine } = useAgentStore();

  useEffect(() => {
    if (!agentId) return;

    // Fetch initial output for selected agent
    api.getAgentOutput(agentId, 500, 0).then(({ lines }) => {
      lines.forEach((line) => addOutputLine(agentId, line));
    }).catch(console.error);
  }, [agentId, addOutputLine]);

  return outputBuffers[agentId ?? '']?.lines ?? [];
}

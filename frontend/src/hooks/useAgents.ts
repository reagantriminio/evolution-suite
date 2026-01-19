import { useEffect } from 'react';
import { useAgentStore } from '@/stores/agentStore';
import * as api from '@/lib/api';

export function useInitialData() {
  const { setAgent, setCycles, setPrompts, setOrchestratorState } = useAgentStore();

  useEffect(() => {
    // Fetch initial status
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

    // Fetch prompts
    api.listPrompts().then(({ prompts }) => {
      setPrompts(prompts);
    }).catch(console.error);
  }, [setAgent, setCycles, setPrompts, setOrchestratorState]);
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

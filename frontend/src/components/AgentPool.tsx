import { motion, AnimatePresence } from 'framer-motion';
import { Plus } from 'lucide-react';
import { useAgentStore } from '@/stores/agentStore';
import { AgentCard } from './AgentCard';
import * as api from '@/lib/api';
import type { AgentType } from '@/lib/types';

const agentTypes: AgentType[] = ['coordinator', 'worker', 'evaluator'];

export function AgentPool() {
  const { agents, setAgent } = useAgentStore();

  const agentsByType = agentTypes.reduce(
    (acc, type) => ({
      ...acc,
      [type]: Object.values(agents).filter((a) => a.type === type),
    }),
    {} as Record<AgentType, typeof agents[string][]>
  );

  const handleSpawnAgent = async (type: AgentType) => {
    try {
      const agent = await api.spawnAgent(type);
      setAgent(agent);
    } catch (error) {
      console.error('Failed to spawn agent:', error);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
          Agent Pool
        </h2>
        <div className="flex items-center gap-2">
          {agentTypes.map((type) => (
            <button
              key={type}
              onClick={() => handleSpawnAgent(type)}
              className="flex items-center gap-1.5 px-2 py-1 text-xs text-zinc-400 hover:text-zinc-200 bg-zinc-900 hover:bg-zinc-800 rounded border border-zinc-800 hover:border-zinc-700 transition-colors"
            >
              <Plus className="w-3 h-3" />
              <span className="capitalize">{type}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <AnimatePresence mode="popLayout">
          {agentTypes.flatMap((type) =>
            agentsByType[type].map((agent) => (
              <motion.div
                key={agent.id}
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2 }}
              >
                <AgentCard agent={agent} />
              </motion.div>
            ))
          )}
        </AnimatePresence>

        {/* Empty state */}
        {Object.values(agents).length === 0 && (
          <div className="col-span-full flex flex-col items-center justify-center py-12 text-zinc-500">
            <p className="text-sm">No agents running</p>
            <p className="text-xs mt-1">Click a button above to spawn an agent</p>
          </div>
        )}
      </div>
    </div>
  );
}

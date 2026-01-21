import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Crown } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAgentStore } from '@/stores/agentStore';
import { AgentCard } from './AgentCard';
import * as api from '@/lib/api';
import type { AgentType } from '@/lib/types';

const agentTypes: AgentType[] = ['coordinator', 'worker', 'evaluator'];

export function AgentPool() {
  const { agents, setAgent } = useAgentStore();

  // Separate master coordinator from others
  const allCoordinators = Object.values(agents).filter((a) => a.type === 'coordinator');
  const masterCoordinator = allCoordinators.find(
    (a) => a.id.includes('master') || a.assignedBy === null || a.assignedBy === undefined
  ) || allCoordinators[0];
  const otherCoordinators = allCoordinators.filter((a) => a !== masterCoordinator);

  const agentsByType = {
    coordinator: otherCoordinators,
    worker: Object.values(agents).filter((a) => a.type === 'worker'),
    evaluator: Object.values(agents).filter((a) => a.type === 'evaluator'),
  } as Record<AgentType, typeof agents[string][]>;

  const handleSpawnAgent = async (type: AgentType) => {
    try {
      const agent = await api.spawnAgent(type);
      setAgent(agent);
      toast.success(`${type.charAt(0).toUpperCase() + type.slice(1)} agent spawned`);
    } catch (error) {
      console.error('Failed to spawn agent:', error);
      toast.error(`Failed to spawn ${type} agent`);
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

      {/* Master Coordinator Section */}
      {masterCoordinator && (
        <div className="bg-gradient-to-r from-pink-500/10 to-zinc-900/50 rounded-lg border-2 border-pink-500/30 p-4">
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-pink-500/20">
            <Crown className="w-4 h-4 text-pink-400" />
            <h3 className="text-sm font-bold text-pink-400">
              MASTER COORDINATOR
            </h3>
            <span className="text-xs text-zinc-500 ml-auto">
              {masterCoordinator.delegatedTo?.length || 0} agents spawned
            </span>
          </div>
          <motion.div
            layout
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2 }}
          >
            <AgentCard agent={masterCoordinator} isMaster />
          </motion.div>
        </div>
      )}

      {/* Grouped by type */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {agentTypes.map((type) => (
          <div key={type} className="bg-zinc-900/50 rounded-lg border border-zinc-800 p-3">
            {/* Type Header */}
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-zinc-800">
              <h3 className={`text-sm font-medium capitalize ${
                type === 'coordinator' ? 'text-indigo-400' :
                type === 'worker' ? 'text-green-400' :
                'text-amber-400'
              }`}>
                {type}s
              </h3>
              <span className="text-xs text-zinc-500">
                {agentsByType[type].length} active
              </span>
            </div>

            {/* Agent Cards */}
            <div className="space-y-2 max-h-[300px] overflow-y-auto">
              <AnimatePresence mode="popLayout">
                {agentsByType[type].map((agent) => (
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
                ))}
              </AnimatePresence>

              {/* Empty state for this type */}
              {agentsByType[type].length === 0 && (
                <div className="flex flex-col items-center justify-center py-6 text-zinc-600">
                  <p className="text-xs">No {type}s</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Global empty state */}
      {Object.values(agents).length === 0 && (
        <div className="text-center py-4 text-zinc-500">
          <p className="text-sm">Click a button above to spawn an agent</p>
        </div>
      )}
    </div>
  );
}

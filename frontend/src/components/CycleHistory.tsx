import { motion, AnimatePresence } from 'framer-motion';
import { Check, X, Clock } from 'lucide-react';
import { useAgentStore } from '@/stores/agentStore';
import clsx from 'clsx';
import type { Cycle, TaskType } from '@/lib/types';

const taskTypeColors: Record<TaskType, string> = {
  EVOLVE: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  CLEANUP: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  BUGFIX: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  DONE: 'bg-green-500/20 text-green-400 border-green-500/30',
};

export function CycleHistory() {
  const { cycles } = useAgentStore();

  return (
    <div className="h-full flex flex-col bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
        <h3 className="text-sm font-medium text-zinc-300">Cycle History</h3>
        <span className="text-xs text-zinc-500">{cycles.length} cycles</span>
      </div>

      {/* Timeline */}
      <div className="flex-1 overflow-x-auto">
        <div className="flex items-stretch h-full px-4 py-3 gap-3">
          <AnimatePresence mode="popLayout">
            {cycles.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-zinc-600 text-sm">
                No cycles yet
              </div>
            ) : (
              cycles.map((cycle, index) => (
                <motion.div
                  key={cycle.cycle}
                  layout
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.2, delay: index * 0.05 }}
                >
                  <CycleCard cycle={cycle} />
                </motion.div>
              ))
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function CycleCard({ cycle }: { cycle: Cycle }) {
  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const timeAgo = formatDuration(cycle.durationSeconds);

  return (
    <div
      className={clsx(
        'flex-shrink-0 w-64 p-4 rounded-lg border transition-all hover:border-zinc-600',
        'bg-zinc-800/50',
        cycle.success ? 'border-zinc-700' : 'border-red-900/50'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {cycle.success ? (
            <div className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center">
              <Check className="w-3 h-3 text-green-400" />
            </div>
          ) : (
            <div className="w-5 h-5 rounded-full bg-red-500/20 flex items-center justify-center">
              <X className="w-3 h-3 text-red-400" />
            </div>
          )}
          <span className="text-sm font-medium text-zinc-300">
            Cycle {cycle.cycle}
          </span>
        </div>

        <span
          className={clsx(
            'px-2 py-0.5 text-xs rounded border',
            taskTypeColors[cycle.taskType]
          )}
        >
          {cycle.taskType}
        </span>
      </div>

      {/* Description */}
      <p className="text-sm text-zinc-400 line-clamp-2 mb-3 min-h-[2.5rem]">
        {cycle.description}
      </p>

      {/* Stats */}
      <div className="flex items-center gap-3 text-xs text-zinc-500">
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          <span>{timeAgo}</span>
        </div>

        {cycle.filesModified.length > 0 && (
          <span>{cycle.filesModified.length} files</span>
        )}

        {cycle.commitHash && (
          <span className="font-mono text-zinc-600">{cycle.commitHash}</span>
        )}
      </div>

      {/* Error message */}
      {cycle.error && (
        <div className="mt-2 p-2 bg-red-900/20 rounded text-xs text-red-400 line-clamp-2">
          {cycle.error}
        </div>
      )}
    </div>
  );
}

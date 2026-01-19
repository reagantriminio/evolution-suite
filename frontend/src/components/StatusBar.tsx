import { motion } from 'framer-motion';
import { Play, Square, Loader2 } from 'lucide-react';
import { useAgentStore } from '@/stores/agentStore';
import * as api from '@/lib/api';
import type { CyclePhase } from '@/lib/types';

interface StatusBarProps {
  connected: boolean;
  running: boolean;
  cycle: number;
  phase: CyclePhase;
}

const phaseLabels: Record<CyclePhase, string> = {
  IDLE: 'Idle',
  COORDINATING: 'Coordinating',
  WORKING: 'Working',
  EVALUATING: 'Evaluating',
  COMPLETED: 'Completed',
  FAILED: 'Failed',
};

export function StatusBar({ running, cycle, phase }: StatusBarProps) {
  const { setOrchestratorState } = useAgentStore();

  const handleStart = async () => {
    try {
      await api.startOrchestrator();
      setOrchestratorState(true, cycle, phase);
    } catch (error) {
      console.error('Failed to start:', error);
    }
  };

  const handleStop = async () => {
    try {
      await api.stopOrchestrator();
    } catch (error) {
      console.error('Failed to stop:', error);
    }
  };

  return (
    <div className="flex items-center gap-4">
      {/* Status badge */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900 rounded-md border border-zinc-800">
        {running ? (
          <motion.div
            className="w-2 h-2 rounded-full bg-green-500"
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
        ) : (
          <div className="w-2 h-2 rounded-full bg-zinc-500" />
        )}
        <span className="text-sm text-zinc-300">
          {running ? phaseLabels[phase] : 'Stopped'}
        </span>
      </div>

      {/* Cycle counter */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900 rounded-md border border-zinc-800">
        <span className="text-sm text-zinc-500">Cycle</span>
        <span className="text-sm font-mono text-zinc-100">{cycle}</span>
      </div>

      {/* Control buttons */}
      <div className="flex items-center gap-2">
        {!running ? (
          <button
            onClick={handleStart}
            className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded-md border border-zinc-700 transition-colors"
          >
            <Play className="w-4 h-4" />
            <span className="text-sm">Start</span>
          </button>
        ) : (
          <button
            onClick={handleStop}
            className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded-md border border-zinc-700 transition-colors"
          >
            {phase !== 'IDLE' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Square className="w-4 h-4" />
            )}
            <span className="text-sm">Stop</span>
          </button>
        )}
      </div>
    </div>
  );
}

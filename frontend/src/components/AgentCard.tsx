import { motion } from 'framer-motion';
import { Pause, Play, X, Syringe } from 'lucide-react';
import { useState } from 'react';
import { useAgentStore } from '@/stores/agentStore';
import * as api from '@/lib/api';
import type { Agent, AgentStatus } from '@/lib/types';
import clsx from 'clsx';

interface AgentCardProps {
  agent: Agent;
}

const statusColors: Record<AgentStatus, string> = {
  idle: 'bg-zinc-500',
  starting: 'bg-yellow-500',
  running: 'bg-green-500',
  paused: 'bg-yellow-500',
  stopping: 'bg-orange-500',
  stopped: 'bg-zinc-500',
  failed: 'bg-red-500',
};

const statusLabels: Record<AgentStatus, string> = {
  idle: 'Idle',
  starting: 'Starting',
  running: 'Running',
  paused: 'Paused',
  stopping: 'Stopping',
  stopped: 'Stopped',
  failed: 'Failed',
};

export function AgentCard({ agent }: AgentCardProps) {
  const { selectedAgentId, setSelectedAgentId, outputBuffers } = useAgentStore();
  const [showInject, setShowInject] = useState(false);
  const [guidance, setGuidance] = useState('');

  const isSelected = selectedAgentId === agent.id;
  const isRunning = agent.status === 'running';
  const isPaused = agent.status === 'paused';
  const outputLines = outputBuffers[agent.id]?.lines ?? [];
  const lastOutput = outputLines[outputLines.length - 1];

  const handlePause = async () => {
    try {
      await api.pauseAgent(agent.id);
    } catch (error) {
      console.error('Failed to pause:', error);
    }
  };

  const handleResume = async () => {
    try {
      await api.resumeAgent(agent.id);
    } catch (error) {
      console.error('Failed to resume:', error);
    }
  };

  const handleKill = async () => {
    try {
      await api.killAgent(agent.id);
    } catch (error) {
      console.error('Failed to kill:', error);
    }
  };

  const handleInject = async () => {
    if (!guidance.trim()) return;
    try {
      await api.injectGuidance(agent.id, guidance);
      setGuidance('');
      setShowInject(false);
    } catch (error) {
      console.error('Failed to inject:', error);
    }
  };

  return (
    <div
      className={clsx(
        'relative p-4 rounded-lg border transition-all cursor-pointer',
        'bg-zinc-900 hover:bg-zinc-800/80',
        isSelected
          ? 'border-zinc-600 ring-1 ring-zinc-600'
          : 'border-zinc-800 hover:border-zinc-700'
      )}
      onClick={() => setSelectedAgentId(agent.id)}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <motion.div
            className={clsx('w-2 h-2 rounded-full', statusColors[agent.status])}
            animate={isRunning ? { scale: [1, 1.2, 1] } : {}}
            transition={{ duration: 2, repeat: Infinity }}
          />
          <span className="font-medium text-sm uppercase tracking-wide text-zinc-300">
            {agent.type}
          </span>
        </div>
        <span className="text-xs text-zinc-500 font-mono">
          {agent.id.split('-')[1]}
        </span>
      </div>

      {/* Status */}
      <div className="text-xs text-zinc-500 mb-2">
        {statusLabels[agent.status]}
      </div>

      {/* Current task / last output */}
      <div className="h-12 mb-3 overflow-hidden">
        {agent.currentTask ? (
          <p className="text-sm text-zinc-400 line-clamp-2">
            {agent.currentTask}
          </p>
        ) : lastOutput ? (
          <p className={clsx(
            'text-sm line-clamp-2 font-mono',
            lastOutput.type === 'thinking' ? 'text-zinc-500 italic' : 'text-zinc-400'
          )}>
            {lastOutput.content}
          </p>
        ) : (
          <p className="text-sm text-zinc-600 italic">Waiting...</p>
        )}
      </div>

      {/* Stats */}
      <div className="flex items-center gap-4 text-xs text-zinc-500 mb-3">
        <span>{agent.toolsUsed} tools</span>
        <span>{agent.filesModified.length} files</span>
        <span>{agent.outputLines} lines</span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={() => setShowInject(!showInject)}
          className="flex items-center gap-1 px-2 py-1 text-xs bg-zinc-800 hover:bg-zinc-700 rounded border border-zinc-700 transition-colors"
        >
          <Syringe className="w-3 h-3" />
          Inject
        </button>

        {isRunning && (
          <button
            onClick={handlePause}
            className="flex items-center gap-1 px-2 py-1 text-xs bg-zinc-800 hover:bg-zinc-700 rounded border border-zinc-700 transition-colors"
          >
            <Pause className="w-3 h-3" />
            Pause
          </button>
        )}

        {isPaused && (
          <button
            onClick={handleResume}
            className="flex items-center gap-1 px-2 py-1 text-xs bg-zinc-800 hover:bg-zinc-700 rounded border border-zinc-700 transition-colors"
          >
            <Play className="w-3 h-3" />
            Resume
          </button>
        )}

        <button
          onClick={handleKill}
          className="flex items-center gap-1 px-2 py-1 text-xs bg-zinc-800 hover:bg-red-900/50 text-zinc-400 hover:text-red-400 rounded border border-zinc-700 hover:border-red-800 transition-colors"
        >
          <X className="w-3 h-3" />
          Kill
        </button>
      </div>

      {/* Inject guidance overlay */}
      {showInject && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute inset-x-0 top-full mt-2 p-3 bg-zinc-900 border border-zinc-700 rounded-lg shadow-lg z-10"
          onClick={(e) => e.stopPropagation()}
        >
          <textarea
            value={guidance}
            onChange={(e) => setGuidance(e.target.value)}
            placeholder="Enter guidance for this agent..."
            className="w-full h-20 px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded resize-none focus:outline-none focus:border-zinc-600"
          />
          <div className="flex justify-end gap-2 mt-2">
            <button
              onClick={() => setShowInject(false)}
              className="px-3 py-1 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleInject}
              disabled={!guidance.trim()}
              className="px-3 py-1 text-xs bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 disabled:cursor-not-allowed rounded transition-colors"
            >
              Inject
            </button>
          </div>
        </motion.div>
      )}
    </div>
  );
}

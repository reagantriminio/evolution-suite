import { motion } from 'framer-motion';
import { Pause, Play, X, Syringe, Rocket, RotateCcw } from 'lucide-react';
import { useState } from 'react';
import toast from 'react-hot-toast';
import { useAgentStore } from '@/stores/agentStore';
import * as api from '@/lib/api';
import type { Agent, AgentStatus } from '@/lib/types';
import clsx from 'clsx';

interface AgentCardProps {
  agent: Agent;
  isMaster?: boolean;
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

const defaultPrompts: Record<string, string> = {
  coordinator: 'You are the coordinator agent. Review the EVOLUTION_STATE.md file and determine the next steps for the project evolution. Coordinate worker agents to implement changes.',
  worker: 'You are a worker agent. Read your assigned task from the state file and implement the required changes. Focus on code quality and testing.',
  evaluator: 'You are the evaluator agent. Review the changes made by worker agents. Check for code quality, test coverage, and potential issues. Provide feedback.',
};

const getContinuePrompt = (agent: Agent): string => {
  const baseContext = agent.goal ? `Previous goal: ${agent.goal}\n\n` : '';

  if (agent.type === 'coordinator') {
    return `${baseContext}You are continuing as the MASTER COORDINATOR.

Your previous session ended. Review what was accomplished and continue coordinating:
1. Check the status of any worker/evaluator agents you spawned
2. If workers completed, spawn evaluators to review their work
3. If evaluators found issues, spawn new workers to fix them
4. Continue until the original directive is fully accomplished

REMEMBER: You coordinate by spawning agents - do NOT do the work yourself.`;
  }

  if (agent.type === 'evaluator') {
    return `${baseContext}You are continuing as an EVALUATOR.

Your previous session ended. Continue your evaluation:
1. Review any changes that were made since your last check
2. Identify any remaining issues or improvements needed
3. Provide a clear summary of your findings`;
  }

  return `${baseContext}You are continuing as a WORKER.

Your previous session ended. Continue your task:
1. Check your progress from the previous session
2. Complete any remaining work
3. Ensure all changes are properly tested`;
};

export function AgentCard({ agent, isMaster = false }: AgentCardProps) {
  const { selectedAgentId, setSelectedAgentId, outputBuffers } = useAgentStore();
  const [showInject, setShowInject] = useState(false);
  const [showStart, setShowStart] = useState(false);
  const [showContinue, setShowContinue] = useState(false);
  const [showKillConfirm, setShowKillConfirm] = useState(false);
  const [guidance, setGuidance] = useState('');
  const [prompt, setPrompt] = useState(defaultPrompts[agent.type] || '');
  const [continuePrompt, setContinuePrompt] = useState('');

  const isSelected = selectedAgentId === agent.id;
  const isRunning = agent.status === 'running';
  const isPaused = agent.status === 'paused';
  const isIdle = agent.status === 'idle';
  const isStopped = agent.status === 'stopped';
  const isFailed = agent.status === 'failed';
  const outputLines = outputBuffers[agent.id]?.lines ?? [];
  const lastOutput = outputLines[outputLines.length - 1];

  const handleStart = async () => {
    if (!prompt.trim()) return;
    try {
      await api.startAgent(agent.id, prompt);
      setShowStart(false);
      toast.success('Agent started');
    } catch (error) {
      console.error('Failed to start:', error);
      toast.error('Failed to start agent');
    }
  };

  const handlePause = async () => {
    try {
      await api.pauseAgent(agent.id);
      toast.success('Agent paused');
    } catch (error) {
      console.error('Failed to pause:', error);
      toast.error('Failed to pause agent');
    }
  };

  const handleResume = async () => {
    try {
      await api.resumeAgent(agent.id);
      toast.success('Agent resumed');
    } catch (error) {
      console.error('Failed to resume:', error);
      toast.error('Failed to resume agent');
    }
  };

  const handleKill = async () => {
    try {
      await api.killAgent(agent.id);
      setShowKillConfirm(false);
      toast.success('Agent killed');
    } catch (error) {
      console.error('Failed to kill:', error);
      toast.error('Failed to kill agent');
    }
  };

  const handleInject = async () => {
    if (!guidance.trim()) return;
    try {
      await api.injectGuidance(agent.id, guidance);
      setGuidance('');
      setShowInject(false);
      toast.success('Guidance injected');
    } catch (error) {
      console.error('Failed to inject:', error);
      toast.error('Failed to inject guidance');
    }
  };

  const handleContinue = async () => {
    try {
      // Use custom prompt if provided, otherwise use default continue prompt
      const promptToUse = continuePrompt.trim() || getContinuePrompt(agent);
      await api.startAgent(agent.id, promptToUse);
      setContinuePrompt('');
      setShowContinue(false);
      toast.success('Agent continued');
    } catch (error) {
      console.error('Failed to continue agent:', error);
      toast.error('Failed to continue agent');
    }
  };

  const handleQuickContinue = async () => {
    try {
      const promptToUse = getContinuePrompt(agent);
      await api.startAgent(agent.id, promptToUse);
      toast.success('Agent continued');
    } catch (error) {
      console.error('Failed to continue agent:', error);
      toast.error('Failed to continue agent');
    }
  };

  return (
    <div
      className={clsx(
        'relative p-4 rounded-lg border transition-all cursor-pointer',
        isMaster
          ? 'bg-zinc-900 hover:bg-zinc-800/80'
          : 'bg-zinc-900 hover:bg-zinc-800/80',
        isSelected
          ? isMaster
            ? 'border-pink-500/50 ring-1 ring-pink-500/30'
            : 'border-zinc-600 ring-1 ring-zinc-600'
          : isMaster
            ? 'border-pink-500/30 hover:border-pink-500/50'
            : 'border-zinc-800 hover:border-zinc-700'
      )}
      onClick={() => setSelectedAgentId(agent.id)}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <motion.div
            className={clsx(
              'w-2 h-2 rounded-full',
              isMaster && isRunning ? 'bg-pink-500' : statusColors[agent.status]
            )}
            animate={isRunning ? { scale: [1, 1.2, 1] } : {}}
            transition={{ duration: 2, repeat: Infinity }}
          />
          <span className={clsx(
            'font-medium text-sm uppercase tracking-wide',
            isMaster ? 'text-pink-400' : 'text-zinc-300'
          )}>
            {isMaster ? 'MASTER' : agent.type}
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
      <div className="flex items-center gap-2 flex-wrap" onClick={(e) => e.stopPropagation()}>
        {isIdle && (
          <button
            onClick={() => setShowStart(!showStart)}
            className="flex items-center gap-1 px-2 py-1 text-xs bg-green-900/50 hover:bg-green-800/50 text-green-400 rounded border border-green-800 transition-colors"
          >
            <Rocket className="w-3 h-3" />
            Start
          </button>
        )}

        {(isStopped || isFailed) && (
          <>
            <button
              onClick={handleQuickContinue}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-900/50 hover:bg-blue-800/50 text-blue-400 rounded border border-blue-800 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Continue
            </button>
            <button
              onClick={() => setShowContinue(!showContinue)}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-400 rounded border border-zinc-700 transition-colors"
            >
              Custom
            </button>
          </>
        )}

        {(isRunning || isPaused) && (
          <button
            onClick={() => setShowInject(!showInject)}
            className="flex items-center gap-1 px-2 py-1 text-xs bg-zinc-800 hover:bg-zinc-700 rounded border border-zinc-700 transition-colors"
          >
            <Syringe className="w-3 h-3" />
            Inject
          </button>
        )}

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
          onClick={() => setShowKillConfirm(true)}
          className="flex items-center gap-1 px-2 py-1 text-xs bg-zinc-800 hover:bg-red-900/50 text-zinc-400 hover:text-red-400 rounded border border-zinc-700 hover:border-red-800 transition-colors"
        >
          <X className="w-3 h-3" />
          Kill
        </button>
      </div>

      {/* Start agent overlay */}
      {showStart && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute inset-x-0 top-full mt-2 p-3 bg-zinc-900 border border-green-800 rounded-lg shadow-lg z-10"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="text-xs text-green-400 mb-2">Start agent with prompt:</div>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter the prompt to start this agent..."
            className="w-full h-24 px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded resize-none focus:outline-none focus:border-green-600"
          />
          <div className="flex justify-end gap-2 mt-2">
            <button
              onClick={() => setShowStart(false)}
              className="px-3 py-1 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleStart}
              disabled={!prompt.trim()}
              className="px-3 py-1 text-xs bg-green-700 hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed rounded transition-colors"
            >
              Start Agent
            </button>
          </div>
        </motion.div>
      )}

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

      {/* Continue with custom prompt overlay */}
      {showContinue && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute inset-x-0 top-full mt-2 p-3 bg-zinc-900 border border-blue-800 rounded-lg shadow-lg z-10"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="text-xs text-blue-400 mb-2">Continue agent with custom prompt:</div>
          <textarea
            value={continuePrompt}
            onChange={(e) => setContinuePrompt(e.target.value)}
            placeholder={getContinuePrompt(agent).slice(0, 200) + '...'}
            className="w-full h-24 px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded resize-none focus:outline-none focus:border-blue-600"
          />
          <div className="flex justify-end gap-2 mt-2">
            <button
              onClick={() => setShowContinue(false)}
              className="px-3 py-1 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleContinue}
              className="px-3 py-1 text-xs bg-blue-700 hover:bg-blue-600 rounded transition-colors"
            >
              Continue Agent
            </button>
          </div>
        </motion.div>
      )}

      {/* Kill confirmation dialog */}
      {showKillConfirm && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute inset-x-0 top-full mt-2 p-3 bg-zinc-900 border border-red-800 rounded-lg shadow-lg z-10"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="text-sm text-zinc-300 mb-3">
            Are you sure you want to kill agent <span className="font-mono text-red-400">{agent.id}</span>?
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowKillConfirm(false)}
              className="px-3 py-1 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleKill}
              className="px-3 py-1 text-xs bg-red-700 hover:bg-red-600 text-white rounded transition-colors"
            >
              Confirm
            </button>
          </div>
        </motion.div>
      )}
    </div>
  );
}

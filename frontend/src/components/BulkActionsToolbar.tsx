import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Pause, Play, Square, Syringe } from 'lucide-react';
import * as api from '@/lib/api';

interface BulkActionsToolbarProps {
  selectedIds: string[];
  onClearSelection: () => void;
  onActionComplete: () => void;
}

export function BulkActionsToolbar({
  selectedIds,
  onClearSelection,
  onActionComplete,
}: BulkActionsToolbarProps) {
  const [showGuidanceInput, setShowGuidanceInput] = useState(false);
  const [guidanceContent, setGuidanceContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Filter to only agent IDs (not state files)
  const agentIds = selectedIds.filter((id) => !id.startsWith('file-'));
  const count = agentIds.length;

  if (count === 0) return null;

  const handleBulkAction = async (action: 'pause' | 'resume' | 'kill') => {
    setIsLoading(true);
    try {
      await api.bulkAgentAction(agentIds, action);
      onActionComplete();
      if (action === 'kill') {
        onClearSelection();
      }
    } catch (error) {
      console.error(`Failed to ${action} agents:`, error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBulkGuidance = async () => {
    if (!guidanceContent.trim()) return;

    setIsLoading(true);
    try {
      await api.bulkInjectGuidance(agentIds, guidanceContent);
      setGuidanceContent('');
      setShowGuidanceInput(false);
      onActionComplete();
    } catch (error) {
      console.error('Failed to inject guidance:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: -50, opacity: 0 }}
        className="fixed top-4 left-1/2 -translate-x-1/2 z-50"
      >
        <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl">
          {/* Main toolbar */}
          <div className="flex items-center gap-3 px-4 py-2">
            {/* Selection count */}
            <div className="flex items-center gap-2 pr-3 border-r border-zinc-700">
              <div className="w-6 h-6 bg-blue-600 rounded flex items-center justify-center text-xs font-medium text-white">
                {count}
              </div>
              <span className="text-sm text-zinc-300">
                agent{count !== 1 ? 's' : ''} selected
              </span>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => handleBulkAction('pause')}
                disabled={isLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800 rounded transition-colors disabled:opacity-50"
                title="Pause all selected"
              >
                <Pause className="w-4 h-4" />
                Pause
              </button>

              <button
                onClick={() => handleBulkAction('resume')}
                disabled={isLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800 rounded transition-colors disabled:opacity-50"
                title="Resume all selected"
              >
                <Play className="w-4 h-4" />
                Resume
              </button>

              <button
                onClick={() => setShowGuidanceInput(!showGuidanceInput)}
                disabled={isLoading}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded transition-colors disabled:opacity-50 ${
                  showGuidanceInput
                    ? 'bg-purple-600 text-white'
                    : 'text-zinc-300 hover:bg-zinc-800'
                }`}
                title="Inject guidance into all selected"
              >
                <Syringe className="w-4 h-4" />
                Guidance
              </button>

              <div className="w-px h-6 bg-zinc-700 mx-1" />

              <button
                onClick={() => handleBulkAction('kill')}
                disabled={isLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-400 hover:bg-red-500/10 rounded transition-colors disabled:opacity-50"
                title="Kill all selected"
              >
                <Square className="w-4 h-4" />
                Kill All
              </button>
            </div>

            {/* Clear selection */}
            <button
              onClick={onClearSelection}
              className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors ml-2"
              title="Clear selection"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Guidance input */}
          <AnimatePresence>
            {showGuidanceInput && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="border-t border-zinc-700 overflow-hidden"
              >
                <div className="p-3">
                  <textarea
                    value={guidanceContent}
                    onChange={(e) => setGuidanceContent(e.target.value)}
                    placeholder="Enter guidance for all selected agents..."
                    className="w-full h-24 p-2 bg-zinc-950 border border-zinc-700 rounded text-sm text-zinc-300 resize-none focus:outline-none focus:border-purple-500"
                  />
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-zinc-500">
                      Will be injected into {count} agent{count !== 1 ? 's' : ''}
                    </span>
                    <button
                      onClick={handleBulkGuidance}
                      disabled={!guidanceContent.trim() || isLoading}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-purple-600 hover:bg-purple-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Syringe className="w-4 h-4" />
                      {isLoading ? 'Injecting...' : 'Inject'}
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

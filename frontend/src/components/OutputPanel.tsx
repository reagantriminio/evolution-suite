import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Download } from 'lucide-react';
import { useAgentStore } from '@/stores/agentStore';
import clsx from 'clsx';
import type { OutputLine } from '@/lib/types';

export function OutputPanel() {
  const { agents, selectedAgentId, setSelectedAgentId, outputBuffers } = useAgentStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);

  const agentList = Object.values(agents);
  const selectedAgent = selectedAgentId ? agents[selectedAgentId] : null;
  const outputLines = selectedAgentId ? outputBuffers[selectedAgentId]?.lines ?? [] : [];

  // Auto-scroll to bottom when new output arrives
  useEffect(() => {
    if (autoScrollRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [outputLines.length]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    // Enable auto-scroll if near bottom
    autoScrollRef.current = scrollHeight - scrollTop - clientHeight < 50;
  };

  const handleExport = () => {
    if (!selectedAgentId || outputLines.length === 0) return;
    const content = outputLines
      .map((line) => `[${line.timestamp}] [${line.type}] ${line.content}`)
      .join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedAgentId}-output.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full flex flex-col bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-medium text-zinc-300">Agent Output</h3>

          {/* Agent selector */}
          <div className="relative">
            <select
              value={selectedAgentId ?? ''}
              onChange={(e) => setSelectedAgentId(e.target.value || null)}
              className="appearance-none pl-3 pr-8 py-1 text-sm bg-zinc-800 border border-zinc-700 rounded focus:outline-none focus:border-zinc-600 cursor-pointer"
            >
              <option value="">Select agent...</option>
              {agentList.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.type} - {agent.id.split('-')[1]}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">
            {outputLines.length} lines
          </span>
          <button
            onClick={handleExport}
            disabled={outputLines.length === 0}
            className="p-1.5 text-zinc-500 hover:text-zinc-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Export logs"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Output content */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 font-mono text-sm"
      >
        {!selectedAgentId ? (
          <div className="h-full flex items-center justify-center text-zinc-600">
            Select an agent to view output
          </div>
        ) : outputLines.length === 0 ? (
          <div className="h-full flex items-center justify-center text-zinc-600">
            No output yet
          </div>
        ) : (
          <AnimatePresence mode="popLayout">
            {outputLines.map((line, index) => (
              <OutputLineItem key={`${line.timestamp}-${index}`} line={line} />
            ))}
          </AnimatePresence>
        )}

        {/* Typewriter cursor for running agents */}
        {selectedAgent?.status === 'running' && (
          <span className="typewriter-cursor text-zinc-500" />
        )}
      </div>
    </div>
  );
}

function OutputLineItem({ line }: { line: OutputLine }) {
  const timestamp = new Date(line.timestamp).toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const getIcon = () => {
    switch (line.type) {
      case 'thinking':
      case 'thinking_delta':
        return '💭';
      case 'tool_use':
        return '🔧';
      case 'error':
        return '❌';
      default:
        return '';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      className={clsx(
        'py-0.5 leading-relaxed',
        line.type === 'thinking' || line.type === 'thinking_delta'
          ? 'text-zinc-500 italic'
          : line.type === 'tool_use'
          ? 'text-zinc-400'
          : line.type === 'error'
          ? 'text-red-400'
          : 'text-zinc-300'
      )}
    >
      <span className="text-zinc-600 mr-2">{timestamp}</span>
      {getIcon() && <span className="mr-1">{getIcon()}</span>}
      <span className="whitespace-pre-wrap break-words">{line.content}</span>
    </motion.div>
  );
}

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Play,
  Pause,
  Square,
  Syringe,
  FileText,
  Save,
  RotateCcw,
  Clock,
  Cpu,
  File,
  DollarSign,
} from 'lucide-react';
import { useAgentStore } from '@/stores/agentStore';
import type { StateFile, Prompt, OutputLine } from '@/lib/types';
import * as api from '@/lib/api';

interface SlideOutPanelProps {
  isOpen: boolean;
  onClose: () => void;
  selectedId: string | null;
  selectedType: 'agent' | 'stateFile' | null;
  stateFiles: StateFile[];
  prompts: Prompt[];
  onPromptUpdate: (name: string, content: string) => void;
}

export function SlideOutPanel({
  isOpen,
  onClose,
  selectedId,
  selectedType,
  stateFiles,
  prompts,
  onPromptUpdate,
}: SlideOutPanelProps) {
  const { agents, outputBuffers } = useAgentStore();
  const [guidanceContent, setGuidanceContent] = useState('');
  const [promptContent, setPromptContent] = useState('');
  const [stateFileContent, setStateFileContent] = useState('');
  const [activeTab, setActiveTab] = useState<'output' | 'prompt' | 'guidance'>('output');
  const [isSaving, setIsSaving] = useState(false);
  const outputRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Get selected agent or state file
  const selectedAgent = selectedType === 'agent' && selectedId ? agents[selectedId] : null;
  const selectedStateFile = selectedType === 'stateFile' && selectedId
    ? stateFiles.find((f) => f.path === selectedId)
    : null;

  // Get agent output
  const output: OutputLine[] = selectedAgent ? outputBuffers[selectedAgent.id]?.lines || [] : [];

  // Get matching prompt for agent type
  const matchingPrompt = selectedAgent
    ? prompts.find((p) => p.name === selectedAgent.type)
    : null;

  // Initialize prompt content when agent changes
  useEffect(() => {
    if (matchingPrompt) {
      setPromptContent(matchingPrompt.content);
    }
  }, [matchingPrompt]);

  // Initialize state file content
  useEffect(() => {
    if (selectedStateFile) {
      setStateFileContent(selectedStateFile.content);
    }
  }, [selectedStateFile]);

  // Auto-scroll output
  useEffect(() => {
    if (autoScroll && outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output, autoScroll]);

  const handleInjectGuidance = async () => {
    if (!selectedAgent || !guidanceContent.trim()) return;

    try {
      await api.injectGuidance(selectedAgent.id, guidanceContent);
      setGuidanceContent('');
    } catch (error) {
      console.error('Failed to inject guidance:', error);
    }
  };

  const handleSavePrompt = async () => {
    if (!selectedAgent || !promptContent.trim()) return;

    setIsSaving(true);
    try {
      await api.updatePrompt(selectedAgent.type, promptContent);
      onPromptUpdate(selectedAgent.type, promptContent);
    } catch (error) {
      console.error('Failed to save prompt:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleResetPrompt = () => {
    if (matchingPrompt) {
      setPromptContent(matchingPrompt.content);
    }
  };

  const handleSaveStateFile = async () => {
    if (!selectedStateFile) return;

    setIsSaving(true);
    try {
      await api.updateStateFile(selectedStateFile.path, stateFileContent);
    } catch (error) {
      console.error('Failed to save state file:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handlePause = async () => {
    if (!selectedAgent) return;
    try {
      await api.pauseAgent(selectedAgent.id);
    } catch (error) {
      console.error('Failed to pause agent:', error);
    }
  };

  const handleResume = async () => {
    if (!selectedAgent) return;
    try {
      await api.resumeAgent(selectedAgent.id);
    } catch (error) {
      console.error('Failed to resume agent:', error);
    }
  };

  const handleKill = async () => {
    if (!selectedAgent) return;
    try {
      await api.killAgent(selectedAgent.id);
      onClose();
    } catch (error) {
      console.error('Failed to kill agent:', error);
    }
  };

  const formatDuration = (startedAt: string | null) => {
    if (!startedAt) return '0s';
    const start = new Date(startedAt);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - start.getTime()) / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="fixed right-0 top-0 h-full w-[450px] bg-zinc-900 border-l border-zinc-700 shadow-2xl z-50 flex flex-col"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-zinc-700">
            <div className="flex items-center gap-3">
              {selectedType === 'agent' && selectedAgent && (
                <>
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{
                      backgroundColor:
                        selectedAgent.status === 'running'
                          ? '#22c55e'
                          : selectedAgent.status === 'failed'
                          ? '#ef4444'
                          : '#6b7280',
                    }}
                  />
                  <div>
                    <div className="text-sm font-medium text-zinc-200">
                      {selectedAgent.type.charAt(0).toUpperCase() + selectedAgent.type.slice(1)}
                    </div>
                    <div className="text-xs text-zinc-500 font-mono">{selectedAgent.id}</div>
                  </div>
                </>
              )}
              {selectedType === 'stateFile' && selectedStateFile && (
                <>
                  <FileText className="w-5 h-5 text-purple-400" />
                  <div>
                    <div className="text-sm font-medium text-zinc-200">{selectedStateFile.name}</div>
                    <div className="text-xs text-zinc-500">{selectedStateFile.path}</div>
                  </div>
                </>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Agent Content */}
          {selectedType === 'agent' && selectedAgent && (
            <>
              {/* Stats */}
              <div className="grid grid-cols-4 gap-2 p-4 border-b border-zinc-800">
                <div className="text-center">
                  <Clock className="w-4 h-4 mx-auto text-zinc-500 mb-1" />
                  <div className="text-sm font-medium text-zinc-300">
                    {formatDuration(selectedAgent.startedAt)}
                  </div>
                  <div className="text-xs text-zinc-500">Runtime</div>
                </div>
                <div className="text-center">
                  <Cpu className="w-4 h-4 mx-auto text-zinc-500 mb-1" />
                  <div className="text-sm font-medium text-zinc-300">{selectedAgent.toolsUsed}</div>
                  <div className="text-xs text-zinc-500">Tools</div>
                </div>
                <div className="text-center">
                  <File className="w-4 h-4 mx-auto text-zinc-500 mb-1" />
                  <div className="text-sm font-medium text-zinc-300">
                    {selectedAgent.filesModified.length}
                  </div>
                  <div className="text-xs text-zinc-500">Files</div>
                </div>
                <div className="text-center">
                  <DollarSign className="w-4 h-4 mx-auto text-zinc-500 mb-1" />
                  <div className="text-sm font-medium text-emerald-400">
                    ${selectedAgent.usage?.costUsd.toFixed(4) || '0.0000'}
                  </div>
                  <div className="text-xs text-zinc-500">Cost</div>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex border-b border-zinc-800">
                {(['output', 'prompt', 'guidance'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                      activeTab === tab
                        ? 'text-blue-400 border-b-2 border-blue-400'
                        : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-hidden flex flex-col">
                {activeTab === 'output' && (
                  <div className="flex-1 flex flex-col">
                    <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800">
                      <span className="text-xs text-zinc-500">{output.length} lines</span>
                      <label className="flex items-center gap-2 text-xs text-zinc-400">
                        <input
                          type="checkbox"
                          checked={autoScroll}
                          onChange={(e) => setAutoScroll(e.target.checked)}
                          className="rounded border-zinc-600 bg-zinc-800"
                        />
                        Auto-scroll
                      </label>
                    </div>
                    <div
                      ref={outputRef}
                      className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-1"
                    >
                      {output.map((line, i) => (
                        <div
                          key={i}
                          className={`${
                            line.type === 'error'
                              ? 'text-red-400'
                              : line.type === 'thinking' || line.type === 'thinking_delta'
                              ? 'text-zinc-500 italic'
                              : line.type === 'tool_use'
                              ? 'text-blue-400'
                              : 'text-zinc-300'
                          }`}
                        >
                          {line.content}
                        </div>
                      ))}
                      {output.length === 0 && (
                        <div className="text-zinc-500 text-center py-8">No output yet</div>
                      )}
                    </div>
                  </div>
                )}

                {activeTab === 'prompt' && (
                  <div className="flex-1 flex flex-col">
                    <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800">
                      <span className="text-xs text-zinc-500">
                        Template: {selectedAgent.type}_default
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={handleResetPrompt}
                          className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors"
                          title="Reset to saved"
                        >
                          <RotateCcw className="w-4 h-4" />
                        </button>
                        <button
                          onClick={handleSavePrompt}
                          disabled={isSaving}
                          className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50"
                        >
                          <Save className="w-3 h-3" />
                          {isSaving ? 'Saving...' : 'Save'}
                        </button>
                      </div>
                    </div>
                    <textarea
                      value={promptContent}
                      onChange={(e) => setPromptContent(e.target.value)}
                      className="flex-1 p-4 bg-zinc-950 text-zinc-300 text-sm font-mono resize-none focus:outline-none"
                      placeholder="Enter prompt template..."
                    />
                  </div>
                )}

                {activeTab === 'guidance' && (
                  <div className="flex-1 flex flex-col p-4">
                    <div className="text-xs text-zinc-400 mb-2">
                      Inject guidance into the running agent. This will be picked up on the next
                      iteration.
                    </div>
                    <textarea
                      value={guidanceContent}
                      onChange={(e) => setGuidanceContent(e.target.value)}
                      className="flex-1 p-3 bg-zinc-950 border border-zinc-700 rounded-lg text-zinc-300 text-sm resize-none focus:outline-none focus:border-blue-500"
                      placeholder="Enter guidance for the agent..."
                    />
                    <button
                      onClick={handleInjectGuidance}
                      disabled={!guidanceContent.trim()}
                      className="mt-3 flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Syringe className="w-4 h-4" />
                      Inject Guidance
                    </button>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="p-4 border-t border-zinc-700 flex items-center gap-2">
                {selectedAgent.status === 'running' ? (
                  <button
                    onClick={handlePause}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg transition-colors"
                  >
                    <Pause className="w-4 h-4" />
                    Pause
                  </button>
                ) : selectedAgent.status === 'paused' ? (
                  <button
                    onClick={handleResume}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                  >
                    <Play className="w-4 h-4" />
                    Resume
                  </button>
                ) : null}
                <button
                  onClick={handleKill}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                >
                  <Square className="w-4 h-4" />
                  Kill
                </button>
              </div>
            </>
          )}

          {/* State File Content */}
          {selectedType === 'stateFile' && selectedStateFile && (
            <>
              <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800">
                <span className="text-xs text-zinc-500">
                  Last modified:{' '}
                  {selectedStateFile.lastModified
                    ? new Date(selectedStateFile.lastModified).toLocaleString()
                    : 'Never'}
                </span>
                <button
                  onClick={handleSaveStateFile}
                  disabled={isSaving}
                  className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50"
                >
                  <Save className="w-3 h-3" />
                  {isSaving ? 'Saving...' : 'Save'}
                </button>
              </div>
              <textarea
                value={stateFileContent}
                onChange={(e) => setStateFileContent(e.target.value)}
                className="flex-1 p-4 bg-zinc-950 text-zinc-300 text-sm font-mono resize-none focus:outline-none"
                placeholder="File content..."
              />
            </>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

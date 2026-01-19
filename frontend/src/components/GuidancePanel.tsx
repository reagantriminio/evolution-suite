import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, ChevronDown, FileText, Save, Plus } from 'lucide-react';
import { useAgentStore } from '@/stores/agentStore';
import * as api from '@/lib/api';
import clsx from 'clsx';

const presets = [
  { name: 'Focus on security', content: 'Prioritize finding and fixing security vulnerabilities. Look for XSS, SQL injection, and authentication issues.' },
  { name: 'Prioritize tests', content: 'Focus on improving test coverage. Write tests before making changes.' },
  { name: 'Performance mode', content: 'Look for performance bottlenecks. Optimize database queries, reduce memory usage, and improve response times.' },
  { name: 'Code cleanup', content: 'Focus on code quality. Remove dead code, fix lint issues, and improve naming.' },
];

export function GuidancePanel() {
  const { agents, prompts, selectedAgentId } = useAgentStore();
  const [activeTab, setActiveTab] = useState<'inject' | 'prompts'>('inject');
  const [guidance, setGuidance] = useState('');
  const [targetAgentId, setTargetAgentId] = useState<string | null>(null);
  const [editingPrompt, setEditingPrompt] = useState<string | null>(null);
  const [promptContent, setPromptContent] = useState('');

  const agentList = Object.values(agents);
  const effectiveTarget = targetAgentId || selectedAgentId;

  const handleInject = async () => {
    if (!guidance.trim() || !effectiveTarget) return;
    try {
      await api.injectGuidance(effectiveTarget, guidance);
      setGuidance('');
    } catch (error) {
      console.error('Failed to inject:', error);
    }
  };

  const handlePresetClick = (content: string) => {
    setGuidance(content);
  };

  const handleEditPrompt = (name: string) => {
    const prompt = prompts[name];
    if (prompt) {
      setEditingPrompt(name);
      setPromptContent(prompt.content);
    }
  };

  const handleSavePrompt = async () => {
    if (!editingPrompt || !promptContent.trim()) return;
    try {
      await api.updatePrompt(editingPrompt, promptContent);
      setEditingPrompt(null);
      setPromptContent('');
    } catch (error) {
      console.error('Failed to save prompt:', error);
    }
  };

  return (
    <div className="h-full flex flex-col bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
      {/* Tabs */}
      <div className="flex border-b border-zinc-800">
        <button
          onClick={() => setActiveTab('inject')}
          className={clsx(
            'flex-1 px-4 py-3 text-sm font-medium transition-colors',
            activeTab === 'inject'
              ? 'text-zinc-100 border-b-2 border-zinc-100'
              : 'text-zinc-500 hover:text-zinc-300'
          )}
        >
          Guidance
        </button>
        <button
          onClick={() => setActiveTab('prompts')}
          className={clsx(
            'flex-1 px-4 py-3 text-sm font-medium transition-colors',
            activeTab === 'prompts'
              ? 'text-zinc-100 border-b-2 border-zinc-100'
              : 'text-zinc-500 hover:text-zinc-300'
          )}
        >
          Prompts
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <AnimatePresence mode="wait">
          {activeTab === 'inject' ? (
            <motion.div
              key="inject"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="h-full flex flex-col p-4"
            >
              {/* Target selector */}
              <div className="mb-3">
                <label className="text-xs text-zinc-500 mb-1 block">
                  Inject to:
                </label>
                <div className="relative">
                  <select
                    value={effectiveTarget ?? ''}
                    onChange={(e) => setTargetAgentId(e.target.value || null)}
                    className="w-full appearance-none pl-3 pr-8 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded focus:outline-none focus:border-zinc-600"
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

              {/* Guidance input */}
              <div className="flex-1 mb-3">
                <textarea
                  value={guidance}
                  onChange={(e) => setGuidance(e.target.value)}
                  placeholder="Enter guidance for the agent..."
                  className="w-full h-full px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded resize-none focus:outline-none focus:border-zinc-600"
                />
              </div>

              {/* Inject button */}
              <button
                onClick={handleInject}
                disabled={!guidance.trim() || !effectiveTarget}
                className="flex items-center justify-center gap-2 w-full py-2 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed rounded border border-zinc-700 transition-colors"
              >
                <Send className="w-4 h-4" />
                <span className="text-sm">Inject Now</span>
              </button>

              {/* Presets */}
              <div className="mt-4 pt-4 border-t border-zinc-800">
                <h4 className="text-xs text-zinc-500 mb-2">Presets</h4>
                <div className="space-y-1">
                  {presets.map((preset) => (
                    <button
                      key={preset.name}
                      onClick={() => handlePresetClick(preset.content)}
                      className="w-full text-left px-3 py-2 text-sm text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors"
                    >
                      {preset.name}
                    </button>
                  ))}
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="prompts"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="h-full flex flex-col p-4"
            >
              {editingPrompt ? (
                <>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-medium text-zinc-300 capitalize">
                      {editingPrompt}
                    </h4>
                    <button
                      onClick={() => setEditingPrompt(null)}
                      className="text-xs text-zinc-500 hover:text-zinc-300"
                    >
                      Cancel
                    </button>
                  </div>
                  <textarea
                    value={promptContent}
                    onChange={(e) => setPromptContent(e.target.value)}
                    className="flex-1 px-3 py-2 text-sm font-mono bg-zinc-800 border border-zinc-700 rounded resize-none focus:outline-none focus:border-zinc-600"
                  />
                  <button
                    onClick={handleSavePrompt}
                    className="flex items-center justify-center gap-2 mt-3 py-2 bg-zinc-800 hover:bg-zinc-700 rounded border border-zinc-700 transition-colors"
                  >
                    <Save className="w-4 h-4" />
                    <span className="text-sm">Save Changes</span>
                  </button>
                </>
              ) : (
                <div className="space-y-2">
                  {Object.values(prompts).map((prompt) => (
                    <button
                      key={prompt.name}
                      onClick={() => handleEditPrompt(prompt.name)}
                      className="w-full flex items-center gap-3 px-3 py-3 text-left bg-zinc-800 hover:bg-zinc-700 rounded border border-zinc-700 transition-colors"
                    >
                      <FileText className="w-4 h-4 text-zinc-500" />
                      <div className="flex-1">
                        <div className="text-sm font-medium text-zinc-300 capitalize">
                          {prompt.name}
                        </div>
                        <div className="text-xs text-zinc-500">
                          {prompt.isCustom ? 'Custom' : 'Default'}
                        </div>
                      </div>
                    </button>
                  ))}

                  {Object.keys(prompts).length === 0 && (
                    <div className="text-center text-zinc-600 py-8">
                      No prompts loaded
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useInitialData } from '@/hooks/useAgents';
import { Layout } from '@/components/Layout';
import { AgentPool } from '@/components/AgentPool';
import { OutputPanel } from '@/components/OutputPanel';
import { GuidancePanel } from '@/components/GuidancePanel';
import { CycleHistory } from '@/components/CycleHistory';
import { AgentNetworkGraph } from '@/components/AgentNetworkGraph';
import { SlideOutPanel } from '@/components/SlideOutPanel';
import { BulkActionsToolbar } from '@/components/BulkActionsToolbar';
import { UsageDashboard } from '@/components/UsageDashboard';
import { Network, LayoutGrid, BarChart3 } from 'lucide-react';
import type { StateFile, AgentRelationship, Prompt } from '@/lib/types';
import * as api from '@/lib/api';

type ViewMode = 'classic' | 'graph' | 'usage';

function App() {
  // Initialize WebSocket connection
  useWebSocket();

  // Fetch initial data
  useInitialData();

  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('graph');

  // Graph state
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedNodeType, setSelectedNodeType] = useState<'agent' | 'stateFile' | null>(null);
  const [selectedNodes, setSelectedNodes] = useState<string[]>([]);
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  // Data state
  const [stateFiles, setStateFiles] = useState<StateFile[]>([]);
  const [relationships, setRelationships] = useState<AgentRelationship[]>([]);
  const [prompts, setPrompts] = useState<Prompt[]>([]);

  // Fetch state files
  const fetchStateFiles = useCallback(async () => {
    try {
      const { files } = await api.listStateFiles();
      setStateFiles(files);
    } catch (error) {
      console.error('Failed to fetch state files:', error);
    }
  }, []);

  // Fetch relationships
  const fetchRelationships = useCallback(async () => {
    try {
      const { relationships: rels } = await api.listRelationships();
      setRelationships(rels);
    } catch (error) {
      console.error('Failed to fetch relationships:', error);
    }
  }, []);

  // Fetch prompts
  const fetchPrompts = useCallback(async () => {
    try {
      const { prompts: p } = await api.listPrompts();
      setPrompts(p);
    } catch (error) {
      console.error('Failed to fetch prompts:', error);
    }
  }, []);

  // Initial data fetch
  useEffect(() => {
    fetchStateFiles();
    fetchRelationships();
    fetchPrompts();

    // Refresh periodically
    const interval = setInterval(() => {
      fetchStateFiles();
      fetchRelationships();
    }, 5000);

    return () => clearInterval(interval);
  }, [fetchStateFiles, fetchRelationships, fetchPrompts]);

  // Handle node selection
  const handleNodeSelect = useCallback((nodeId: string, nodeType: 'agent' | 'stateFile') => {
    setSelectedNodeId(nodeId);
    setSelectedNodeType(nodeType);
    setIsPanelOpen(true);
  }, []);

  // Handle multi-selection change
  const handleSelectionChange = useCallback((nodeIds: string[]) => {
    setSelectedNodes(nodeIds);
  }, []);

  // Handle panel close
  const handlePanelClose = useCallback(() => {
    setIsPanelOpen(false);
    setSelectedNodeId(null);
    setSelectedNodeType(null);
  }, []);

  // Handle prompt update
  const handlePromptUpdate = useCallback((name: string, content: string) => {
    setPrompts((prev) =>
      prev.map((p) => (p.name === name ? { ...p, content, isCustom: true } : p))
    );
  }, []);

  // Clear multi-selection
  const handleClearSelection = useCallback(() => {
    setSelectedNodes([]);
  }, []);

  // Handle action complete (refresh data)
  const handleActionComplete = useCallback(() => {
    fetchRelationships();
    fetchStateFiles();
  }, [fetchRelationships, fetchStateFiles]);

  return (
    <Layout>
      {/* View Mode Tabs */}
      <div className="flex items-center gap-2 mb-4">
        <div className="flex items-center bg-zinc-900 rounded-lg p-1 border border-zinc-800">
          <button
            onClick={() => setViewMode('classic')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-colors ${
              viewMode === 'classic'
                ? 'bg-zinc-700 text-zinc-100'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <LayoutGrid className="w-4 h-4" />
            Classic
          </button>
          <button
            onClick={() => setViewMode('graph')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-colors ${
              viewMode === 'graph'
                ? 'bg-zinc-700 text-zinc-100'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Network className="w-4 h-4" />
            Network
          </button>
          <button
            onClick={() => setViewMode('usage')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-colors ${
              viewMode === 'usage'
                ? 'bg-zinc-700 text-zinc-100'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            Usage
          </button>
        </div>
      </div>

      {/* Classic View */}
      {viewMode === 'classic' && (
        <div className="flex flex-col h-full gap-4">
          {/* Top section: Agent Pool */}
          <section className="flex-shrink-0">
            <AgentPool />
          </section>

          {/* Middle section: Output + Guidance */}
          <section className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0">
            <div className="lg:col-span-2 min-h-0">
              <OutputPanel />
            </div>
            <div className="min-h-0">
              <GuidancePanel />
            </div>
          </section>

          {/* Bottom section: Cycle History */}
          <section className="flex-shrink-0 h-48">
            <CycleHistory />
          </section>
        </div>
      )}

      {/* Graph View */}
      {viewMode === 'graph' && (
        <div className="flex flex-col h-[calc(100vh-180px)] gap-4">
          {/* Graph */}
          <section className="flex-1 min-h-0">
            <AgentNetworkGraph
              onNodeSelect={handleNodeSelect}
              selectedNodes={selectedNodes}
              onSelectionChange={handleSelectionChange}
              stateFiles={stateFiles}
              relationships={relationships}
            />
          </section>

          {/* Bottom section: Cycle History */}
          <section className="flex-shrink-0 h-40">
            <CycleHistory />
          </section>
        </div>
      )}

      {/* Usage View */}
      {viewMode === 'usage' && (
        <UsageDashboard isVisible={viewMode === 'usage'} />
      )}

      {/* Bulk Actions Toolbar */}
      <BulkActionsToolbar
        selectedIds={selectedNodes}
        onClearSelection={handleClearSelection}
        onActionComplete={handleActionComplete}
      />

      {/* Slide-out Panel */}
      <SlideOutPanel
        isOpen={isPanelOpen}
        onClose={handlePanelClose}
        selectedId={selectedNodeId}
        selectedType={selectedNodeType}
        stateFiles={stateFiles}
        prompts={prompts}
        onPromptUpdate={handlePromptUpdate}
      />
    </Layout>
  );
}

export default App;

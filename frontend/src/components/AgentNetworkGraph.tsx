import { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  Position,
  MarkerType,
  NodeProps,
  Handle,
  SelectionMode,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { motion } from 'framer-motion';
import { FileText, Users } from 'lucide-react';
import { useAgentStore } from '@/stores/agentStore';
import type { Agent, AgentType, StateFile, AgentRelationship } from '@/lib/types';

// Lane configuration - wider spacing for larger nodes
const LANES = {
  coordinator: { x: 50, label: 'Coordinators', color: '#6366f1' },
  stateFiles: { x: 380, label: 'State Files', color: '#8b5cf6' },
  worker: { x: 580, label: 'Workers', color: '#22c55e' },
  evaluator: { x: 910, label: 'Evaluators', color: '#f59e0b' },
};

const NODE_HEIGHT = 180;  // Taller nodes to accommodate goal
const NODE_SPACING = 30;

// Status colors
const STATUS_COLORS: Record<string, string> = {
  idle: '#6b7280',
  starting: '#eab308',
  running: '#22c55e',
  paused: '#f59e0b',
  stopping: '#f97316',
  stopped: '#6b7280',
  failed: '#ef4444',
};

// Type colors for borders
const TYPE_COLORS: Record<string, string> = {
  coordinator: '#6366f1',
  worker: '#22c55e',
  evaluator: '#f59e0b',
};

// Custom Agent Node
function AgentNode({ data, selected }: NodeProps) {
  const agent = data.agent as Agent;
  const statusColor = STATUS_COLORS[agent.status] || '#6b7280';
  const typeColor = TYPE_COLORS[agent.type] || '#6b7280';

  return (
    <div
      className={`
        bg-zinc-900 border-2 rounded-lg p-3 min-w-[220px] max-w-[280px] transition-all shadow-lg
        ${selected ? 'ring-2 ring-blue-500/40' : ''}
        hover:shadow-xl
      `}
      style={{ borderColor: typeColor }}
    >
      <Handle type="target" position={Position.Left} className="!bg-zinc-400 !w-3 !h-3" />
      <Handle type="source" position={Position.Right} className="!bg-zinc-400 !w-3 !h-3" />

      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <motion.div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: statusColor }}
            animate={agent.status === 'running' ? { scale: [1, 1.3, 1] } : {}}
            transition={{ repeat: Infinity, duration: 1 }}
          />
          <span
            className="text-sm font-bold uppercase"
            style={{ color: typeColor }}
          >
            {agent.type}
          </span>
        </div>
        <span className="text-xs text-zinc-400 font-mono bg-zinc-800 px-1.5 py-0.5 rounded">
          {agent.id.split('-')[1]}
        </span>
      </div>

      {/* Goal - prominently displayed */}
      {agent.goal && (
        <div
          className="text-sm text-zinc-200 mb-2 p-2 bg-zinc-800/70 rounded border-l-2"
          style={{ borderLeftColor: typeColor }}
          title={agent.goal}
        >
          <div className="text-[10px] uppercase text-zinc-500 mb-0.5 font-medium">Goal</div>
          <div className="line-clamp-2">{agent.goal}</div>
        </div>
      )}

      {/* Status badge */}
      <div className="flex items-center gap-2 mb-2">
        <span
          className="text-xs px-2 py-0.5 rounded-full font-medium"
          style={{
            backgroundColor: statusColor + '20',
            color: statusColor
          }}
        >
          {agent.status}
        </span>
        {agent.error && (
          <span className="text-xs text-red-400 truncate" title={agent.error}>
            Error
          </span>
        )}
      </div>

      {/* Stats */}
      <div className="flex items-center gap-3 text-xs text-zinc-400">
        <span title="Tools used">{agent.toolsUsed} tools</span>
        <span title="Files modified">{agent.filesModified.length} files</span>
        <span title="Output lines">{agent.outputLines} lines</span>
      </div>

      {/* Usage cost if available */}
      {agent.usage && agent.usage.costUsd > 0 && (
        <div className="mt-2 text-xs text-emerald-400 font-mono">
          ${agent.usage.costUsd.toFixed(4)}
        </div>
      )}

      {/* Waiting indicator */}
      {agent.waitingFor && (
        <div className="mt-2 text-xs text-orange-400 flex items-center gap-1">
          <span className="animate-pulse">⏳ Waiting...</span>
        </div>
      )}
    </div>
  );
}

// Custom State File Node
function StateFileNode({ data, selected }: NodeProps) {
  const file = data.file as StateFile;

  return (
    <div
      className={`
        bg-zinc-800/50 border border-dashed rounded-lg p-3 min-w-[140px] transition-all
        ${selected ? 'border-purple-500 ring-2 ring-purple-500/20' : 'border-zinc-600'}
        hover:border-zinc-500
      `}
    >
      <Handle type="target" position={Position.Left} className="!bg-purple-500" />
      <Handle type="source" position={Position.Right} className="!bg-purple-500" />

      <div className="flex items-center gap-2 mb-1">
        <FileText className="w-4 h-4 text-purple-400" />
        <span className="text-xs font-medium text-zinc-300">{file.name}</span>
      </div>

      {file.lockedBy && (
        <div className="text-xs text-orange-400 mt-1">
          Locked by: {file.lockedBy}
        </div>
      )}

      <div className="text-xs text-zinc-500 mt-1">
        {file.lastModified
          ? new Date(file.lastModified).toLocaleTimeString()
          : 'No modifications'}
      </div>
    </div>
  );
}

// Lane Header Component
function LaneHeader({ label, color, count }: { label: string; color: string; count: number }) {
  return (
    <div
      className="absolute top-0 px-3 py-1.5 rounded-b-lg text-xs font-medium"
      style={{ backgroundColor: color + '20', color }}
    >
      {label} ({count})
    </div>
  );
}

// Node types for React Flow
const nodeTypes = {
  agent: AgentNode,
  stateFile: StateFileNode,
};

interface AgentNetworkGraphProps {
  onNodeSelect: (nodeId: string, nodeType: 'agent' | 'stateFile') => void;
  selectedNodes: string[];
  onSelectionChange: (nodeIds: string[]) => void;
  stateFiles: StateFile[];
  relationships: AgentRelationship[];
}

// Inner component that uses React Flow hooks (must be inside ReactFlowProvider)
function FlowGraph({
  onNodeSelect,
  selectedNodes,
  onSelectionChange,
  stateFiles,
  relationships,
}: AgentNetworkGraphProps) {
  const { agents } = useAgentStore();
  const agentsList = Object.values(agents);

  // Build nodes
  const nodes = useMemo(() => {
    const result: Node[] = [];

    // Agent nodes by type
    const agentsByType: Record<AgentType, Agent[]> = {
      coordinator: [],
      worker: [],
      evaluator: [],
    };

    agentsList.forEach((agent) => {
      agentsByType[agent.type].push(agent);
    });

    // Position agents in their lanes
    Object.entries(agentsByType).forEach(([type, typeAgents]) => {
      const lane = LANES[type as keyof typeof LANES];
      if (!lane) return;

      typeAgents.forEach((agent, index) => {
        result.push({
          id: agent.id,
          type: 'agent',
          position: { x: lane.x, y: 80 + index * (NODE_HEIGHT + NODE_SPACING) },
          data: { agent },
          selected: selectedNodes.includes(agent.id),
        });
      });
    });

    // State file nodes
    stateFiles.forEach((file, index) => {
      result.push({
        id: `file-${file.path}`,
        type: 'stateFile',
        position: { x: LANES.stateFiles.x, y: 80 + index * (80 + NODE_SPACING) },
        data: { file },
        selected: selectedNodes.includes(`file-${file.path}`),
      });
    });

    return result;
  }, [agentsList, stateFiles, selectedNodes]);

  // Build edges from relationships
  const edges = useMemo(() => {
    const result: Edge[] = [];

    relationships.forEach((rel, index) => {
      let strokeColor = '#6b7280';
      let animated = false;
      let strokeDasharray = undefined;

      switch (rel.type) {
        case 'delegation':
          strokeColor = '#3b82f6';
          animated = true;
          break;
        case 'waiting':
          strokeColor = '#f97316';
          animated = true;
          break;
        case 'data_flow':
          strokeColor = '#22c55e';
          animated = true;
          break;
        case 'completed':
          strokeColor = '#6b7280';
          strokeDasharray = '5 5';
          break;
      }

      result.push({
        id: `edge-${index}`,
        source: rel.sourceId,
        target: rel.targetId,
        animated,
        style: { stroke: strokeColor, strokeWidth: 2, strokeDasharray },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: strokeColor,
        },
        label: rel.taskDescription?.slice(0, 20),
        labelStyle: { fill: '#9ca3af', fontSize: 10 },
      });
    });

    // Add implicit connections to state files for active agents
    agentsList.forEach((agent) => {
      if (agent.status === 'running' || agent.status === 'starting') {
        stateFiles.forEach((file) => {
          if (file.name.includes('STATE') || file.name.includes('LOCK')) {
            result.push({
              id: `state-${agent.id}-${file.path}`,
              source: agent.id,
              target: `file-${file.path}`,
              animated: agent.status === 'running',
              style: { stroke: '#8b5cf6', strokeWidth: 1, opacity: 0.5 },
            });
          }
        });
      }
    });

    return result;
  }, [relationships, agentsList, stateFiles]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const nodeType = node.type === 'stateFile' ? 'stateFile' : 'agent';
      const nodeId = nodeType === 'stateFile'
        ? node.id.replace('file-', '')
        : node.id;
      onNodeSelect(nodeId, nodeType);
    },
    [onNodeSelect]
  );

  const onSelectionChangeHandler = useCallback(
    ({ nodes: selectedNodesList }: { nodes: Node[] }) => {
      onSelectionChange(selectedNodesList.map((n) => n.id));
    },
    [onSelectionChange]
  );

  // Count agents by type
  const counts = useMemo(() => ({
    coordinator: agentsList.filter((a) => a.type === 'coordinator').length,
    worker: agentsList.filter((a) => a.type === 'worker').length,
    evaluator: agentsList.filter((a) => a.type === 'evaluator').length,
    stateFiles: stateFiles.length,
  }), [agentsList, stateFiles]);

  return (
    <div className="h-full w-full relative bg-zinc-950 rounded-lg overflow-hidden" style={{ minHeight: '400px' }}>
      {/* Lane Headers - positioned absolutely */}
      <div className="absolute top-0 left-0 right-0 z-10 pointer-events-none">
        <div className="absolute" style={{ left: LANES.coordinator.x + 60 }}>
          <LaneHeader label="Coordinators" color={LANES.coordinator.color} count={counts.coordinator} />
        </div>
        <div className="absolute" style={{ left: LANES.stateFiles.x + 20 }}>
          <LaneHeader label="State Files" color={LANES.stateFiles.color} count={counts.stateFiles} />
        </div>
        <div className="absolute" style={{ left: LANES.worker.x + 80 }}>
          <LaneHeader label="Workers" color={LANES.worker.color} count={counts.worker} />
        </div>
        <div className="absolute" style={{ left: LANES.evaluator.x + 60 }}>
          <LaneHeader label="Evaluators" color={LANES.evaluator.color} count={counts.evaluator} />
        </div>
      </div>

      {/* Lane Dividers */}
      <svg className="absolute inset-0 pointer-events-none z-0" width="100%" height="100%">
        {[LANES.stateFiles.x - 30, LANES.worker.x - 30, LANES.evaluator.x - 30].map((x, i) => (
          <line
            key={i}
            x1={x}
            y1={0}
            x2={x}
            y2="100%"
            stroke="#27272a"
            strokeDasharray="4 4"
          />
        ))}
      </svg>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodeClick={onNodeClick}
        onSelectionChange={onSelectionChangeHandler}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        selectionOnDrag
        selectNodesOnDrag
        selectionMode={SelectionMode.Partial}
        className="bg-zinc-950"
        proOptions={{ hideAttribution: true }}
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        nodesDraggable={true}
        nodesConnectable={false}
        elementsSelectable={true}
      >
        <Background color="#27272a" gap={20} />
        <Controls className="!bg-zinc-800 !border-zinc-700 !rounded-lg [&>button]:!bg-zinc-800 [&>button]:!border-zinc-700 [&>button]:!text-zinc-400 [&>button:hover]:!bg-zinc-700" />
        <MiniMap
          nodeColor={(node) => {
            if (node.type === 'stateFile') return LANES.stateFiles.color;
            const agent = node.data?.agent as Agent;
            return LANES[agent?.type as keyof typeof LANES]?.color || '#6b7280';
          }}
          className="!bg-zinc-900 !border-zinc-700 !rounded-lg"
        />
      </ReactFlow>

      {/* Empty State */}
      {agentsList.length === 0 && stateFiles.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center text-zinc-500">
            <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No agents or state files</p>
            <p className="text-xs mt-1">Spawn agents to see them here</p>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-zinc-900/90 border border-zinc-700 rounded-lg p-3 text-xs z-10">
        <div className="font-medium text-zinc-300 mb-2">Edge Types</div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-blue-500" />
            <span className="text-zinc-400">Delegation</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-orange-500" />
            <span className="text-zinc-400">Waiting</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-green-500" />
            <span className="text-zinc-400">Data Flow</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-zinc-500 border-dashed" style={{ borderTopWidth: 2, borderTopStyle: 'dashed' }} />
            <span className="text-zinc-400">Completed</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Outer component that provides the ReactFlowProvider context
export function AgentNetworkGraph(props: AgentNetworkGraphProps) {
  return (
    <ReactFlowProvider>
      <FlowGraph {...props} />
    </ReactFlowProvider>
  );
}

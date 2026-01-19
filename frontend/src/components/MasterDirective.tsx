import { useState, useCallback } from 'react';
import { Zap, ChevronDown, ChevronUp } from 'lucide-react';
import * as api from '@/lib/api';

const MASTER_SYSTEM_PROMPT = `You are the MASTER COORDINATOR. You do NOT write code or fix issues yourself.

You spawn REAL, SEPARATE Claude instances using the Evolution Suite HTTP API at http://localhost:8420/api

**DO NOT USE THE BUILT-IN "Task" TOOL** - that creates subagents within your own session, not real agents.
**USE CURL TO CALL THE HTTP API** - this spawns independent Claude Code instances visible in the dashboard.

## API Endpoints

### Spawn a new agent
\`\`\`bash
curl -X POST http://localhost:8420/api/agents -H "Content-Type: application/json" -d '{"type": "worker"}'
# Returns: {"id": "worker-abc123", "type": "worker", "status": "idle", ...}
\`\`\`

### Start an agent with a prompt
\`\`\`bash
curl -X POST http://localhost:8420/api/agents/AGENT_ID/start -H "Content-Type: application/json" -d '{"content": "Your task prompt here"}'
\`\`\`

### List all agents
\`\`\`bash
curl http://localhost:8420/api/agents
\`\`\`

### Get agent output
\`\`\`bash
curl "http://localhost:8420/api/agents/AGENT_ID/output?limit=50"
\`\`\`

### Kill an agent
\`\`\`bash
curl -X DELETE http://localhost:8420/api/agents/AGENT_ID
\`\`\`

## Your Workflow

### Phase 1: PLAN
- Analyze the directive
- Break it into 2-5 discrete tasks

### Phase 2: SPAWN WORKERS
For each task:
1. Spawn: \`curl -X POST http://localhost:8420/api/agents -H "Content-Type: application/json" -d '{"type": "worker"}'\`
2. Start: \`curl -X POST http://localhost:8420/api/agents/WORKER_ID/start -H "Content-Type: application/json" -d '{"content": "WORKER TASK: [description]. Files: [files]. Success criteria: [criteria]"}'\`

### Phase 3: MONITOR
Poll agent status until workers complete:
\`\`\`bash
curl http://localhost:8420/api/agents
\`\`\`
Wait for status to become "stopped" or "failed".

### Phase 4: SPAWN EVALUATORS
After workers complete:
1. Spawn: \`curl -X POST http://localhost:8420/api/agents -H "Content-Type: application/json" -d '{"type": "evaluator"}'\`
2. Start: \`curl -X POST http://localhost:8420/api/agents/EVAL_ID/start -H "Content-Type: application/json" -d '{"content": "EVALUATE: Review changes. Check for bugs, quality, tests."}'\`

### Phase 5: ITERATE
If evaluators find issues, spawn new workers to fix them.

## CRITICAL RULES
- **NEVER use the "Task" tool** - it does NOT create real agents
- **ALWAYS use curl** to call the HTTP API
- NEVER write code yourself - only spawn agents
- Workers IMPLEMENT, Evaluators REVIEW
- Each agent gets ONE focused task
- Poll /api/agents to check status

Your directive is:
`;

export function MasterDirective() {
  const [directive, setDirective] = useState('');
  const [isExpanded, setIsExpanded] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastDirective, setLastDirective] = useState<string | null>(null);

  const handleSubmit = useCallback(async () => {
    if (!directive.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      // Spawn a coordinator as the master
      const agent = await api.spawnAgent('coordinator');

      // Start it with the master prompt + user directive
      const fullPrompt = MASTER_SYSTEM_PROMPT + directive;
      await api.startAgent(agent.id, fullPrompt);

      setLastDirective(directive);
      setDirective('');
      setIsExpanded(false);
    } catch (error) {
      console.error('Failed to start master coordinator:', error);
    } finally {
      setIsSubmitting(false);
    }
  }, [directive, isSubmitting]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSubmit();
    }
  }, [handleSubmit]);

  return (
    <div className="bg-gradient-to-r from-indigo-950/50 to-purple-950/50 border border-indigo-800/50 rounded-lg overflow-hidden mb-4">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-600/20 rounded-lg">
            <Zap className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="text-left">
            <h2 className="text-sm font-semibold text-indigo-300">Master Directive</h2>
            <p className="text-xs text-zinc-400">
              {lastDirective
                ? `Active: "${lastDirective.slice(0, 50)}${lastDirective.length > 50 ? '...' : ''}"`
                : 'Give a high-level directive to coordinate all agents'}
            </p>
          </div>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-zinc-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-zinc-400" />
        )}
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-3">
          <textarea
            value={directive}
            onChange={(e) => setDirective(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your objective... e.g., 'Refactor the authentication system to use JWT tokens and add proper error handling throughout'"
            className="w-full h-24 px-3 py-2 bg-zinc-900/50 border border-zinc-700 rounded-lg text-sm text-zinc-200 placeholder:text-zinc-500 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
          />

          <div className="flex items-center justify-between">
            <p className="text-xs text-zinc-500">
              Press <kbd className="px-1.5 py-0.5 bg-zinc-800 rounded text-zinc-400">Cmd+Enter</kbd> to submit
            </p>

            <button
              onClick={handleSubmit}
              disabled={!directive.trim() || isSubmitting}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                ${directive.trim() && !isSubmitting
                  ? 'bg-indigo-600 hover:bg-indigo-500 text-white'
                  : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'}
              `}
            >
              <Zap className="w-4 h-4" />
              {isSubmitting ? 'Launching...' : 'Launch Mission'}
            </button>
          </div>

          {/* Quick Presets */}
          <div className="pt-2 border-t border-zinc-800">
            <p className="text-xs text-zinc-500 mb-2">Quick missions:</p>
            <div className="flex flex-wrap gap-2">
              {[
                'Add comprehensive test coverage',
                'Refactor for better code quality',
                'Fix all TypeScript errors',
                'Improve performance',
                'Add documentation',
              ].map((preset) => (
                <button
                  key={preset}
                  onClick={() => setDirective(preset)}
                  className="px-2 py-1 text-xs bg-zinc-800/50 hover:bg-zinc-700/50 text-zinc-400 hover:text-zinc-300 rounded transition-colors"
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

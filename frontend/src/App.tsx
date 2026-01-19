import { useWebSocket } from '@/hooks/useWebSocket';
import { useInitialData } from '@/hooks/useAgents';
import { Layout } from '@/components/Layout';
import { AgentPool } from '@/components/AgentPool';
import { OutputPanel } from '@/components/OutputPanel';
import { GuidancePanel } from '@/components/GuidancePanel';
import { CycleHistory } from '@/components/CycleHistory';

function App() {
  // Initialize WebSocket connection
  useWebSocket();

  // Fetch initial data
  useInitialData();

  return (
    <Layout>
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
    </Layout>
  );
}

export default App;

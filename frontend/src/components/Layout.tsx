import { ReactNode } from 'react';
import { useAgentStore } from '@/stores/agentStore';
import { StatusBar } from './StatusBar';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { connected, running, cycle, phase } = useAgentStore();

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-zinc-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold tracking-tight">
              Evolution Suite
            </h1>
            <StatusBar
              connected={connected}
              running={running}
              cycle={cycle}
              phase={phase}
            />
          </div>
          <div className="flex items-center gap-2">
            <ConnectionIndicator connected={connected} />
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 p-6 overflow-hidden">
        {children}
      </main>
    </div>
  );
}

function ConnectionIndicator({ connected }: { connected: boolean }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <div
        className={`w-2 h-2 rounded-full transition-colors ${
          connected ? 'bg-green-500' : 'bg-red-500'
        }`}
      />
      <span className="text-zinc-400">
        {connected ? 'Connected' : 'Disconnected'}
      </span>
    </div>
  );
}

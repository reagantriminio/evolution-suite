import { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { motion } from 'framer-motion';
import {
  Zap,
  Activity,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Calendar,
  Hash,
} from 'lucide-react';
import { usePersistedState } from '@/hooks/usePersistedState';
import type { UsageHistory } from '@/lib/types';
import * as api from '@/lib/api';

const AGENT_COLORS: Record<string, string> = {
  coordinator: '#6366f1',
  worker: '#22c55e',
  evaluator: '#f59e0b',
};

const MODEL_COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6'];

interface StatCardProps {
  label: string;
  value: string;
  subValue?: string;
  trend?: number;
  icon: React.ReactNode;
  color: string;
}

function StatCard({ label, value, subValue, trend, icon, color }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-zinc-900 border border-zinc-800 rounded-lg p-4"
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-zinc-400 mb-1">{label}</div>
          <div className="text-2xl font-bold" style={{ color }}>
            {value}
          </div>
          {subValue && <div className="text-xs text-zinc-500 mt-1">{subValue}</div>}
        </div>
        <div className="p-2 rounded-lg" style={{ backgroundColor: color + '20' }}>
          {icon}
        </div>
      </div>
      {trend !== undefined && (
        <div className={`flex items-center gap-1 mt-2 text-xs ${trend >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {trend >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          <span>{Math.abs(trend).toFixed(1)}% from yesterday</span>
        </div>
      )}
    </motion.div>
  );
}

interface UsageDashboardProps {
  isVisible: boolean;
}

export function UsageDashboard({ isVisible }: UsageDashboardProps) {
  const [usage, setUsage] = useState<UsageHistory | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [timeRange, setTimeRange] = usePersistedState<7 | 30 | 90>('usage-time-range', 7);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [containerReady, setContainerReady] = useState(false);

  const fetchUsage = async () => {
    setIsLoading(true);
    try {
      const data = await api.getUsage(timeRange);
      setUsage(data);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch usage:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isVisible) {
      fetchUsage();
      // Auto-refresh every 30 seconds
      const interval = setInterval(fetchUsage, 30000);
      return () => clearInterval(interval);
    }
  }, [isVisible, timeRange]);

  // Delay rendering of ResponsiveContainer until parent has computed dimensions
  useEffect(() => {
    const timer = setTimeout(() => setContainerReady(true), 100);
    return () => clearTimeout(timer);
  }, []);

  if (!isVisible) return null;

  const today = usage?.today;
  const history = usage?.history || [];

  // Calculate trends
  const yesterdayUsage = history[1];
  const requestsTrend = today && yesterdayUsage && yesterdayUsage.metrics.requests > 0
    ? ((today.metrics.requests - yesterdayUsage.metrics.requests) / yesterdayUsage.metrics.requests) * 100
    : undefined;

  const tokenTrend = today && yesterdayUsage && (yesterdayUsage.metrics.inputTokens + yesterdayUsage.metrics.outputTokens) > 0
    ? (((today.metrics.inputTokens + today.metrics.outputTokens) -
        (yesterdayUsage.metrics.inputTokens + yesterdayUsage.metrics.outputTokens)) /
        (yesterdayUsage.metrics.inputTokens + yesterdayUsage.metrics.outputTokens)) * 100
    : undefined;

  // Parse date as local time to avoid timezone issues
  const parseLocalDate = (dateStr: string) => {
    const [year, month, day] = dateStr.split('-').map(Number);
    return new Date(year, month - 1, day);
  };

  // Prepare chart data
  const dailyChartData = history.slice(0, timeRange).reverse().map((day) => ({
    date: parseLocalDate(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    inputTokens: day.metrics.inputTokens / 1000,
    outputTokens: day.metrics.outputTokens / 1000,
    requests: day.metrics.requests,
  }));

  // Agent type breakdown (by tokens)
  const agentTypeData = today?.byAgentType
    ? Object.entries(today.byAgentType).map(([type, metrics]) => ({
        name: type.charAt(0).toUpperCase() + type.slice(1),
        value: metrics.inputTokens + metrics.outputTokens,
        requests: metrics.requests,
      }))
    : [];

  // Model breakdown (by tokens)
  const modelData = today?.byModel
    ? Object.entries(today.byModel).map(([model, metrics]) => ({
        name: model.split('-').slice(1, 3).join('-'),
        value: metrics.inputTokens + metrics.outputTokens,
        requests: metrics.requests,
      }))
    : [];

  return (
    <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(100vh-200px)]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-zinc-200">Usage Dashboard</h2>
          <p className="text-sm text-zinc-500">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(Number(e.target.value) as 7 | 30 | 90)}
            className="px-3 py-1.5 bg-zinc-800 border border-zinc-700 rounded text-sm text-zinc-300 focus:outline-none focus:border-blue-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <button
            onClick={fetchUsage}
            disabled={isLoading}
            className="p-2 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          label="Requests Today"
          value={`${today?.metrics.requests || 0}`}
          trend={requestsTrend}
          icon={<Hash className="w-5 h-5 text-emerald-400" />}
          color="#10b981"
        />
        <StatCard
          label="Tokens Today"
          value={`${(((today?.metrics.inputTokens || 0) + (today?.metrics.outputTokens || 0)) / 1000).toFixed(1)}K`}
          subValue={`${((today?.metrics.inputTokens || 0) / 1000).toFixed(1)}K in / ${((today?.metrics.outputTokens || 0) / 1000).toFixed(1)}K out`}
          trend={tokenTrend}
          icon={<Zap className="w-5 h-5 text-yellow-400" />}
          color="#eab308"
        />
        <StatCard
          label="Cycles Today"
          value={`${today?.cycles || 0}`}
          subValue={`${today?.successRate.toFixed(1) || 0}% success rate`}
          icon={<Activity className="w-5 h-5 text-blue-400" />}
          color="#3b82f6"
        />
        <StatCard
          label="Total Requests"
          value={`${usage?.total.requests || 0}`}
          subValue={`${((usage?.total.inputTokens || 0) / 1000000).toFixed(2)}M tokens total`}
          icon={<Calendar className="w-5 h-5 text-purple-400" />}
          color="#8b5cf6"
        />
      </div>

      {/* Daily Usage Chart */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h3 className="text-sm font-medium text-zinc-300 mb-4">Daily Usage</h3>
        <div className="h-64">
          {containerReady && (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dailyChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="date" tick={{ fill: '#71717a', fontSize: 12 }} />
                <YAxis
                  yAxisId="left"
                  tick={{ fill: '#71717a', fontSize: 12 }}
                  label={{ value: 'Tokens (K)', angle: -90, position: 'insideLeft', fill: '#71717a' }}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fill: '#71717a', fontSize: 12 }}
                  label={{ value: 'Requests', angle: 90, position: 'insideRight', fill: '#71717a' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#18181b',
                    border: '1px solid #27272a',
                    borderRadius: '8px',
                  }}
                  labelStyle={{ color: '#d4d4d8' }}
                />
                <Legend />
                <Bar yAxisId="left" dataKey="inputTokens" name="Input (K)" fill="#3b82f6" stackId="tokens" />
                <Bar yAxisId="left" dataKey="outputTokens" name="Output (K)" fill="#8b5cf6" stackId="tokens" />
                <Bar yAxisId="right" dataKey="requests" name="Requests" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Breakdown Charts */}
      <div className="grid grid-cols-2 gap-4">
        {/* By Agent Type */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <h3 className="text-sm font-medium text-zinc-300 mb-4">By Agent Type</h3>
          <div className="h-48">
            {containerReady && agentTypeData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={agentTypeData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={70}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {agentTypeData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={AGENT_COLORS[entry.name.toLowerCase()] || '#6b7280'}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => `${((value as number) / 1000).toFixed(1)}K tokens`}
                    contentStyle={{
                      backgroundColor: '#18181b',
                      border: '1px solid #27272a',
                      borderRadius: '8px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-zinc-500 text-sm">
                No data available
              </div>
            )}
          </div>
        </div>

        {/* By Model */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <h3 className="text-sm font-medium text-zinc-300 mb-4">By Model</h3>
          <div className="h-48">
            {containerReady && modelData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={modelData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={70}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {modelData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={MODEL_COLORS[index % MODEL_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => `${((value as number) / 1000).toFixed(1)}K tokens`}
                    contentStyle={{
                      backgroundColor: '#18181b',
                      border: '1px solid #27272a',
                      borderRadius: '8px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-zinc-500 text-sm">
                No data available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Weekly Table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800">
          <h3 className="text-sm font-medium text-zinc-300">Daily Breakdown</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-zinc-800/50">
              <tr>
                <th className="px-4 py-2 text-left text-zinc-400 font-medium">Date</th>
                <th className="px-4 py-2 text-right text-zinc-400 font-medium">Input Tokens</th>
                <th className="px-4 py-2 text-right text-zinc-400 font-medium">Output Tokens</th>
                <th className="px-4 py-2 text-right text-zinc-400 font-medium">Requests</th>
                <th className="px-4 py-2 text-right text-zinc-400 font-medium">Cycles</th>
                <th className="px-4 py-2 text-right text-zinc-400 font-medium">Success</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {history.slice(0, 7).map((day, index) => (
                <tr key={day.date} className={index === 0 ? 'bg-blue-500/5' : ''}>
                  <td className="px-4 py-2 text-zinc-300">
                    {parseLocalDate(day.date).toLocaleDateString('en-US', {
                      weekday: 'short',
                      month: 'short',
                      day: 'numeric',
                    })}
                    {index === 0 && (
                      <span className="ml-2 text-xs text-blue-400">(Today)</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right text-zinc-300 font-mono">
                    {(day.metrics.inputTokens / 1000).toFixed(1)}K
                  </td>
                  <td className="px-4 py-2 text-right text-zinc-300 font-mono">
                    {(day.metrics.outputTokens / 1000).toFixed(1)}K
                  </td>
                  <td className="px-4 py-2 text-right text-emerald-400 font-mono">
                    {day.metrics.requests}
                  </td>
                  <td className="px-4 py-2 text-right text-zinc-300">{day.cycles}</td>
                  <td className="px-4 py-2 text-right">
                    <span
                      className={`${
                        day.successRate >= 90
                          ? 'text-green-400'
                          : day.successRate >= 70
                          ? 'text-yellow-400'
                          : 'text-red-400'
                      }`}
                    >
                      {day.successRate.toFixed(1)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Live Activity (placeholder) */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-zinc-300">Live Activity</h3>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-xs text-zinc-500">Live</span>
          </div>
        </div>
        <div className="space-y-2 max-h-40 overflow-y-auto">
          <div className="text-sm text-zinc-500 text-center py-4">
            Live activity feed will appear here when agents are running
          </div>
        </div>
      </div>
    </div>
  );
}

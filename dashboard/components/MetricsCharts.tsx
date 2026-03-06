'use client'

import { AreaChart, Area, LineChart, Line, BarChart, Bar, ResponsiveContainer } from 'recharts'
import { TrendingUp } from 'lucide-react'
import { MetricsData } from '@/lib/socket'

interface MetricsChartsProps {
  metricsHistory: MetricsData[]
}

export default function MetricsCharts({ metricsHistory }: MetricsChartsProps) {
  const data = metricsHistory.slice(-20).map((m, i) => ({
    time: i,
    eps: m.events_per_second,
    alerts: m.alerts_generated,
    tasks: m.tasks_running,
    latency: m.avg_execution_time,
  }))

  const latest = metricsHistory[metricsHistory.length - 1]

  return (
    <div className="glass rounded-xl overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-blue-500/20">
        <TrendingUp className="w-4 h-4 text-blue-400" />
        <span className="text-sm font-medium text-white">Framework Metrics</span>
      </div>

      <div className="p-3 space-y-4">
        {/* Stats Row */}
        {latest && (
          <div className="grid grid-cols-4 gap-2">
            {[
              { label: 'Events/s', value: latest.events_per_second, color: 'text-blue-400', unit: '' },
              { label: 'Alerts', value: latest.alerts_generated, color: 'text-red-400', unit: '' },
              { label: 'Tasks', value: latest.tasks_running, color: 'text-yellow-400', unit: '' },
              { label: 'Avg ms', value: latest.avg_execution_time, color: 'text-green-400', unit: 'ms' },
            ].map(stat => (
              <div key={stat.label} className="bg-slate-900/50 rounded-lg p-2 text-center">
                <div className={`text-lg font-bold font-mono ${stat.color}`}>
                  {stat.value}{stat.unit}
                </div>
                <div className="text-xs text-slate-500">{stat.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Events Per Second Chart */}
        <div>
          <div className="text-xs text-slate-500 mb-1">Events Per Second</div>
          <ResponsiveContainer width="100%" height={60}>
            <AreaChart data={data}>
              <defs>
                <linearGradient id="epsGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="eps" stroke="#3b82f6" fill="url(#epsGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Tasks Running Chart */}
        <div>
          <div className="text-xs text-slate-500 mb-1">Tasks Running</div>
          <ResponsiveContainer width="100%" height={60}>
            <BarChart data={data}>
              <Bar dataKey="tasks" fill="#f59e0b" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Execution Time Chart */}
        <div>
          <div className="text-xs text-slate-500 mb-1">Avg Execution Time (ms)</div>
          <ResponsiveContainer width="100%" height={60}>
            <LineChart data={data}>
              <Line type="monotone" dataKey="latency" stroke="#22c55e" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

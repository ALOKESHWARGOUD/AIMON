'use client'

import { motion } from 'framer-motion'
import { Search, Globe, Brain, Bell, Activity } from 'lucide-react'
import { ModuleStatusData } from '@/lib/socket'

const moduleIcons = {
  discovery: Search,
  crawler: Globe,
  intelligence: Brain,
  alerts: Bell,
}

const moduleColors = {
  discovery: 'text-green-400 border-green-500/30 bg-green-500/5',
  crawler: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/5',
  intelligence: 'text-yellow-400 border-yellow-500/30 bg-yellow-500/5',
  alerts: 'text-red-400 border-red-500/30 bg-red-500/5',
}

const statusColors = {
  active: 'bg-green-500 text-green-900',
  idle: 'bg-yellow-500 text-yellow-900',
  error: 'bg-red-500 text-red-900',
}

const statusGlow = {
  active: 'shadow-[0_0_8px_rgba(34,197,94,0.6)]',
  idle: 'shadow-[0_0_8px_rgba(245,158,11,0.6)]',
  error: 'shadow-[0_0_8px_rgba(239,68,68,0.6)]',
}

interface ModuleStatusProps {
  modules: ModuleStatusData[]
}

export default function ModuleStatus({ modules }: ModuleStatusProps) {
  return (
    <div className="glass rounded-xl overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-blue-500/20">
        <Activity className="w-4 h-4 text-blue-400" />
        <span className="text-sm font-medium text-white">Module Status</span>
      </div>
      <div className="p-3 grid grid-cols-2 gap-3">
        {modules.map((mod, i) => {
          const Icon = moduleIcons[mod.name as keyof typeof moduleIcons] || Activity
          const colorClass = moduleColors[mod.name as keyof typeof moduleColors] || 'text-blue-400 border-blue-500/30 bg-blue-500/5'

          return (
            <motion.div
              key={mod.name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`rounded-lg border p-3 ${colorClass}`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Icon className="w-4 h-4" />
                  <span className="text-xs font-semibold capitalize">{mod.name}</span>
                </div>
                <div className={`w-2 h-2 rounded-full ${statusColors[mod.status]} ${statusGlow[mod.status]}`} />
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Events</span>
                  <span className="text-slate-300 font-mono">{mod.events_processed.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Tasks</span>
                  <span className="text-slate-300 font-mono">{mod.tasks_running}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Status</span>
                  <span className={`capitalize font-medium ${mod.status === 'active' ? 'text-green-400' : mod.status === 'idle' ? 'text-yellow-400' : 'text-red-400'}`}>
                    {mod.status}
                  </span>
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

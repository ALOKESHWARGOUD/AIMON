'use client'

import { Activity, Shield, Zap, Bell } from 'lucide-react'
import { motion } from 'framer-motion'

interface NavbarProps {
  connected: boolean
  totalEvents: number
  totalThreats: number
}

export default function Navbar({ connected, totalEvents, totalThreats }: NavbarProps) {
  return (
    <motion.nav
      initial={{ y: -50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="glass border-b border-blue-500/20 px-6 py-3 flex items-center justify-between sticky top-0 z-50"
    >
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <Shield className="w-8 h-8 text-blue-500" />
          <motion.div
            animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="absolute inset-0 bg-blue-500/20 rounded-full blur-sm"
          />
        </div>
        <div>
          <span className="text-xl font-bold text-white tracking-wider">AI</span>
          <span className="text-xl font-bold text-blue-500 tracking-wider">MON</span>
          <div className="text-xs text-slate-400 -mt-1">Monitoring Control Center</div>
        </div>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-sm">
          <Zap className="w-4 h-4 text-yellow-500" />
          <span className="text-slate-400">Events:</span>
          <span className="text-white font-mono font-bold">{totalEvents.toLocaleString()}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Bell className="w-4 h-4 text-red-500" />
          <span className="text-slate-400">Threats:</span>
          <span className="text-red-400 font-mono font-bold">{totalThreats}</span>
        </div>
        <div className="flex items-center gap-2">
          <motion.div
            animate={connected ? { scale: [1, 1.3, 1] } : {}}
            transition={{ duration: 1.5, repeat: Infinity }}
            className={`w-2.5 h-2.5 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}
          />
          <span className={`text-sm font-medium ${connected ? 'text-green-400' : 'text-red-400'}`}>
            {connected ? 'LIVE' : 'DEMO'}
          </span>
        </div>
        <Activity className="w-5 h-5 text-blue-400 animate-pulse" />
      </div>
    </motion.nav>
  )
}

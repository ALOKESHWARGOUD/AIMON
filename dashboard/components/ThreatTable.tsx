'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, ExternalLink } from 'lucide-react'
import { ThreatData } from '@/lib/socket'

interface ThreatTableProps {
  threats: ThreatData[]
}

function RiskBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = pct >= 80 ? 'bg-red-500/20 text-red-400 border-red-500/30' :
    pct >= 60 ? 'bg-orange-500/20 text-orange-400 border-orange-500/30' :
    'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
  return (
    <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${color}`}>
      {pct}%
    </span>
  )
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', { hour12: false })
}

export default function ThreatTable({ threats }: ThreatTableProps) {
  return (
    <div className="glass rounded-xl overflow-hidden h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-red-500/20">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-400" />
          <span className="text-sm font-medium text-white">Threat Detection</span>
        </div>
        {threats.length > 0 && (
          <motion.div
            animate={{ opacity: [1, 0.5, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="flex items-center gap-1"
          >
            <div className="w-2 h-2 rounded-full bg-red-500" />
            <span className="text-xs text-red-400 font-mono">{threats.length} detected</span>
          </motion.div>
        )}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto" style={{ minHeight: 0 }}>
        {threats.length === 0 ? (
          <div className="text-slate-600 text-center py-8">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">No threats detected</p>
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-slate-900/90 backdrop-blur">
              <tr className="text-slate-500 uppercase tracking-wider">
                <th className="text-left px-4 py-2">URL</th>
                <th className="text-center px-2 py-2">Risk</th>
                <th className="text-center px-2 py-2">Source</th>
                <th className="text-right px-4 py-2">Time</th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence initial={false}>
                {threats.slice(0, 50).map((threat) => {
                  const isHigh = threat.risk_score >= 0.8
                  return (
                    <motion.tr
                      key={threat.id}
                      initial={{ opacity: 0, backgroundColor: 'rgba(239, 68, 68, 0.2)' }}
                      animate={{ opacity: 1, backgroundColor: isHigh ? 'rgba(239, 68, 68, 0.05)' : 'transparent' }}
                      transition={{ duration: 0.5 }}
                      className={`border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors ${
                        isHigh ? 'border-l-2 border-l-red-500' : ''
                      }`}
                    >
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-1 max-w-[160px]">
                          <span className="truncate text-slate-300">{threat.url}</span>
                          <ExternalLink className="w-3 h-3 text-slate-600 shrink-0" />
                        </div>
                      </td>
                      <td className="px-2 py-2 text-center">
                        <RiskBadge score={threat.risk_score} />
                      </td>
                      <td className="px-2 py-2 text-center">
                        <span className="text-slate-400 capitalize">{threat.source}</span>
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-slate-500">
                        {formatTimestamp(threat.timestamp)}
                      </td>
                    </motion.tr>
                  )
                })}
              </AnimatePresence>
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

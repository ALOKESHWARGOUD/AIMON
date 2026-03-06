'use client'

import { useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Terminal } from 'lucide-react'
import { FrameworkEvent } from '@/lib/socket'

interface EventStreamProps {
  events: FrameworkEvent[]
}

const eventColors: Record<string, string> = {
  search_started: 'text-blue-400',
  source_discovered: 'text-cyan-400',
  page_crawled: 'text-green-400',
  content_analyzed: 'text-yellow-400',
  threat_detected: 'text-red-400',
  alert_generated: 'text-orange-400',
  default: 'text-slate-400',
}

const eventIcons: Record<string, string> = {
  search_started: '🔍',
  source_discovered: '📡',
  page_crawled: '🕷️',
  content_analyzed: '🧠',
  threat_detected: '⚠️',
  alert_generated: '🚨',
  default: '⚡',
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso)
  return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
    '.' + String(date.getMilliseconds()).padStart(3, '0')
}

export default function EventStream({ events }: EventStreamProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  return (
    <div className="glass rounded-xl overflow-hidden h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-blue-500/20">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-medium text-white">Event Stream</span>
        </div>
        <div className="flex items-center gap-2">
          <motion.div
            animate={{ opacity: [1, 0, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
            className="w-2 h-2 rounded-full bg-green-500"
          />
          <span className="text-xs text-slate-400 font-mono">{events.length} events</span>
        </div>
      </div>

      {/* Terminal body */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-3 font-mono text-xs space-y-1 bg-black/30"
        style={{ minHeight: 0 }}
      >
        {events.length === 0 ? (
          <div className="text-slate-600 text-center py-8">
            <Terminal className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p>Waiting for events...</p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {events.slice(0, 100).map((event) => (
              <motion.div
                key={event.id}
                initial={{ opacity: 0, x: -10, backgroundColor: 'rgba(59, 130, 246, 0.1)' }}
                animate={{ opacity: 1, x: 0, backgroundColor: 'transparent' }}
                transition={{ duration: 0.3 }}
                className={`flex items-start gap-2 py-0.5 border-b border-slate-800/50 ${
                  event.type === 'threat_detected' ? 'bg-red-500/5' : ''
                }`}
              >
                <span className="text-slate-600 shrink-0 w-24">{formatTimestamp(event.timestamp)}</span>
                <span className="text-slate-500 shrink-0 w-16">[{event.module.slice(0, 6)}]</span>
                <span className="shrink-0">{eventIcons[event.type] || eventIcons.default}</span>
                <span className={`${eventColors[event.type] || eventColors.default} shrink-0`}>
                  {event.type}
                </span>
                {event.data?.url !== undefined && (
                  <span className="text-slate-500 truncate">{String(event.data.url)}</span>
                )}
                {event.data?.risk_score !== undefined && (
                  <span className="text-red-400 ml-auto shrink-0">
                    risk: {(Number(event.data.risk_score) * 100).toFixed(0)}%
                  </span>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  )
}

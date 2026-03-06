'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import dynamic from 'next/dynamic'
import Navbar from '@/components/Navbar'
import EventStream from '@/components/EventStream'
import ModuleStatus from '@/components/ModuleStatus'
import MetricsCharts from '@/components/MetricsCharts'
import ThreatTable from '@/components/ThreatTable'
import { FrameworkEvent, ThreatData, ModuleStatusData, MetricsData, getSocket, disconnectSocket } from '@/lib/socket'
import { generateMockEvent, generateMockModuleStatus, generateMockMetrics } from '@/lib/api'
import { motion } from 'framer-motion'

// Dynamic import for Three.js component (no SSR)
const Framework3D = dynamic(() => import('@/components/Framework3D'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-slate-500 text-sm">Loading 3D Visualization...</p>
      </div>
    </div>
  ),
})

export default function DashboardPage() {
  const [connected, setConnected] = useState(false)
  const [events, setEvents] = useState<FrameworkEvent[]>([])
  const [threats, setThreats] = useState<ThreatData[]>([])
  const [modules, setModules] = useState<ModuleStatusData[]>(generateMockModuleStatus())
  const [metricsHistory, setMetricsHistory] = useState<MetricsData[]>(() =>
    Array.from({ length: 20 }, () => generateMockMetrics())
  )
  const [activeNodes, setActiveNodes] = useState<string[]>([])
  const demoIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const metricsIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const addEvent = useCallback((event: FrameworkEvent) => {
    setEvents(prev => [event, ...prev].slice(0, 200))

    // Activate node based on module
    const nodeMap: Record<string, string> = {
      discovery: 'discovery',
      crawler: 'crawler',
      intelligence: 'intelligence',
      alerts: 'alerts',
    }
    const nodeId = nodeMap[event.module]
    if (nodeId) {
      setActiveNodes(prev => [...new Set([...prev, nodeId, 'runtime', 'eventbus'])])
      setTimeout(() => {
        setActiveNodes(prev => prev.filter(n => n !== nodeId))
      }, 1500)
    }

    if (event.type === 'threat_detected' && event.data?.url) {
      const threat: ThreatData = {
        id: event.id,
        url: String(event.data.url),
        risk_score: Number(event.data.risk_score) || Math.random() * 0.5 + 0.5,
        source: event.module,
        timestamp: event.timestamp,
      }
      setThreats(prev => [threat, ...prev].slice(0, 100))
    }

    // Update module status
    setModules(prev => prev.map(m =>
      m.name === event.module
        ? { ...m, status: 'active' as const, events_processed: m.events_processed + 1 }
        : m
    ))
  }, [])

  // Try WebSocket connection
  useEffect(() => {
    let socket: ReturnType<typeof getSocket> | null = null

    try {
      socket = getSocket()

      socket.on('connect', () => {
        setConnected(true)
        // Stop demo mode
        if (demoIntervalRef.current) {
          clearInterval(demoIntervalRef.current)
          demoIntervalRef.current = null
        }
      })

      socket.on('disconnect', () => {
        setConnected(false)
      })

      socket.on('event', (data: FrameworkEvent) => {
        addEvent(data)
      })

      socket.on('framework_event', (data: FrameworkEvent) => {
        addEvent(data)
      })
    } catch {
      // WebSocket not available, use demo mode
    }

    return () => {
      if (socket) {
        disconnectSocket()
      }
    }
  }, [addEvent])

  // Demo mode: generate events when not connected
  useEffect(() => {
    if (!connected) {
      demoIntervalRef.current = setInterval(() => {
        const event = generateMockEvent()
        addEvent(event)
      }, 800)
    }
    return () => {
      if (demoIntervalRef.current) {
        clearInterval(demoIntervalRef.current)
      }
    }
  }, [connected, addEvent])

  // Metrics update interval
  useEffect(() => {
    metricsIntervalRef.current = setInterval(() => {
      setMetricsHistory(prev => [...prev, generateMockMetrics()].slice(-50))
    }, 2000)
    return () => {
      if (metricsIntervalRef.current) {
        clearInterval(metricsIntervalRef.current)
      }
    }
  }, [])

  const totalEvents = events.length

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      <Navbar connected={connected} totalEvents={totalEvents} totalThreats={threats.length} />

      {/* Main Grid */}
      <div className="flex-1 p-4 grid grid-cols-1 lg:grid-cols-2 gap-4" style={{ minHeight: 'calc(100vh - 60px)' }}>

        {/* LEFT: 3D Visualization */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="glass rounded-xl overflow-hidden"
          style={{ minHeight: '500px' }}
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-blue-500/20">
            <span className="text-sm font-medium text-white">Framework Architecture</span>
            <span className="text-xs text-slate-500">Click nodes to explore • Drag to rotate</span>
          </div>
          <div style={{ height: 'calc(100% - 48px)' }}>
            <Framework3D activeNodes={activeNodes} />
          </div>
        </motion.div>

        {/* RIGHT: Panels Stack */}
        <div className="flex flex-col gap-4">

          {/* Event Stream */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            style={{ height: '280px' }}
          >
            <EventStream events={events} />
          </motion.div>

          {/* Module Status */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <ModuleStatus modules={modules} />
          </motion.div>

          {/* Metrics Charts */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <MetricsCharts metricsHistory={metricsHistory} />
          </motion.div>
        </div>

        {/* BOTTOM: Threat Table (full width) */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="lg:col-span-2"
          style={{ height: '300px' }}
        >
          <ThreatTable threats={threats} />
        </motion.div>
      </div>
    </div>
  )
}

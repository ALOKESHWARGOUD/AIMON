import { io, Socket } from 'socket.io-client'

export interface FrameworkEvent {
  id: string
  type: string
  module: string
  timestamp: string
  data: Record<string, unknown>
}

export interface ThreatData {
  id: string
  url: string
  risk_score: number
  source: string
  timestamp: string
}

export interface ModuleStatusData {
  name: string
  status: 'active' | 'idle' | 'error'
  events_processed: number
  tasks_running: number
}

export interface MetricsData {
  events_per_second: number
  alerts_generated: number
  tasks_running: number
  avg_execution_time: number
  timestamp: string
}

let socket: Socket | null = null

export function getSocket(url: string = 'http://localhost:8765'): Socket {
  if (!socket) {
    socket = io(url, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
      timeout: 5000,
    })
  }
  return socket
}

export function disconnectSocket(): void {
  if (socket) {
    socket.disconnect()
    socket = null
  }
}

import { FrameworkEvent, ThreatData, ModuleStatusData, MetricsData } from './socket'

// Simulated data generators for demo when no WebSocket server is available
export function generateMockEvent(): FrameworkEvent {
  const eventTypes = [
    'search_started',
    'source_discovered',
    'page_crawled',
    'content_analyzed',
    'threat_detected',
    'alert_generated',
  ]
  const modules = ['discovery', 'crawler', 'intelligence', 'alerts']
  const type = eventTypes[Math.floor(Math.random() * eventTypes.length)]
  const module = modules[Math.floor(Math.random() * modules.length)]

  return {
    id: Math.random().toString(36).slice(2, 11),
    type,
    module,
    timestamp: new Date().toISOString(),
    data: {
      url: type === 'threat_detected' ? `example${Math.floor(Math.random() * 100)}.com/leak` : undefined,
      risk_score: type === 'threat_detected' ? Math.random() : undefined,
      query: type === 'search_started' ? 'course download' : undefined,
      sources_found: type === 'source_discovered' ? Math.floor(Math.random() * 10) + 1 : undefined,
    },
  }
}

export function generateMockThreat(): ThreatData {
  const domains = ['pastebin.com', 'mega.nz', 'mediafire.com', 'dropbox.com', 'telegram.me']
  const sources = ['google', 'reddit', 'telegram', 'torrent']
  return {
    id: Math.random().toString(36).slice(2, 11),
    url: `${domains[Math.floor(Math.random() * domains.length)]}/leak${Math.floor(Math.random() * 1000)}`,
    risk_score: Math.round((0.5 + Math.random() * 0.5) * 100) / 100,
    source: sources[Math.floor(Math.random() * sources.length)],
    timestamp: new Date().toISOString(),
  }
}

export function generateMockModuleStatus(): ModuleStatusData[] {
  const statuses: ('active' | 'idle' | 'error')[] = ['active', 'idle', 'error']
  return ['discovery', 'crawler', 'intelligence', 'alerts'].map(name => ({
    name,
    status: statuses[Math.floor(Math.random() * 2)] as 'active' | 'idle',
    events_processed: Math.floor(Math.random() * 1000),
    tasks_running: Math.floor(Math.random() * 10),
  }))
}

export function generateMockMetrics(): MetricsData {
  return {
    events_per_second: Math.round(Math.random() * 50 + 10),
    alerts_generated: Math.floor(Math.random() * 100),
    tasks_running: Math.floor(Math.random() * 20),
    avg_execution_time: Math.round(Math.random() * 100 + 10),
    timestamp: new Date().toISOString(),
  }
}

# AIMON Monitoring Dashboard

A professional real-time monitoring dashboard for the AIMON AI Monitoring Framework, built as a cyber-security engineering control panel.

## Screenshot

![AIMON Dashboard](https://github.com/user-attachments/assets/1e783d45-d3f0-4ebd-909a-e58fe16c9763)

## Tech Stack

- **Next.js 14** (App Router)
- **TypeScript**
- **TailwindCSS** - Glassmorphism dark-mode design
- **Framer Motion** - Smooth animations
- **Three.js / React Three Fiber / Drei** - 3D architecture visualization
- **Recharts** - Animated metrics charts
- **Lucide React** - Icons
- **socket.io-client** - WebSocket real-time data

## Features

### 3D Framework Visualization
- Interactive 3D architecture diagram with all AIMON nodes: Runtime, EventBus, Discovery, Crawler, Intelligence, Alerts
- Animated glowing connection lines between nodes
- Event particles flowing between nodes
- Nodes pulse and glow when events pass through
- Click any node to open a side panel with component description
- Auto-rotates slowly with drag-to-rotate support

### Real-Time Event Stream
- Terminal-style live event monitor
- Displays: timestamp, module, event type, and data
- Color-coded event types with emoji indicators
- New events appear at the top with smooth animations

### Module Status Panel
- Cards for each AIMON module: Discovery, Crawler, Intelligence, Alerts
- Shows: status (active/idle/error), events processed, tasks running
- Color-coded status indicators with glow effects

### Framework Metrics Charts
- Events per second (area chart)
- Tasks running (bar chart)  
- Average execution time (line chart)
- Live updating stat counters

### Threat Detection Panel
- Table showing detected threats with URL, risk score, source, timestamp
- High-risk rows (≥80%) highlighted in red with animated border
- Real-time updates as threats are detected

## Getting Started

```bash
cd dashboard
npm install
npm run dev
```

Dashboard runs at: **http://localhost:3000**

## Real-Time Data Connection

The dashboard automatically connects to a WebSocket server at `ws://localhost:8765`.

When no server is available, the dashboard runs in **DEMO mode** generating simulated AIMON events.

### WebSocket Event Format

```json
{
  "type": "threat_detected",
  "module": "intelligence",
  "timestamp": "2026-03-06T12:00:00",
  "data": {
    "url": "example.com/leak",
    "risk_score": 0.92
  }
}
```

### Supported Event Types

| Event | Module | Description |
|-------|--------|-------------|
| `search_started` | discovery | New search initiated |
| `source_discovered` | discovery | Data source found |
| `page_crawled` | crawler | Page content extracted |
| `content_analyzed` | intelligence | Content analysis complete |
| `threat_detected` | intelligence | Security threat identified |
| `alert_generated` | alerts | Alert notification sent |

## Visual Design

- **Background**: `#0f172a` (Slate 950)
- **Primary**: `#3b82f6` (Blue 500)
- **Success**: `#22c55e` (Green 500)
- **Alert**: `#ef4444` (Red 500)
- **Warning**: `#f59e0b` (Amber 500)
- Glassmorphism panels with backdrop blur
- Cyber-security command center aesthetic

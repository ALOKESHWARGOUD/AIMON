'use client'

import { useRef, useState, useMemo } from 'react'
import { Canvas, useFrame, ThreeEvent } from '@react-three/fiber'
import { OrbitControls, Text, Sphere, Line } from '@react-three/drei'
import * as THREE from 'three'
import { motion, AnimatePresence } from 'framer-motion'

interface NodeData {
  id: string
  label: string
  position: [number, number, number]
  color: string
  description: string
  connections: string[]
}

const nodes: NodeData[] = [
  {
    id: 'runtime',
    label: 'Runtime',
    position: [0, 2.5, 0],
    color: '#3b82f6',
    description: 'AIMONCoreRuntime: Central orchestrator managing modules, events, and execution. Provides lifecycle management and dependency injection.',
    connections: ['eventbus'],
  },
  {
    id: 'eventbus',
    label: 'Event Bus',
    position: [0, 0.5, 0],
    color: '#8b5cf6',
    description: 'Pub/Sub EventBus: Loose-coupling communication layer. Modules publish and subscribe to events without direct dependencies.',
    connections: ['discovery', 'crawler', 'intelligence', 'alerts'],
  },
  {
    id: 'discovery',
    label: 'Discovery',
    position: [-3, -1.5, 0],
    color: '#22c55e',
    description: 'DiscoveryModule: Searches for data sources across Google, Reddit, Telegram, and Torrent networks. Emits source_discovered events.',
    connections: ['crawler'],
  },
  {
    id: 'crawler',
    label: 'Crawler',
    position: [-1, -1.5, 0],
    color: '#06b6d4',
    description: 'CrawlerModule: Extracts content from discovered sources. Handles HTTP requests, parsing, and deduplication. Emits page_crawled events.',
    connections: ['intelligence'],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    position: [1, -1.5, 0],
    color: '#f59e0b',
    description: 'IntelligenceModule: Analyzes crawled content using fingerprinting algorithms. Detects threats and leaked assets. Emits threat_detected events.',
    connections: ['alerts'],
  },
  {
    id: 'alerts',
    label: 'Alerts',
    position: [3, -1.5, 0],
    color: '#ef4444',
    description: 'AlertsModule: Generates notifications for detected threats. Sends alerts via configured channels (email, webhook, etc). Emits alert_generated events.',
    connections: [],
  },
]

interface NodeMeshProps {
  node: NodeData
  isActive: boolean
  onHover: (id: string | null) => void
  onClick: (id: string) => void
}

function NodeMesh({ node, isActive, onHover, onClick }: NodeMeshProps) {
  const meshRef = useRef<THREE.Mesh>(null)
  const glowRef = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.005
      if (isActive) {
        const scale = 1 + Math.sin(state.clock.elapsedTime * 4) * 0.1
        meshRef.current.scale.setScalar(scale)
      } else {
        meshRef.current.scale.setScalar(1)
      }
    }
    if (glowRef.current) {
      const opacity = isActive
        ? 0.3 + Math.sin(state.clock.elapsedTime * 3) * 0.2
        : 0.1
      ;(glowRef.current.material as THREE.MeshBasicMaterial).opacity = opacity
    }
  })

  const color = new THREE.Color(node.color)

  return (
    <group position={node.position}>
      {/* Glow sphere */}
      <Sphere ref={glowRef} args={[0.45, 16, 16]}>
        <meshBasicMaterial
          color={node.color}
          transparent
          opacity={0.1}
          side={THREE.BackSide}
        />
      </Sphere>

      {/* Main sphere */}
      <Sphere
        ref={meshRef}
        args={[0.3, 32, 32]}
        onPointerOver={(e: ThreeEvent<PointerEvent>) => { e.stopPropagation(); onHover(node.id) }}
        onPointerOut={() => onHover(null)}
        onClick={(e: ThreeEvent<MouseEvent>) => { e.stopPropagation(); onClick(node.id) }}
      >
        <meshStandardMaterial
          color={node.color}
          emissive={color}
          emissiveIntensity={isActive ? 0.8 : 0.3}
          roughness={0.2}
          metalness={0.8}
        />
      </Sphere>

      {/* Label */}
      <Text
        position={[0, -0.55, 0]}
        fontSize={0.18}
        color={node.color}
        anchorX="center"
        anchorY="middle"
      >
        {node.label}
      </Text>
    </group>
  )
}

interface ParticleProps {
  from: [number, number, number]
  to: [number, number, number]
  color: string
  speed?: number
}

function EventParticle({ from, to, color, speed = 1 }: ParticleProps) {
  const meshRef = useRef<THREE.Mesh>(null)
  const progress = useRef(Math.random())

  useFrame((_, delta) => {
    if (meshRef.current) {
      progress.current = (progress.current + delta * speed * 0.5) % 1
      const t = progress.current
      meshRef.current.position.x = from[0] + (to[0] - from[0]) * t
      meshRef.current.position.y = from[1] + (to[1] - from[1]) * t
      meshRef.current.position.z = from[2] + (to[2] - from[2]) * t
    }
  })

  return (
    <Sphere ref={meshRef} args={[0.06, 8, 8]}>
      <meshBasicMaterial color={color} />
    </Sphere>
  )
}

interface ConnectionLineProps {
  from: [number, number, number]
  to: [number, number, number]
  color: string
  active: boolean
}

function ConnectionLine({ from, to, color, active }: ConnectionLineProps) {
  const points = useMemo(() => [new THREE.Vector3(...from), new THREE.Vector3(...to)], [from, to])

  return (
    <Line
      points={points}
      color={active ? color : '#334155'}
      lineWidth={active ? 2 : 1}
      transparent
      opacity={active ? 0.8 : 0.3}
    />
  )
}

interface Framework3DProps {
  activeNodes?: string[]
}

export default function Framework3D({ activeNodes = [] }: Framework3DProps) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<string | null>(null)

  const selectedNodeData = nodes.find(n => n.id === selectedNode)

  const connections = useMemo(() => {
    const conns: Array<{ from: NodeData; to: NodeData }> = []
    nodes.forEach(node => {
      node.connections.forEach(targetId => {
        const target = nodes.find(n => n.id === targetId)
        if (target) conns.push({ from: node, to: target })
      })
    })
    return conns
  }, [])

  return (
    <div className="relative w-full h-full">
      <Canvas camera={{ position: [0, 0, 8], fov: 60 }}>
        <ambientLight intensity={0.3} />
        <pointLight position={[10, 10, 10]} intensity={1} />
        <pointLight position={[-10, -10, -10]} intensity={0.5} color="#3b82f6" />

        {/* Grid */}
        <gridHelper args={[20, 20, '#1e293b', '#1e293b']} position={[0, -3, 0]} />

        {/* Connection Lines */}
        {connections.map((conn, i) => (
          <ConnectionLine
            key={i}
            from={conn.from.position}
            to={conn.to.position}
            color={conn.from.color}
            active={activeNodes.includes(conn.from.id) || activeNodes.includes(conn.to.id)}
          />
        ))}

        {/* Event Particles */}
        {connections.map((conn, i) => (
          <EventParticle
            key={`particle-${i}`}
            from={conn.from.position}
            to={conn.to.position}
            color={conn.from.color}
            speed={activeNodes.includes(conn.from.id) ? 2 : 0.5}
          />
        ))}

        {/* Nodes */}
        {nodes.map(node => (
          <NodeMesh
            key={node.id}
            node={node}
            isActive={activeNodes.includes(node.id) || hoveredNode === node.id}
            onHover={setHoveredNode}
            onClick={setSelectedNode}
          />
        ))}

        <OrbitControls
          enablePan={false}
          minDistance={4}
          maxDistance={14}
          autoRotate
          autoRotateSpeed={0.5}
        />
      </Canvas>

      {/* Tooltip */}
      {hoveredNode && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 glass rounded-lg px-3 py-1.5 text-sm text-white pointer-events-none z-10">
          Click to learn about {nodes.find(n => n.id === hoveredNode)?.label}
        </div>
      )}

      {/* Side Panel */}
      <AnimatePresence>
        {selectedNode && selectedNodeData && (
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 20 }}
            className="absolute top-0 right-0 h-full w-64 glass border-l border-blue-500/20 p-4 overflow-y-auto"
          >
            <button
              onClick={() => setSelectedNode(null)}
              className="absolute top-3 right-3 text-slate-400 hover:text-white text-lg"
            >
              ×
            </button>
            <div
              className="w-3 h-3 rounded-full mb-3 mt-1"
              style={{ backgroundColor: selectedNodeData.color }}
            />
            <h3 className="text-white font-bold text-lg mb-2">{selectedNodeData.label}</h3>
            <p className="text-slate-300 text-sm leading-relaxed">{selectedNodeData.description}</p>
            {selectedNodeData.connections.length > 0 && (
              <div className="mt-4">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Connects To</div>
                {selectedNodeData.connections.map(connId => {
                  const connNode = nodes.find(n => n.id === connId)
                  return connNode ? (
                    <div key={connId} className="flex items-center gap-2 text-sm text-slate-300 mb-1">
                      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: connNode.color }} />
                      {connNode.label}
                    </div>
                  ) : null
                })}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 glass rounded-lg p-3">
        <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Nodes</div>
        <div className="flex flex-col gap-1.5">
          {nodes.map(node => (
            <div key={node.id} className="flex items-center gap-2 text-xs">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: node.color }}
              />
              <span className="text-slate-400">{node.label}</span>
              {activeNodes.includes(node.id) && (
                <span className="text-xs text-green-400">●</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

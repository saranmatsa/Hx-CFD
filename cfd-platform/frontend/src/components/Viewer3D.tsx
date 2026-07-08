import { useRef, useEffect, useState, Suspense } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Grid, AxesHelper, Environment, PerspectiveCamera } from '@react-three/drei'
import * as THREE from 'three'
import { useViewerStore } from '../store/viewerStore'

interface Viewer3DProps {
  meshUrl?: string
  vtkData?: {
    points: number[][]
    cells: number[]
    pointData?: Record<string, number[]>
    cellData?: Record<string, number[]>
  }
  className?: string
  showControls?: boolean
  onFieldSelect?: (field: string) => void
}

// Color maps for CFD visualization
const COLORMAPS = {
  viridis: ['#440154', '#414487', '#2a788e', '#22a884', '#7ad151', '#fde725'],
  coolwarm: ['#3b4cc0', '#6788ee', '#9abbff', '#f0f0f0', '#f8a58a', '#c03a2b'],
  plasma: ['#0d0887', '#6a00a8', '#b12a90', '#e16462', '#fca636', '#f0f921'],
}

function MeshGeometry({ data, colorMap = 'viridis' }: { data: { points: number[][]; cells: number[] }; colorMap?: keyof typeof COLORMAPS }) {
  const meshRef = useRef<THREE.Mesh>(null)
  const [hovered, setHovered] = useState(false)

  useEffect(() => {
    if (!meshRef.current) return

    const geometry = new THREE.BufferGeometry()
    const positions = new Float32Array(data.points.flatMap(p => p))
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    if (data.cells.length > 0) {
      geometry.setIndex(data.cells)
      geometry.computeVertexNormals()
    }

    meshRef.current.geometry = geometry
  }, [data])

  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.001
    }
  })

  return (
    <mesh
      ref={meshRef}
      onPointerOver={() => setHovered(true)}
      onPointerOut={() => setHovered(false)}
    >
      <bufferGeometry />
      <meshStandardMaterial
        color={hovered ? '#60a5fa' : '#4488ff'}
        side={THREE.DoubleSide}
        wireframe={false}
        transparent
        opacity={0.9}
      />
    </mesh>
  )
}

function CFDVisualization({ data, field, colorMap }: { data: { points: number[][]; cells: number[]; pointData?: Record<string, number[]> }; field: string; colorMap: keyof typeof COLORMAPS }) {
  const meshRef = useRef<THREE.Mesh>(null)

  useEffect(() => {
    if (!meshRef.current || !data.pointData || !data.pointData[field]) return

    const fieldData = data.pointData[field]
    const colors = new Float32Array(data.points.length * 3)
    const min = Math.min(...fieldData)
    const max = Math.max(...fieldData)
    const colorScale = COLORMAPS[colorMap]

    for (let i = 0; i < fieldData.length; i++) {
      const t = (fieldData[i] - min) / (max - min || 1)
      const colorIndex = Math.min(Math.floor(t * (colorScale.length - 1)), colorScale.length - 2)
      const localT = (t * (colorScale.length - 1)) % 1
      const color = new THREE.Color(colorScale[colorIndex])
      colors[i * 3] = color.r
      colors[i * 3 + 1] = color.g
      colors[i * 3 + 2] = color.b
    }

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(data.points.flatMap(p => p)), 3))
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    if (data.cells.length > 0) {
      geometry.setIndex(data.cells)
      geometry.computeVertexNormals()
    }

    meshRef.current.geometry = geometry
  }, [data, field, colorMap])

  return (
    <mesh ref={meshRef}>
      <bufferGeometry />
      <meshStandardMaterial vertexColors side={THREE.DoubleSide} />
    </mesh>
  )
}

function CameraController() {
  const { camera } = useThree()
  
  useFrame(() => {
    // Smooth camera movement could be added here
  })
  
  return null
}

function Scene({ data, showField, field, colorMap }: { 
  data?: { points: number[][]; cells: number[]; pointData?: Record<string, number[]> }; 
  showField: boolean;
  field: string;
  colorMap: keyof typeof COLORMAPS;
}) {
  return (
    <>
      <PerspectiveCamera makeDefault position={[5, 5, 5]} fov={50} />
      <OrbitControls enableDamping dampingFactor={0.05} />
      <CameraController />
      
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 10]} intensity={0.8} />
      <directionalLight position={[-10, -10, -10]} intensity={0.3} />
      
      <Grid args={[20, 20]} cellSize={1} cellThickness={0.5} cellColor="#444444" sectionSize={5} sectionThickness={1} sectionColor="#666666" fadeDistance={50} />
      <AxesHelper args={[3]} />
      
      {data && (
        showField && data.pointData && data.pointData[field] ? (
          <CFDVisualization data={data} field={field} colorMap={colorMap} />
        ) : (
          <MeshGeometry data={data} colorMap={colorMap} />
        )
      )}
      
      <Environment preset="city" />
    </>
  )
}

export default function Viewer3D({ meshUrl, vtkData, className = '', showControls = true, onFieldSelect }: Viewer3DProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
  const [showField, setShowField] = useState(false)
  const [field, setField] = useState('p')
  const [colorMap, setColorMap] = useState<keyof typeof COLORMAPS>('viridis')
  const { selectedField, setSelectedField } = useViewerStore()

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        })
      }
    }

    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  const handleFieldChange = (newField: string) => {
    setField(newField)
    setSelectedField(newField)
    onFieldSelect?.(newField)
  }

  const availableFields = vtkData?.pointData ? Object.keys(vtkData.pointData) : []

  return (
    <div className={`relative ${className}`}>
      <div ref={containerRef} className="w-full h-full min-h-[400px] bg-gray-900 rounded-lg overflow-hidden">
        <Canvas
          gl={{ antialias: true, alpha: true }}
          style={{ background: '#1a1a2e' }}
        >
          <Suspense fallback={null}>
            <Scene 
              data={vtkData} 
              showField={showField} 
              field={field}
              colorMap={colorMap}
            />
          </Suspense>
        </Canvas>
      </div>

      {showControls && (
        <div className="absolute top-4 right-4 bg-gray-800/90 backdrop-blur-sm rounded-lg p-4 text-white space-y-4 w-64">
          <h3 className="font-semibold text-sm">Viewer Controls</h3>
          
          {/* Field Selection */}
          {availableFields.length > 0 && (
            <div>
              <label className="block text-xs text-gray-400 mb-1">Field</label>
              <select
                value={field}
                onChange={(e) => handleFieldChange(e.target.value)}
                className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm"
              >
                <option value="">Geometry</option>
                {availableFields.map(f => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>
          )}

          {/* Color Map */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">Color Map</label>
            <select
              value={colorMap}
              onChange={(e) => setColorMap(e.target.value as keyof typeof COLORMAPS)}
              className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm"
            >
              <option value="viridis">Viridis</option>
              <option value="coolwarm">Cool-Warm</option>
              <option value="plasma">Plasma</option>
            </select>
          </div>

          {/* Color Scale Legend */}
          {showField && availableFields.length > 0 && (
            <div>
              <label className="block text-xs text-gray-400 mb-1">Scale</label>
              <div className="h-4 rounded" style={{
                background: `linear-gradient(to right, ${COLORMAPS[colorMap].join(', ')})`
              }} />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>Min</span>
                <span>Max</span>
              </div>
            </div>
          )}

          {/* Quick Stats */}
          {vtkData && (
            <div className="pt-2 border-t border-gray-700">
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-400">Points:</span>
                  <span className="ml-1">{vtkData.points.length.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-gray-400">Cells:</span>
                  <span className="ml-1">{vtkData.cells.length.toLocaleString()}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Loading Overlay */}
      {!vtkData && !meshUrl && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/50">
          <div className="text-white text-center">
            <svg className="animate-spin h-8 w-8 mx-auto mb-2" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <p className="text-sm">Loading 3D view...</p>
          </div>
        </div>
      )}
    </div>
  )
}

// VTK.js integration component for advanced visualization
export function VTKViewer({ dataUrl, className = '' }: { dataUrl?: string; className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current || !dataUrl) return

    // VTK.js integration would go here
    // This is a placeholder for VTK.js specific rendering
    const container = containerRef.current
    
    return () => {
      // Cleanup VTK.js resources
    }
  }, [dataUrl])

  return (
    <div ref={containerRef} className={`w-full h-full min-h-[400px] bg-gray-900 rounded-lg ${className}`}>
      {/* VTK.js rendering would happen here */}
      <div className="flex items-center justify-center h-full text-gray-500">
        VTK.js Viewer - Connect to data source
      </div>
    </div>
  )
}
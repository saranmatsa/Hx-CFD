import { useEffect, useRef } from 'react'
import { useViewerStore } from '../store/viewerStore'
import { useSimulation } from '../hooks/useSimulation'

interface SimulationViewerProps {
  simulationId?: string
  className?: string
}

export default function SimulationViewer({ simulationId, className = '' }: SimulationViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const { colormap, setColormap, clippingPlane, setClippingPlane } = useViewerStore()
  const { simulations } = useSimulation()

  const simulation = simulations.find(s => s.id === simulationId)

  useEffect(() => {
    if (!containerRef.current) return

    const container = containerRef.current
    const scene = new (window as any).THREE.Scene()
    scene.background = new (window as any).THREE.Color(0x1a1a2e)

    const camera = new (window as any).THREE.PerspectiveCamera(
      60,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    )
    camera.position.set(10, 10, 10)

    const renderer = new (window as any).THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(container.clientWidth, container.clientHeight)
    container.appendChild(renderer.domElement)

    const ambientLight = new (window as any).THREE.AmbientLight(0xffffff, 0.5)
    scene.add(ambientLight)

    const directionalLight = new (window as any).THREE.DirectionalLight(0xffffff, 0.8)
    directionalLight.position.set(10, 20, 10)
    scene.add(directionalLight)

    const geometry = new (window as any).THREE.BoxGeometry(4, 4, 4)
    const material = new (window as any).THREE.MeshPhongMaterial({
      color: 0x4488ff,
      transparent: true,
      opacity: 0.8,
      wireframe: false
    })
    const cube = new (window as any).THREE.Mesh(geometry, material)
    scene.add(cube)

    const gridHelper = new (window as any).THREE.GridHelper(20, 20, 0x444444, 0x222222)
    scene.add(gridHelper)

    const animate = () => {
      requestAnimationFrame(animate)
      cube.rotation.x += 0.005
      cube.rotation.y += 0.005
      renderer.render(scene, camera)
    }
    animate()

    return () => {
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [])

  return (
    <div className="space-y-4">
      <div ref={containerRef} className={`w-full h-full min-h-[500px] bg-gray-900 rounded-lg ${className}`} />
      
      {simulation && (
        <div className="bg-gray-800 rounded-lg p-4 text-white">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-gray-400 text-sm">Status</p>
              <p className="font-medium capitalize">{simulation.status}</p>
            </div>
            <div>
              <p className="text-gray-400 text-sm">Progress</p>
              <p className="font-medium">{simulation.progress ? `${(simulation.progress * 100).toFixed(1)}%` : 'N/A'}</p>
            </div>
            <div>
              <p className="text-gray-400 text-sm">Current Time</p>
              <p className="font-medium">{simulation.current_time?.toFixed(4) || 'N/A'}</p>
            </div>
            <div>
              <p className="text-gray-400 text-sm">Iterations</p>
              <p className="font-medium">{simulation.num_iterations?.toLocaleString() || 'N/A'}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
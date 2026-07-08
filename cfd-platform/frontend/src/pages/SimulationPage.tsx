import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { simulationService } from '../services/simulationService'
import { visualizationService } from '../services/visualizationService'
import { useState, useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

export default function SimulationPage() {
  const { simulationId } = useParams<{ simulationId: string }>()
  const navigate = useNavigate()
  const containerRef = useRef<HTMLDivElement>(null)
  const [selectedField, setSelectedField] = useState('p')

  const { data: simulation, isLoading } = useQuery({
    queryKey: ['simulation', simulationId],
    queryFn: () => simulationService.get(simulationId!),
    enabled: !!simulationId,
    refetchInterval: 5000,
  })

  useEffect(() => {
    if (!containerRef.current) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xf0f0f0)

    const camera = new THREE.PerspectiveCamera(75, containerRef.current.clientWidth / containerRef.current.clientHeight, 0.1, 1000)
    camera.position.set(5, 5, 5)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight)
    containerRef.current.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true

    const geometry = new THREE.BoxGeometry(2, 2, 2)
    const material = new THREE.MeshPhongMaterial({ color: 0x00aaff, wireframe: true })
    const cube = new THREE.Mesh(geometry, material)
    scene.add(cube)

    const light = new THREE.DirectionalLight(0xffffff, 1)
    light.position.set(5, 5, 5)
    scene.add(light)
    scene.add(new THREE.AmbientLight(0x404040))

    const grid = new THREE.GridHelper(10, 10)
    scene.add(grid)

    const animate = () => {
      requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    const handleResize = () => {
      if (!containerRef.current) return
      camera.aspect = containerRef.current.clientWidth / containerRef.current.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      renderer.dispose()
      if (containerRef.current) {
        containerRef.current.removeChild(renderer.domElement)
      }
    }
  }, [])

  if (isLoading) return <div>Loading...</div>
  if (!simulation) return <div>Simulation not found</div>

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-700">
          ← Back
        </button>
        <h1 className="text-2xl font-bold">{simulation.name}</h1>
        <span className={`px-2 py-1 text-xs rounded ${
          simulation.status === 'completed' ? 'bg-green-100 text-green-800' :
          simulation.status === 'running' ? 'bg-blue-100 text-blue-800' :
          'bg-gray-100 text-gray-800'
        }`}>
          {simulation.status}
        </span>
      </div>

      <div className="grid grid-cols-4 gap-6">
        <div className="col-span-3 bg-white rounded-lg shadow">
          <div className="p-4 border-b flex justify-between items-center">
            <h2 className="font-semibold">3D Visualization</h2>
            <select
              value={selectedField}
              onChange={(e) => setSelectedField(e.target.value)}
              className="px-3 py-1 border rounded"
            >
              <option value="p">Pressure (p)</option>
              <option value="U">Velocity (U)</option>
              <option value="T">Temperature (T)</option>
            </select>
          </div>
          <div ref={containerRef} className="h-96" />
        </div>

        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-2">Simulation Info</h3>
            <dl className="space-y-1 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Solver</dt>
                <dd>{simulation.solver}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Status</dt>
                <dd>{simulation.status}</dd>
              </div>
              {simulation.progress !== undefined && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Progress</dt>
                  <dd>{Math.round(simulation.progress * 100)}%</dd>
                </div>
              )}
            </dl>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-2">Controls</h3>
            <div className="space-y-2">
              {simulation.status !== 'running' && (
                <button className="w-full bg-green-600 text-white py-2 rounded hover:bg-green-700">
                  Start
                </button>
              )}
              {simulation.status === 'running' && (
                <button className="w-full bg-red-600 text-white py-2 rounded hover:bg-red-700">
                  Stop
                </button>
              )}
              <button className="w-full bg-gray-200 py-2 rounded hover:bg-gray-300">
                Export Results
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
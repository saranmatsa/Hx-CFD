import { useRef, useEffect } from 'react'
import * as THREE from 'three'
import { useViewerStore } from '../store/viewerStore'

interface MeshViewerProps {
  points?: number[][]
  connectivity?: number[]
  boundingBox?: { min: [number, number, number]; max: [number, number, number] }
  className?: string
}

export default function MeshViewer({ points, connectivity, boundingBox, className = '' }: MeshViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const { camera, setCamera, clippingPlane, setClippingPlane, colormap } = useViewerStore()

  useEffect(() => {
    if (!containerRef.current) return

    const container = containerRef.current
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xf0f0f0)

    const camera3D = new THREE.PerspectiveCamera(
      75,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    )
    camera3D.position.set(5, 5, 5)
    camera3D.lookAt(0, 0, 0)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(container.clientWidth, container.clientHeight)
    container.appendChild(renderer.domElement)

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
    scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.4)
    directionalLight.position.set(10, 10, 10)
    scene.add(directionalLight)

    if (points && connectivity && points.length > 0) {
      const geometry = new THREE.BufferGeometry()
      const positions = new Float32Array(points.flatMap(p => p))
      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

      if (connectivity.length > 0) {
        geometry.setIndex(connectivity)
        geometry.computeVertexNormals()
      }

      const material = new THREE.MeshPhongMaterial({
        color: 0x4488ff,
        side: THREE.DoubleSide,
        wireframe: false
      })

      const mesh = new THREE.Mesh(geometry, material)
      scene.add(mesh)

      if (boundingBox) {
        const center = new THREE.Vector3(
          (boundingBox.min[0] + boundingBox.max[0]) / 2,
          (boundingBox.min[1] + boundingBox.max[1]) / 2,
          (boundingBox.min[2] + boundingBox.max[2]) / 2
        )
        camera3D.lookAt(center)
      }
    }

    const gridHelper = new THREE.GridHelper(10, 10)
    scene.add(gridHelper)

    const axesHelper = new THREE.AxesHelper(2)
    scene.add(axesHelper)

    const animate = () => {
      requestAnimationFrame(animate)
      renderer.render(scene, camera3D)
    }
    animate()

    const handleResize = () => {
      if (!container) return
      camera3D.aspect = container.clientWidth / container.clientHeight
      camera3D.updateProjectionMatrix()
      renderer.setSize(container.clientWidth, container.clientHeight)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      renderer.dispose()
      container.removeChild(renderer.domElement)
    }
  }, [points, connectivity, boundingBox])

  return (
    <div ref={containerRef} className={`w-full h-full min-h-[400px] ${className}`} />
  )
}
import { Bounds, OrbitControls } from '@react-three/drei'
import { Canvas, useLoader } from '@react-three/fiber'
import { TextureLoader } from 'three'
import { convertFileSrc } from '@tauri-apps/api/core'

type Viewport3DProps = {
  previewPath: string
  bounds?: unknown
}

function ResultPreview({ previewPath }: { previewPath: string }) {
  const texture = useLoader(
    TextureLoader,
    previewPath.startsWith('data:') ? previewPath : convertFileSrc(previewPath),
  )
  const ratio = texture.image.width / texture.image.height
  return <mesh>
    <planeGeometry args={[ratio * 2, 2]} />
    <meshBasicMaterial map={texture} toneMapped={false} />
  </mesh>
}

/**
 * Renders a PyVista-produced result image inside the desktop's actual
 * three.js/react-three-fiber viewport. No procedural turbine or streamlines
 * are generated here; this viewer only mounts a published result artifact.
 */
export function Viewport3D({ previewPath }: Viewport3DProps) {
  return <Canvas camera={{ position: [0, 0, 3], fov: 42 }} dpr={[1, 2]}>
    <color attach="background" args={['#030405']} />
    <ambientLight intensity={0.8} />
    <Bounds fit clip observe margin={1.15}>
      <ResultPreview previewPath={previewPath} />
    </Bounds>
    <OrbitControls enablePan={false} />
  </Canvas>
}

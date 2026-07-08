import { LitElement, html, css, PropertyValues } from 'lit'
import { customElement, property, query, state } from 'lit/decorators.js'
import * as THREE from 'three'
import { CfdComponent } from './base'

interface BoundingBox {
  min: [number, number, number]
  max: [number, number, number]
}

@customElement('mesh-viewer')
export class MeshViewer extends CfdComponent {
  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      min-height: 400px;
    }
    .container {
      width: 100%;
      height: 100%;
      background: #f0f0f0;
    }
  `

  @property({ type: Array }) points: number[][] = []
  @property({ type: Array }) connectivity: number[] = []
  @property({ type: Object }) boundingBox: BoundingBox | null = null
  @property({ type: String }) className = ''

  @query('.container') container!: HTMLDivElement

  @state() private _isLoading = false

  private scene: THREE.Scene | null = null
  private camera: THREE.PerspectiveCamera | null = null
  private renderer: THREE.WebGLRenderer | null = null
  private animationId: number | null = null
  private mesh: THREE.Mesh | null = null

  protected updated(changedProperties: PropertyValues) {
    if (changedProperties.has('points') || changedProperties.has('connectivity') || changedProperties.has('boundingBox')) {
      this.updateMesh()
    }
  }

  firstUpdated() {
    this.initThree()
  }

  disconnectedCallback() {
    super.disconnectedCallback()
    this.dispose()
  }

  private initThree() {
    if (!this.container) return

    // Scene
    this.scene = new THREE.Scene()
    this.scene.background = new THREE.Color(0xf0f0f0)

    // Camera
    this.camera = new THREE.PerspectiveCamera(
      75,
      this.container.clientWidth / this.container.clientHeight,
      0.1,
      1000
    )
    this.camera.position.set(5, 5, 5)
    this.camera.lookAt(0, 0, 0)

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true })
    this.renderer.setSize(this.container.clientWidth, this.container.clientHeight)
    this.container.appendChild(this.renderer.domElement)

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
    this.scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.4)
    directionalLight.position.set(10, 10, 10)
    this.scene.add(directionalLight)

    // Grid and axes
    const gridHelper = new THREE.GridHelper(10, 10)
    this.scene.add(gridHelper)

    const axesHelper = new THREE.AxesHelper(2)
    this.scene.add(axesHelper)

    // Initial mesh
    this.updateMesh()

    // Animation loop
    const animate = () => {
      this.animationId = requestAnimationFrame(animate)
      if (this.camera && this.renderer && this.scene) {
        this.renderer.render(this.scene, this.camera)
      }
    }
    animate()

    // Resize handler
    const handleResize = () => {
      if (!this.container || !this.camera || !this.renderer) return
      this.camera.aspect = this.container.clientWidth / this.container.clientHeight
      this.camera.updateProjectionMatrix()
      this.renderer.setSize(this.container.clientWidth, this.container.clientHeight)
    }
    window.addEventListener('resize', handleResize)
  }

  private updateMesh() {
    if (!this.scene) return

    // Remove existing mesh
    if (this.mesh) {
      this.scene.remove(this.mesh)
      this.mesh.geometry.dispose()
      if (this.mesh.material instanceof THREE.Material) {
        this.mesh.material.dispose()
      }
      this.mesh = null
    }

    // Create new mesh if data available
    if (this.points && this.points.length > 0) {
      const geometry = new THREE.BufferGeometry()
      const positions = new Float32Array(this.points.flatMap(p => p))
      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

      if (this.connectivity && this.connectivity.length > 0) {
        geometry.setIndex(this.connectivity)
        geometry.computeVertexNormals()
      }

      const material = new THREE.MeshPhongMaterial({
        color: 0x4488ff,
        side: THREE.DoubleSide,
        wireframe: false
      })

      this.mesh = new THREE.Mesh(geometry, material)
      this.scene.add(this.mesh)

      // Center camera on mesh
      if (this.boundingBox && this.camera) {
        const center = new THREE.Vector3(
          (this.boundingBox.min[0] + this.boundingBox.max[0]) / 2,
          (this.boundingBox.min[1] + this.boundingBox.max[1]) / 2,
          (this.boundingBox.min[2] + this.boundingBox.max[2]) / 2
        )
        this.camera.lookAt(center)
      }
    }
  }

  private dispose() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId)
    }
    if (this.mesh) {
      this.mesh.geometry.dispose()
      if (this.mesh.material instanceof THREE.Material) {
        this.mesh.material.dispose()
      }
    }
    if (this.renderer) {
      this.renderer.dispose()
      if (this.container && this.renderer.domElement.parentNode === this.container) {
        this.container.removeChild(this.renderer.domElement)
      }
    }
  }

  render() {
    return html`<div class="container ${this.className}"></div>`
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'mesh-viewer': MeshViewer
  }
}
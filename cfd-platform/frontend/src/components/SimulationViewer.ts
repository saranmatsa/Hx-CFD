import { LitElement, html, css, PropertyValues } from 'lit'
import { customElement, property, query, state } from 'lit/decorators.js'
import * as THREE from 'three'
import { CfdComponent } from './base'

interface Simulation {
  id: string
  status: string
  progress?: number
  current_time?: number
  num_iterations?: number
}

@customElement('simulation-viewer')
export class SimulationViewer extends CfdComponent {
  static styles = css`
    :host {
      display: block;
    }
    .container {
      width: 100%;
      height: 100%;
      min-height: 500px;
      background: #1a1a2e;
      border-radius: 0.5rem;
    }
    .info-panel {
      background: #1f2937;
      border-radius: 0.5rem;
      padding: 1rem;
      color: white;
    }
    .info-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;
    }
    @media (min-width: 768px) {
      .info-grid {
        grid-template-columns: repeat(4, 1fr);
      }
    }
    .info-item {
      display: flex;
      flex-direction: column;
    }
    .info-label {
      color: #9ca3af;
      font-size: 0.875rem;
    }
    .info-value {
      font-weight: 500;
      text-transform: capitalize;
    }
    .space-y-4 > * + * {
      margin-top: 1rem;
    }
  `

  @property({ type: String }) simulationId = ''
  @property({ type: String }) className = ''

  @query('.container') container!: HTMLDivElement

  @state() private _simulation: Simulation | null = null

  private scene: THREE.Scene | null = null
  private camera: THREE.PerspectiveCamera | null = null
  private renderer: THREE.WebGLRenderer | null = null
  private animationId: number | null = null
  private cube: THREE.Mesh | null = null

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
    this.scene.background = new THREE.Color(0x1a1a2e)

    // Camera
    this.camera = new THREE.PerspectiveCamera(
      60,
      this.container.clientWidth / this.container.clientHeight,
      0.1,
      1000
    )
    this.camera.position.set(10, 10, 10)

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true })
    this.renderer.setSize(this.container.clientWidth, this.container.clientHeight)
    this.container.appendChild(this.renderer.domElement)

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5)
    this.scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
    directionalLight.position.set(10, 20, 10)
    this.scene.add(directionalLight)

    // Demo cube (placeholder for actual simulation mesh)
    const geometry = new THREE.BoxGeometry(4, 4, 4)
    const material = new THREE.MeshPhongMaterial({
      color: 0x4488ff,
      transparent: true,
      opacity: 0.8,
      wireframe: false
    })
    this.cube = new THREE.Mesh(geometry, material)
    this.scene.add(this.cube)

    // Grid
    const gridHelper = new THREE.GridHelper(20, 20, 0x444444, 0x222222)
    this.scene.add(gridHelper)

    // Animation loop
    const animate = () => {
      this.animationId = requestAnimationFrame(animate)
      if (this.cube) {
        this.cube.rotation.x += 0.005
        this.cube.rotation.y += 0.005
      }
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

  private dispose() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId)
    }
    if (this.cube) {
      this.cube.geometry.dispose()
      if (this.cube.material instanceof THREE.Material) {
        this.cube.material.dispose()
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
    return html`
      <div class="space-y-4">
        <div class="container ${this.className}"></div>
        
        ${this._simulation ? html`
          <div class="info-panel">
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">Status</span>
                <span class="info-value">${this._simulation.status}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Progress</span>
                <span class="info-value">${this._simulation.progress ? `${(this._simulation.progress * 100).toFixed(1)}%` : 'N/A'}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Current Time</span>
                <span class="info-value">${this._simulation.current_time?.toFixed(4) || 'N/A'}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Iterations</span>
                <span class="info-value">${this._simulation.num_iterations?.toLocaleString() || 'N/A'}</span>
              </div>
            </div>
          </div>
        ` : ''}
      </div>
    `
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'simulation-viewer': SimulationViewer
  }
}
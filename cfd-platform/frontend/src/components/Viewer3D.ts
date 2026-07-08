import { LitElement, html, css, PropertyValues } from 'lit'
import { customElement, property, query, state } from 'lit/decorators.js'
import * as THREE from 'three'
import { CfdComponent } from './base'

interface VTKData {
  points: number[][]
  cells: number[]
  pointData?: Record<string, number[]>
  cellData?: Record<string, number[]>
}

// Color maps for CFD visualization
const COLORMAPS: Record<string, string[]> = {
  viridis: ['#440154', '#414487', '#2a788e', '#22a884', '#7ad151', '#fde725'],
  coolwarm: ['#3b4cc0', '#6788ee', '#9abbff', '#f0f0f0', '#f8a58a', '#c03a2b'],
  plasma: ['#0d0887', '#6a00a8', '#b12a90', '#e16462', '#fca636', '#f0f921'],
}

@customElement('viewer-3d')
export class Viewer3D extends CfdComponent {
  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
    }
    .container {
      width: 100%;
      height: 100%;
      position: relative;
    }
    .controls {
      position: absolute;
      top: 1rem;
      right: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      z-index: 10;
    }
    .control-btn {
      padding: 0.5rem;
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid #e5e7eb;
      border-radius: 0.375rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .control-btn:hover {
      background: white;
    }
    .control-btn.active {
      background: #2563eb;
      color: white;
      border-color: #2563eb;
    }
    .field-selector {
      position: absolute;
      bottom: 1rem;
      left: 1rem;
      background: rgba(255, 255, 255, 0.95);
      padding: 0.75rem;
      border-radius: 0.5rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
      z-index: 10;
    }
    .field-label {
      font-size: 0.75rem;
      font-weight: 500;
      color: #6b7280;
      margin-bottom: 0.25rem;
    }
    .field-select {
      padding: 0.25rem 0.5rem;
      border: 1px solid #d1d5db;
      border-radius: 0.25rem;
      font-size: 0.875rem;
      min-width: 120px;
    }
    .loading {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      color: #6b7280;
    }
  `

  @property({ type: String }) meshUrl = ''
  @property({ type: Object }) vtkData: VTKData | null = null
  @property({ type: String }) className = ''
  @property({ type: Boolean }) showControls = true
  @property({ type: String }) colorMap = 'viridis'

  @query('.container') container!: HTMLDivElement

  @state() private _selectedField = ''
  @state() private _isLoading = false
  @state() private _isWireframe = false
  @state() private _autoRotate = true
  @state() private _availableFields: string[] = []

  private scene: THREE.Scene | null = null
  private camera: THREE.PerspectiveCamera | null = null
  private renderer: THREE.WebGLRenderer | null = null
  private animationId: number | null = null
  private mesh: THREE.Mesh | null = null
  private controls: { rotate: () => void } | null = null

  firstUpdated() {
    this.initThree()
    if (this.vtkData) {
      this.updateMesh(this.vtkData)
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback()
    this.dispose()
  }

  protected updated(changedProperties: PropertyValues) {
    if (changedProperties.has('vtkData') && this.vtkData) {
      this.updateMesh(this.vtkData)
    }
    if (changedProperties.has('colorMap') && this.mesh && this._selectedField) {
      this.updateFieldColors(this._selectedField)
    }
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

    // Grid
    const gridHelper = new THREE.GridHelper(20, 20, 0x444444, 0x222222)
    this.scene.add(gridHelper)

    // Axes
    const axesHelper = new THREE.AxesHelper(5)
    this.scene.add(axesHelper)

    // Animation loop
    const animate = () => {
      this.animationId = requestAnimationFrame(animate)
      if (this._autoRotate && this.mesh) {
        this.mesh.rotation.y += 0.001
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

    // Mouse controls (simple orbit)
    this.setupMouseControls()
  }

  private setupMouseControls() {
    let isDragging = false
    let previousMousePosition = { x: 0, y: 0 }

    this.container?.addEventListener('mousedown', (e) => {
      isDragging = true
      previousMousePosition = { x: e.clientX, y: e.clientY }
    })

    this.container?.addEventListener('mousemove', (e) => {
      if (!isDragging || !this.camera) return

      const deltaX = e.clientX - previousMousePosition.x
      const deltaY = e.clientY - previousMousePosition.y

      if (this.mesh) {
        this.mesh.rotation.y += deltaX * 0.01
        this.mesh.rotation.x += deltaY * 0.01
      }

      previousMousePosition = { x: e.clientX, y: e.clientY }
    })

    this.container?.addEventListener('mouseup', () => {
      isDragging = false
    })

    this.container?.addEventListener('mouseleave', () => {
      isDragging = false
    })
  }

  private updateMesh(data: VTKData) {
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

    // Create geometry
    const geometry = new THREE.BufferGeometry()
    const positions = new Float32Array(data.points.flatMap(p => p))
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    if (data.cells.length > 0) {
      geometry.setIndex(data.cells)
      geometry.computeVertexNormals()
    }

    // Create material
    const material = new THREE.MeshStandardMaterial({
      color: 0x4488ff,
      side: THREE.DoubleSide,
      wireframe: this._isWireframe,
      transparent: true,
      opacity: 0.9
    })

    this.mesh = new THREE.Mesh(geometry, material)
    this.scene.add(this.mesh)

    // Update available fields
    if (data.pointData) {
      this._availableFields = Object.keys(data.pointData)
    }
  }

  private updateFieldColors(field: string) {
    if (!this.mesh || !this.vtkData?.pointData || !this.vtkData.pointData[field]) return

    const fieldData = this.vtkData.pointData[field]
    const colors = new Float32Array(this.vtkData.points.length * 3)
    const min = Math.min(...fieldData)
    const max = Math.max(...fieldData)
    const colorScale = COLORMAPS[this.colorMap] || COLORMAPS.viridis

    for (let i = 0; i < fieldData.length; i++) {
      const t = (fieldData[i] - min) / (max - min || 1)
      const colorIndex = Math.min(Math.floor(t * (colorScale.length - 1)), colorScale.length - 2)
      const color = new THREE.Color(colorScale[colorIndex])
      colors[i * 3] = color.r
      colors[i * 3 + 1] = color.g
      colors[i * 3 + 2] = color.b
    }

    const geometry = this.mesh.geometry
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    
    const material = this.mesh.material as THREE.MeshStandardMaterial
    material.vertexColors = true
    material.needsUpdate = true
  }

  private toggleWireframe() {
    this._isWireframe = !this._isWireframe
    if (this.mesh) {
      const material = this.mesh.material as THREE.MeshStandardMaterial
      material.wireframe = this._isWireframe
      material.needsUpdate = true
    }
  }

  private toggleAutoRotate() {
    this._autoRotate = !this._autoRotate
  }

  private resetCamera() {
    if (this.camera) {
      this.camera.position.set(10, 10, 10)
      this.camera.lookAt(0, 0, 0)
    }
  }

  private handleFieldChange(e: Event) {
    const select = e.target as HTMLSelectElement
    this._selectedField = select.value
    if (this._selectedField) {
      this.updateFieldColors(this._selectedField)
      this.dispatchEvent(new CustomEvent('field-select', { 
        detail: { field: this._selectedField } 
      }))
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
    return html`
      <div class="container ${this.className}">
        ${this._isLoading ? html`<div class="loading">Loading...</div>` : ''}
        
        ${this.showControls ? html`
          <div class="controls">
            <button 
              class="control-btn ${this._isWireframe ? 'active' : ''}"
              @click="${this.toggleWireframe}"
              title="Toggle Wireframe"
            >
              <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
            </button>
            <button 
              class="control-btn ${this._autoRotate ? 'active' : ''}"
              @click="${this.toggleAutoRotate}"
              title="Toggle Auto Rotate"
            >
              <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <button 
              class="control-btn"
              @click="${this.resetCamera}"
              title="Reset Camera"
            >
              <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
            </button>
          </div>
        ` : ''}

        ${this._availableFields.length > 0 ? html`
          <div class="field-selector">
            <div class="field-label">Field</div>
            <select 
              class="field-select"
              @change="${this.handleFieldChange}"
            >
              <option value="">Select field...</option>
              ${this._availableFields.map(field => html`
                <option value="${field}">${field}</option>
              `)}
            </select>
          </div>
        ` : ''}
      </div>
    `
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'viewer-3d': Viewer3D
  }
}
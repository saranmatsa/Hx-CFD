import { LitElement, html, css } from 'lit'
import { customElement, state, query } from 'lit/decorators.js'
import { CfdComponent } from '../components/base'
import { simulationService, Simulation } from '../services/simulationService'
import { visualizationService } from '../services/visualizationService'
import { notify } from '../services/notificationService'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

@customElement('cfd-simulation-page')
export class SimulationPage extends LitElement {
  static styles = css`
    :host {
      display: block;
      height: 100%;
    }
    .simulation-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #f9fafb;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 24px;
      background: white;
      border-bottom: 1px solid #e5e7eb;
    }
    .header h1 {
      font-size: 20px;
      font-weight: 600;
    }
    .status-badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 500;
    }
    .status-running { background: #dbeafe; color: #1e40af; }
    .status-completed { background: #d1fae5; color: #065f46; }
    .status-failed { background: #fee2e2; color: #991b1b; }
    .status-pending { background: #f3f4f6; color: #4b5563; }
    .main-content {
      display: flex;
      flex: 1;
      overflow: hidden;
    }
    .viewer {
      flex: 1;
      position: relative;
    }
    #three-canvas {
      width: 100%;
      height: 100%;
    }
    .sidebar {
      width: 300px;
      background: white;
      border-left: 1px solid #e5e7eb;
      padding: 16px;
      overflow-y: auto;
    }
    .sidebar-section {
      margin-bottom: 24px;
    }
    .sidebar-section h3 {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 12px;
      color: #374151;
    }
    .field-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .field-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
    }
    .field-item:hover {
      background: #f3f4f6;
    }
    .field-item.active {
      background: #eff6ff;
      color: #2563eb;
    }
    .info-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .info-item {
      background: #f9fafb;
      padding: 12px;
      border-radius: 6px;
    }
    .info-item label {
      display: block;
      font-size: 11px;
      color: #6b7280;
      text-transform: uppercase;
      margin-bottom: 4px;
    }
    .info-item span {
      font-size: 14px;
      font-weight: 500;
    }
    .loading-overlay {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.9);
    }
    .spinner {
      width: 40px;
      height: 40px;
      border: 3px solid #e5e7eb;
      border-top-color: #2563eb;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `

  @state() private _simulation: Simulation | null = null
  @state() private _isLoading = true
  @state() private _selectedField = 'p'
  @state() private _availableFields: string[] = ['p', 'U', 'T', 'k', 'epsilon']

  @query('#three-canvas') private _canvas!: HTMLCanvasElement

  private _scene: THREE.Scene | null = null
  private _camera: THREE.PerspectiveCamera | null = null
  private _renderer: THREE.WebGLRenderer | null = null
  private _controls: OrbitControls | null = null
  private _mesh: THREE.Mesh | null = null
  private _pollInterval: number | null = null
  private _animationFrame: number | null = null

  private _simulationId: string = ''

  connectedCallback() {
    super.connectedCallback()
    const params = new URLSearchParams(window.location.search)
    this._simulationId = params.get('id') || ''
    if (this._simulationId) {
      this._loadSimulation()
      this._startPolling()
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback()
    this._stopPolling()
    this._cleanup()
  }

  firstUpdated() {
    this._initThreeJS()
  }

  private _initThreeJS() {
    if (!this._canvas) return

    // Scene
    this._scene = new THREE.Scene()
    this._scene.background = new THREE.Color(0xf0f0f0)

    // Camera
    this._camera = new THREE.PerspectiveCamera(
      75,
      this._canvas.clientWidth / this._canvas.clientHeight,
      0.1,
      1000
    )
    this._camera.position.set(5, 5, 5)

    // Renderer
    this._renderer = new THREE.WebGLRenderer({
      canvas: this._canvas,
      antialias: true,
    })
    this._renderer.setSize(this._canvas.clientWidth, this._canvas.clientHeight)
    this._renderer.setPixelRatio(window.devicePixelRatio)

    // Controls
    this._controls = new OrbitControls(this._camera, this._renderer.domElement)
    this._controls.enableDamping = true
    this._controls.dampingFactor = 0.05

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
    this._scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
    directionalLight.position.set(10, 10, 10)
    this._scene.add(directionalLight)

    // Grid helper
    const gridHelper = new THREE.GridHelper(10, 10)
    this._scene.add(gridHelper)

    // Axes helper
    const axesHelper = new THREE.AxesHelper(2)
    this._scene.add(axesHelper)

    // Animation loop
    this._animate()
  }

  private _animate() {
    this._animationFrame = requestAnimationFrame(() => this._animate())
    this._controls?.update()
    if (this._renderer && this._scene && this._camera) {
      this._renderer.render(this._scene, this._camera)
    }
  }

  private _cleanup() {
    if (this._animationFrame) {
      cancelAnimationFrame(this._animationFrame)
    }
    if (this._renderer) {
      this._renderer.dispose()
    }
    if (this._mesh) {
      this._mesh.geometry.dispose()
      if (Array.isArray(this._mesh.material)) {
        this._mesh.material.forEach(m => m.dispose())
      } else {
        this._mesh.material.dispose()
      }
    }
  }

  private _startPolling() {
    this._pollInterval = window.setInterval(() => {
      this._loadSimulation()
    }, 5000)
  }

  private _stopPolling() {
    if (this._pollInterval) {
      clearInterval(this._pollInterval)
      this._pollInterval = null
    }
  }

  private async _loadSimulation() {
    try {
      const simulation = await simulationService.get(this._simulationId)
      this._simulation = simulation
      this._isLoading = false
    } catch (error) {
      console.error('Failed to load simulation:', error)
      this._isLoading = false
    }
  }

  private async _loadFieldData(field: string) {
    try {
      const data = await visualizationService.getScalarField(this._simulationId, field)
      this._updateVisualization(data)
    } catch (error) {
      console.error('Failed to load field data:', error)
    }
  }

  private _updateVisualization(data: any) {
    if (!this._scene || !data.points) return

    // Clear existing mesh
    if (this._mesh) {
      this._scene.remove(this._mesh)
      this._mesh.geometry.dispose()
    }

    // Create geometry from points
    const geometry = new THREE.BufferGeometry()
    const positions = new Float32Array(data.points.flat())
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    // Create material with scalar field coloring
    const material = new THREE.MeshPhongMaterial({
      color: 0x4488ff,
      side: THREE.DoubleSide,
      wireframe: true,
    })

    this._mesh = new THREE.Mesh(geometry, material)
    this._scene.add(this._mesh)
  }

  private _getStatusClass(status: string) {
    switch (status) {
      case 'completed': return 'status-completed'
      case 'running': return 'status-running'
      case 'failed': return 'status-failed'
      default: return 'status-pending'
    }
  }

  render() {
    const { _simulation, _isLoading, _selectedField, _availableFields } = this

    return html`
      <div class="simulation-container">
        <div class="header">
          <div>
            <h1>Simulation ${_simulation?.name || this._simulationId.slice(0, 8)}</h1>
            ${_simulation ? html`
              <span class="status-badge ${this._getStatusClass(_simulation.status)}">
                ${_simulation.status}
              </span>
            ` : ''}
          </div>
        </div>

        <div class="main-content">
          <div class="viewer">
            ${_isLoading ? html`
              <div class="loading-overlay">
                <div class="spinner"></div>
              </div>
            ` : ''}
            <canvas id="three-canvas"></canvas>
          </div>

          <div class="sidebar">
            <div class="sidebar-section">
              <h3>Simulation Info</h3>
              <div class="info-grid">
                <div class="info-item">
                  <label>Solver</label>
                  <span>${_simulation?.solver || '-'}</span>
                </div>
                <div class="info-item">
                  <label>Time</label>
                  <span>${_simulation?.current_time?.toFixed(2) || '0.00'}s</span>
                </div>
                <div class="info-item">
                  <label>Iterations</label>
                  <span>${_simulation?.iterations || 0}</span>
                </div>
                <div class="info-item">
                  <label>Cells</label>
                  <span>${_simulation?.num_cells?.toLocaleString() || '-'}</span>
                </div>
              </div>
            </div>

            <div class="sidebar-section">
              <h3>Visualization Fields</h3>
              <div class="field-list">
                ${_availableFields.map(field => html`
                  <div
                    class="field-item ${_selectedField === field ? 'active' : ''}"
                    @click=${() => {
                      this._selectedField = field
                      this._loadFieldData(field)
                    }}
                  >
                    <span>${field === 'U' ? 'Velocity' : field === 'p' ? 'Pressure' : field}</span>
                  </div>
                `)}
              </div>
            </div>
          </div>
        </div>
      </div>
    `
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'cfd-simulation-page': SimulationPage
  }
}
import { LitElement, html, css } from 'lit'
import { customElement, state } from 'lit/decorators.js'
import { CfdComponent } from '../components/base'
import { projectService, Project } from '../services/projectService'
import { meshService, Mesh } from '../services/meshService'
import { simulationService, Simulation } from '../services/simulationService'
import { notify } from '../services/notificationService'

@customElement('cfd-project-page')
export class ProjectPage extends CfdComponent {
  static styles = css`
    ...super.styles,
    `
    .project-container {
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }
    .btn {
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-primary {
      background: #2563eb;
      border: none;
      color: white;
    }
    .btn-primary:hover:not(:disabled) {
      background: #1d4ed8;
    }
    .btn-secondary {
      background: white;
      border: 1px solid #d1d5db;
      color: #374151;
    }
    .btn-secondary:hover {
      background: #f9fafb;
    }
    .card {
      background: white;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      padding: 24px;
      margin-bottom: 24px;
    }
    .card h2 {
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 16px;
    }
    .tabs {
      display: flex;
      border-bottom: 1px solid #e5e7eb;
      margin-bottom: 24px;
    }
    .tab {
      padding: 12px 24px;
      font-size: 14px;
      font-weight: 500;
      color: #6b7280;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      margin-bottom: -1px;
    }
    .tab:hover {
      color: #374151;
    }
    .tab.active {
      color: #2563eb;
      border-bottom-color: #2563eb;
    }
    .form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
    }
    .form-group {
      margin-bottom: 16px;
    }
    .form-group label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      color: #374151;
      margin-bottom: 4px;
    }
    .form-group input, .form-group select {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      font-size: 14px;
    }
    .table {
      width: 100%;
      border-collapse: collapse;
    }
    .table th, .table td {
      padding: 12px 16px;
      text-align: left;
      border-bottom: 1px solid #e5e7eb;
    }
    .table th {
      background: #f9fafb;
      font-size: 12px;
      font-weight: 500;
      color: #6b7280;
      text-transform: uppercase;
    }
    .table tbody tr:hover {
      background: #f9fafb;
    }
    .status-badge {
      display: inline-block;
      padding: 4px 8px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 500;
    }
    .status-completed { background: #d1fae5; color: #065f46; }
    .status-running { background: #dbeafe; color: #1e40af; }
    .status-pending { background: #f3f4f6; color: #4b5563; }
    .status-failed { background: #fee2e2; color: #991b1b; }
    .empty-state {
      padding: 48px;
      text-align: center;
      color: #6b7280;
    }
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 50;
    }
    .modal {
      background: white;
      border-radius: 8px;
      padding: 24px;
      width: 100%;
      max-width: 500px;
    }
    .modal h2 {
      font-size: 20px;
      font-weight: 600;
      margin-bottom: 16px;
    }
    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 24px;
    }
    .loading {
      display: flex;
      justify-content: center;
      padding: 48px;
    }
    .spinner {
      width: 32px;
      height: 32px;
      border: 3px solid #e5e7eb;
      border-top-color: #2563eb;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `

  @state() private _project: Project | null = null
  @state() private _meshes: Mesh[] = []
  @state() private _simulations: Simulation[] = []
  @state() private _isLoading = true
  @state() private _activeTab: 'meshes' | 'simulations' = 'meshes'
  @state() private _showMeshModal = false
  @state() private _showSimModal = false
  @state() private _isCreating = false
  @state() private _meshConfig = {
    name: '',
    element_size: 0.01,
    growth_rate: 1.2,
    num_boundary_layers: 3,
  }
  @state() private _simConfig = {
    name: '',
    end_time: 1.0,
    write_interval: 0.05,
    residual_print: true,
  }

  private _projectId: string = ''
  private _pollInterval: number | null = null

  connectedCallback() {
    super.connectedCallback()
    const params = new URLSearchParams(window.location.search)
    this._projectId = params.get('id') || ''
    if (this._projectId) {
      this._loadProject()
      this._loadMeshes()
      this._loadSimulations()
      this._startPolling()
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback()
    this._stopPolling()
  }

  private _startPolling() {
    this._pollInterval = window.setInterval(() => {
      this._loadMeshes()
      this._loadSimulations()
    }, 5000)
  }

  private _stopPolling() {
    if (this._pollInterval) {
      clearInterval(this._pollInterval)
      this._pollInterval = null
    }
  }

  private async _loadProject() {
    try {
      const project = await projectService.get(this._projectId)
      this._project = project
      this._isLoading = false
    } catch (error) {
      console.error('Failed to load project:', error)
      this._isLoading = false
    }
  }

  private async _loadMeshes() {
    try {
      const meshes = await meshService.list(this._projectId)
      this._meshes = meshes
    } catch (error) {
      console.error('Failed to load meshes:', error)
    }
  }

  private async _loadSimulations() {
    try {
      const simulations = await simulationService.list(this._projectId)
      this._simulations = simulations
    } catch (error) {
      console.error('Failed to load simulations:', error)
    }
  }

  private _handleCreateMesh() {
    if (!this._meshConfig.name.trim()) return
    this._isCreating = true
    meshService.create(this._projectId, {
      name: this._meshConfig.name,
      config: {
        element_size: this._meshConfig.element_size,
        growth_rate: this._meshConfig.growth_rate,
        num_boundary_layers: this._meshConfig.num_boundary_layers,
      },
    }).then(() => {
      notify.success('Mesh generation started')
      this._showMeshModal = false
      this._meshConfig = { name: '', element_size: 0.01, growth_rate: 1.2, num_boundary_layers: 3 }
      this._loadMeshes()
    }).catch(() => {
      notify.error('Failed to start mesh generation')
    }).finally(() => {
      this._isCreating = false
    })
  }

  private _handleCreateSimulation() {
    if (!this._simConfig.name.trim()) return
    this._isCreating = true
    simulationService.create(this._projectId, {
      name: this._simConfig.name,
      config: {
        end_time: this._simConfig.end_time,
        write_interval: this._simConfig.write_interval,
        residual_print: this._simConfig.residual_print,
      },
    }).then(() => {
      notify.success('Simulation started')
      this._showSimModal = false
      this._simConfig = { name: '', end_time: 1.0, write_interval: 0.05, residual_print: true }
      this._loadSimulations()
    }).catch(() => {
      notify.error('Failed to start simulation')
    }).finally(() => {
      this._isCreating = false
    })
  }

  private _getStatusClass(status: string) {
    switch (status) {
      case 'completed': return 'status-completed'
      case 'running': case 'generating': return 'status-running'
      case 'failed': return 'status-failed'
      default: return 'status-pending'
    }
  }

  render() {
    const { _project, _meshes, _simulations, _isLoading, _activeTab, _showMeshModal, _showSimModal, _meshConfig, _simConfig, _isCreating } = this

    return html`
      <div class="project-container">
        <div class="header">
          <div>
            <h1 class="text-2xl font-bold">${_project?.name || 'Project'}</h1>
            ${_project?.description ? html`<p class="text-gray-500">${_project.description}</p>` : ''}
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-secondary" @click=${() => window.location.href = '/projects'}>
              Back to Projects
            </button>
            <button class="btn btn-primary" @click=${() => window.location.href = `/upload?project=${this._projectId}`}>
              Upload Geometry
            </button>
          </div>
        </div>

        ${_isLoading ? html`
          <div class="loading">
            <div class="spinner"></div>
          </div>
        ` : html`
          <div class="card">
            <div class="tabs">
              <div
                class="tab ${_activeTab === 'meshes' ? 'active' : ''}"
                @click=${() => this._activeTab = 'meshes'}
              >
                Meshes (${_meshes.length})
              </div>
              <div
                class="tab ${_activeTab === 'simulations' ? 'active' : ''}"
                @click=${() => this._activeTab = 'simulations'}
              >
                Simulations (${_simulations.length})
              </div>
            </div>

            ${_activeTab === 'meshes' ? html`
              <div>
                <div style="display: flex; justify-content: flex-end; margin-bottom: 16px;">
                  <button class="btn btn-primary" @click=${() => this._showMeshModal = true}>
                    Generate Mesh
                  </button>
                </div>
                ${_meshes.length === 0 ? html`
                  <div class="empty-state">No meshes yet.</div>
                ` : html`
                  <table class="table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Status</th>
                        <th>Cells</th>
                        <th>Points</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${_meshes.map(mesh => html`
                        <tr>
                          <td class="font-medium">${mesh.name}</td>
                          <td>
                            <span class="status-badge ${this._getStatusClass(mesh.status)}">
                              ${mesh.status}
                            </span>
                          </td>
                          <td>${mesh.num_cells?.toLocaleString() || '-'}</td>
                          <td>${mesh.num_points?.toLocaleString() || '-'}</td>
                          <td>${mesh.created_at ? new Date(mesh.created_at).toLocaleDateString() : '-'}</td>
                        </tr>
                      `)}
                    </tbody>
                  </table>
                `}
              </div>
            ` : html`
              <div>
                <div style="display: flex; justify-content: flex-end; margin-bottom: 16px;">
                  <button class="btn btn-primary" @click=${() => this._showSimModal = true}>
                    New Simulation
                  </button>
                </div>
                ${_simulations.length === 0 ? html`
                  <div class="empty-state">No simulations yet.</div>
                ` : html`
                  <table class="table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Status</th>
                        <th>Mesh</th>
                        <th>Time</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${_simulations.map(sim => html`
                        <tr>
                          <td class="font-medium">${sim.name}</td>
                          <td>
                            <span class="status-badge ${this._getStatusClass(sim.status)}">
                              ${sim.status}
                            </span>
                          </td>
                          <td>${sim.mesh_id || '-'}</td>
                          <td>${sim.current_time?.toFixed(2) || '0.00'}s</td>
                          <td>${sim.created_at ? new Date(sim.created_at).toLocaleDateString() : '-'}</td>
                        </tr>
                      `)}
                    </tbody>
                  </table>
                `}
              </div>
            `}
          </div>
        `}

        <!-- Mesh Modal -->
        ${_showMeshModal ? html`
          <div class="modal-overlay" @click=${(e: Event) => e.target === e.currentTarget && (this._showMeshModal = false)}>
            <div class="modal">
              <h2>Generate Mesh</h2>
              <div class="form-group">
                <label>Mesh name</label>
                <input
                  type="text"
                  placeholder="Mesh name"
                  .value=${_meshConfig.name}
                  @input=${(e: Event) => this._meshConfig = { ...this._meshConfig, name: (e.target as HTMLInputElement).value }}
                />
              </div>
              <div class="form-grid">
                <div class="form-group">
                  <label>Element Size</label>
                  <input
                    type="number"
                    .value=${String(_meshConfig.element_size)}
                    @input=${(e: Event) => this._meshConfig = { ...this._meshConfig, element_size: parseFloat((e.target as HTMLInputElement).value) }}
                    step="0.001"
                  />
                </div>
                <div class="form-group">
                  <label>Growth Rate</label>
                  <input
                    type="number"
                    .value=${String(_meshConfig.growth_rate)}
                    @input=${(e: Event) => this._meshConfig = { ...this._meshConfig, growth_rate: parseFloat((e.target as HTMLInputElement).value) }}
                    step="0.1"
                  />
                </div>
              </div>
              <div class="form-group">
                <label>Boundary Layers</label>
                <input
                  type="number"
                  .value=${String(_meshConfig.num_boundary_layers)}
                  @input=${(e: Event) => this._meshConfig = { ...this._meshConfig, num_boundary_layers: parseInt((e.target as HTMLInputElement).value) }}
                  min="0"
                />
              </div>
              <div class="modal-actions">
                <button class="btn btn-secondary" @click=${() => this._showMeshModal = false}>Cancel</button>
                <button
                  class="btn btn-primary"
                  @click=${this._handleCreateMesh}
                  ?disabled=${_isCreating || !_meshConfig.name.trim()}
                >
                  ${_isCreating ? 'Creating...' : 'Generate'}
                </button>
              </div>
            </div>
          </div>
        ` : ''}

        <!-- Simulation Modal -->
        ${_showSimModal ? html`
          <div class="modal-overlay" @click=${(e: Event) => e.target === e.currentTarget && (this._showSimModal = false)}>
            <div class="modal">
              <h2>New Simulation</h2>
              <div class="form-group">
                <label>Simulation name</label>
                <input
                  type="text"
                  placeholder="Simulation name"
                  .value=${_simConfig.name}
                  @input=${(e: Event) => this._simConfig = { ...this._simConfig, name: (e.target as HTMLInputElement).value }}
                />
              </div>
              <div class="form-grid">
                <div class="form-group">
                  <label>End Time</label>
                  <input
                    type="number"
                    .value=${String(_simConfig.end_time)}
                    @input=${(e: Event) => this._simConfig = { ...this._simConfig, end_time: parseFloat((e.target as HTMLInputElement).value) }}
                    step="0.1"
                  />
                </div>
                <div class="form-group">
                  <label>Write Interval</label>
                  <input
                    type="number"
                    .value=${String(_simConfig.write_interval)}
                    @input=${(e: Event) => this._simConfig = { ...this._simConfig, write_interval: parseFloat((e.target as HTMLInputElement).value) }}
                    step="0.01"
                  />
                </div>
              </div>
              <div class="modal-actions">
                <button class="btn btn-secondary" @click=${() => this._showSimModal = false}>Cancel</button>
                <button
                  class="btn btn-primary"
                  @click=${this._handleCreateSimulation}
                  ?disabled=${_isCreating || !_simConfig.name.trim()}
                >
                  ${_isCreating ? 'Creating...' : 'Create'}
                </button>
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
    'cfd-project-page': ProjectPage
  }
}
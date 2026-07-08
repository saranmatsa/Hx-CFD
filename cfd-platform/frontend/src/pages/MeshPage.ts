import { LitElement, html, css } from 'lit'
import { customElement, state } from 'lit/decorators.js'
import { CfdComponent } from '../components/base'
import { meshService, Mesh } from '../services/meshService'
import { projectService } from '../services/projectService'
import { notify } from '../services/notificationService'

@customElement('cfd-mesh-page')
export class MeshPage extends CfdComponent {
  static styles = css`
    ...super.styles,
    `
    .mesh-container {
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
    .btn-primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
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
    .status-generating { background: #fef3c7; color: #92400e; }
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
  `

  @state() private _meshes: Mesh[] = []
  @state() private _isLoading = true
  @state() private _isGenerating = false
  @state() private _showCreateModal = false
  @state() private _newMeshName = ''
  @state() private _config = {
    element_size: 0.01,
    growth_rate: 1.2,
    num_boundary_layers: 3,
  }

  private _projectId: string = ''
  private _pollInterval: number | null = null

  connectedCallback() {
    super.connectedCallback()
    const params = new URLSearchParams(window.location.search)
    this._projectId = params.get('project') || ''
    this._loadMeshes()
    this._startPolling()
  }

  disconnectedCallback() {
    super.disconnectedCallback()
    this._stopPolling()
  }

  private _startPolling() {
    this._pollInterval = window.setInterval(() => {
      this._loadMeshes()
    }, 5000)
  }

  private _stopPolling() {
    if (this._pollInterval) {
      clearInterval(this._pollInterval)
      this._pollInterval = null
    }
  }

  private async _loadMeshes() {
    try {
      const meshes = await meshService.list(this._projectId)
      this._meshes = meshes
      this._isLoading = false
    } catch (error) {
      console.error('Failed to load meshes:', error)
      this._isLoading = false
    }
  }

  private _handleCreateMesh() {
    if (!this._newMeshName.trim()) return
    this._isGenerating = true
    meshService.create(this._projectId, {
      name: this._newMeshName,
      config: this._config,
    }).then(() => {
      notify.success('Mesh generation started')
      this._showCreateModal = false
      this._newMeshName = ''
      this._loadMeshes()
    }).catch((error) => {
      notify.error('Failed to start mesh generation')
    }).finally(() => {
      this._isGenerating = false
    })
  }

  private _getStatusClass(status: string) {
    switch (status) {
      case 'completed': return 'status-completed'
      case 'generating': return 'status-generating'
      case 'failed': return 'status-failed'
      default: return 'status-pending'
    }
  }

  render() {
    return html`
      <div class="mesh-container">
        <div class="header">
          <h1 class="text-2xl font-bold">Mesh Generation</h1>
          <button class="btn btn-primary" @click=${() => this._showCreateModal = true}>
            Generate New Mesh
          </button>
        </div>

        <!-- Configuration Card -->
        <div class="card">
          <h2>Default Configuration</h2>
          <div class="form-grid">
            <div class="form-group">
              <label>Element Size</label>
              <input
                type="number"
                .value=${String(this._config.element_size)}
                @input=${(e: Event) => this._config = { ...this._config, element_size: parseFloat((e.target as HTMLInputElement).value) }}
                step="0.001"
                min="0.0001"
              />
            </div>
            <div class="form-group">
              <label>Growth Rate</label>
              <input
                type="number"
                .value=${String(this._config.growth_rate)}
                @input=${(e: Event) => this._config = { ...this._config, growth_rate: parseFloat((e.target as HTMLInputElement).value) }}
                step="0.1"
                min="1"
                max="2"
              />
            </div>
            <div class="form-group">
              <label>Boundary Layers</label>
              <input
                type="number"
                .value=${String(this._config.num_boundary_layers)}
                @input=${(e: Event) => this._config = { ...this._config, num_boundary_layers: parseInt((e.target as HTMLInputElement).value) }}
                min="0"
                max="10"
              />
            </div>
          </div>
        </div>

        <!-- Meshes Table -->
        <div class="card">
          <h2>Meshes</h2>
          ${this._isLoading ? html`
            <div class="empty-state">Loading...</div>
          ` : this._meshes.length === 0 ? html`
            <div class="empty-state">No meshes yet. Create one to get started.</div>
          ` : html`
            <table class="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Cells</th>
                  <th>Points</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                ${this._meshes.map(mesh => html`
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
                    <td>
                      ${mesh.status === 'completed' ? html`
                        <button class="btn btn-secondary" @click=${() => this._exportMesh(mesh.id)}>
                          Export
                        </button>
                      ` : ''}
                    </td>
                  </tr>
                `)}
              </tbody>
            </table>
          `}
        </div>

        <!-- Create Modal -->
        ${this._showCreateModal ? html`
          <div class="modal-overlay" @click=${(e: Event) => e.target === e.currentTarget && (this._showCreateModal = false)}>
            <div class="modal">
              <h2>Generate New Mesh</h2>
              <div class="form-group">
                <label>Mesh name</label>
                <input
                  type="text"
                  placeholder="Mesh name"
                  .value=${this._newMeshName}
                  @input=${(e: Event) => this._newMeshName = (e.target as HTMLInputElement).value}
                />
              </div>
              <div class="modal-actions">
                <button class="btn btn-secondary" @click=${() => this._showCreateModal = false}>
                  Cancel
                </button>
                <button
                  class="btn btn-primary"
                  @click=${this._handleCreateMesh}
                  ?disabled=${this._isGenerating || !this._newMeshName.trim()}
                >
                  ${this._isGenerating ? 'Generating...' : 'Generate'}
                </button>
              </div>
            </div>
          </div>
        ` : ''}
      </div>
    `
  }

  private async _exportMesh(meshId: string) {
    try {
      const blob = await meshService.export(meshId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `mesh-${meshId}.vtk`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      notify.error('Failed to export mesh')
    }
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'cfd-mesh-page': MeshPage
  }
}
import { LitElement, html, css } from 'lit'
import { customElement, state } from 'lit/decorators.js'
import { CfdComponent } from '../components/base'
import { optimizationService, Optimization } from '../services/optimizationService'
import { notify } from '../services/notificationService'

interface OptimizationConfig {
  algorithm: string
  num_variables: number
  num_objectives: number
  max_iterations: number
}

@customElement('cfd-optimization-page')
export class OptimizationPage extends CfdComponent {
  static styles = css`
    ...super.styles,
    `
    .optimization-container {
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
    .btn-danger {
      background: #dc2626;
      border: none;
      color: white;
    }
    .btn-danger:hover:not(:disabled) {
      background: #b91c1c;
    }
    .btn-sm {
      padding: 4px 8px;
      font-size: 12px;
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
    .status-running { background: #dbeafe; color: #1e40af; }
    .status-pending { background: #f3f4f6; color: #4b5563; }
    .status-failed { background: #fee2e2; color: #991b1b; }
    .progress-bar {
      width: 100%;
      height: 8px;
      background: #e5e7eb;
      border-radius: 4px;
      overflow: hidden;
    }
    .progress-fill {
      height: 100%;
      background: #2563eb;
      transition: width 0.3s;
    }
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

  @state() private _optimizations: Optimization[] = []
  @state() private _isLoading = true
  @state() private _showCreateModal = false
  @state() private _isCreating = false
  @state() private _newOptimization = {
    name: '',
    algorithm: 'Nelder-Mead',
    num_variables: 2,
    num_objectives: 1,
    max_iterations: 100,
  }

  private _pollInterval: number | null = null

  connectedCallback() {
    super.connectedCallback()
    this._loadOptimizations()
    this._startPolling()
  }

  disconnectedCallback() {
    super.disconnectedCallback()
    this._stopPolling()
  }

  private _startPolling() {
    this._pollInterval = window.setInterval(() => {
      this._loadOptimizations()
    }, 5000)
  }

  private _stopPolling() {
    if (this._pollInterval) {
      clearInterval(this._pollInterval)
      this._pollInterval = null
    }
  }

  private async _loadOptimizations() {
    try {
      const optimizations = await optimizationService.list()
      this._optimizations = optimizations
      this._isLoading = false
    } catch (error) {
      console.error('Failed to load optimizations:', error)
      this._isLoading = false
    }
  }

  private _handleCreateOptimization() {
    if (!this._newOptimization.name.trim()) return
    this._isCreating = true
    optimizationService.create(this._newOptimization).then(() => {
      notify.success('Optimization started')
      this._showCreateModal = false
      this._newOptimization = {
        name: '',
        algorithm: 'Nelder-Mead',
        num_variables: 2,
        num_objectives: 1,
        max_iterations: 100,
      }
      this._loadOptimizations()
    }).catch((error) => {
      notify.error('Failed to start optimization')
    }).finally(() => {
      this._isCreating = false
    })
  }

  private _handleStopOptimization(id: string) {
    optimizationService.stop(id).then(() => {
      notify.success('Optimization stopped')
      this._loadOptimizations()
    }).catch(() => {
      notify.error('Failed to stop optimization')
    })
  }

  private _handleDeleteOptimization(id: string) {
    if (!confirm('Are you sure you want to delete this optimization?')) return
    optimizationService.delete(id).then(() => {
      notify.success('Optimization deleted')
      this._loadOptimizations()
    }).catch(() => {
      notify.error('Failed to delete optimization')
    })
  }

  private _getStatusClass(status: string) {
    switch (status) {
      case 'completed': return 'status-completed'
      case 'running': return 'status-running'
      case 'failed': return 'status-failed'
      default: return 'status-pending'
    }
  }

  private _getAlgorithmLabel(algorithm: string) {
    const labels: Record<string, string> = {
      'Nelder-Mead': 'Nelder-Mead',
      'COBYLA': 'COBYLA',
      'Powell': 'Powell',
      'DE': 'Differential Evolution',
      'CMA-ES': 'CMA-ES',
      'NSGA-II': 'NSGA-II',
    }
    return labels[algorithm] || algorithm
  }

  render() {
    const { _optimizations, _isLoading, _showCreateModal, _newOptimization, _isCreating } = this

    return html`
      <div class="optimization-container">
        <div class="header">
          <h1 class="text-2xl font-bold">Design Optimization</h1>
          <button class="btn btn-primary" @click=${() => this._showCreateModal = true}>
            New Optimization
          </button>
        </div>

        <!-- Optimizations Table -->
        <div class="card">
          <h2>Optimizations</h2>
          ${_isLoading ? html`
            <div class="empty-state">Loading...</div>
          ` : _optimizations.length === 0 ? html`
            <div class="empty-state">No optimizations yet. Create one to get started.</div>
          ` : html`
            <table class="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Algorithm</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>Best Objective</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                ${_optimizations.map(opt => html`
                  <tr>
                    <td class="font-medium">${opt.name}</td>
                    <td>${this._getAlgorithmLabel(opt.algorithm)}</td>
                    <td>
                      <span class="status-badge ${this._getStatusClass(opt.status)}">
                        ${opt.status}
                      </span>
                    </td>
                    <td style="width: 150px">
                      <div class="progress-bar">
                        <div class="progress-fill" style="width: ${opt.progress || 0}%"></div>
                      </div>
                      <span class="text-sm text-gray-500">${opt.progress || 0}%</span>
                    </td>
                    <td>${opt.best_objective !== undefined ? opt.best_objective.toFixed(4) : '-'}</td>
                    <td>
                      <div style="display: flex; gap: 8px;">
                        ${opt.status === 'running' ? html`
                          <button class="btn btn-sm btn-secondary" @click=${() => this._handleStopOptimization(opt.id)}>
                            Stop
                          </button>
                        ` : ''}
                        <button class="btn btn-sm btn-danger" @click=${() => this._handleDeleteOptimization(opt.id)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                `)}
              </tbody>
            </table>
          `}
        </div>

        <!-- Create Modal -->
        ${_showCreateModal ? html`
          <div class="modal-overlay" @click=${(e: Event) => e.target === e.currentTarget && (this._showCreateModal = false)}>
            <div class="modal">
              <h2>New Optimization</h2>
              <div class="form-group">
                <label>Name</label>
                <input
                  type="text"
                  placeholder="Optimization name"
                  .value=${_newOptimization.name}
                  @input=${(e: Event) => this._newOptimization = { ...this._newOptimization, name: (e.target as HTMLInputElement).value }}
                />
              </div>
              <div class="form-group">
                <label>Algorithm</label>
                <select
                  .value=${_newOptimization.algorithm}
                  @change=${(e: Event) => this._newOptimization = { ...this._newOptimization, algorithm: (e.target as HTMLSelectElement).value }}
                >
                  <option value="Nelder-Mead">Nelder-Mead</option>
                  <option value="COBYLA">COBYLA</option>
                  <option value="Powell">Powell</option>
                  <option value="DE">Differential Evolution</option>
                  <option value="CMA-ES">CMA-ES</option>
                  <option value="NSGA-II">NSGA-II</option>
                </select>
              </div>
              <div class="form-grid">
                <div class="form-group">
                  <label>Variables</label>
                  <input
                    type="number"
                    .value=${String(_newOptimization.num_variables)}
                    @input=${(e: Event) => this._newOptimization = { ...this._newOptimization, num_variables: parseInt((e.target as HTMLInputElement).value) }}
                    min="1"
                    max="50"
                  />
                </div>
                <div class="form-group">
                  <label>Objectives</label>
                  <input
                    type="number"
                    .value=${String(_newOptimization.num_objectives)}
                    @input=${(e: Event) => this._newOptimization = { ...this._newOptimization, num_objectives: parseInt((e.target as HTMLInputElement).value) }}
                    min="1"
                    max="10"
                  />
                </div>
              </div>
              <div class="form-group">
                <label>Max Iterations</label>
                <input
                  type="number"
                  .value=${String(_newOptimization.max_iterations)}
                  @input=${(e: Event) => this._newOptimization = { ...this._newOptimization, max_iterations: parseInt((e.target as HTMLInputElement).value) }}
                  min="1"
                />
              </div>
              <div class="modal-actions">
                <button class="btn btn-secondary" @click=${() => this._showCreateModal = false}>
                  Cancel
                </button>
                <button
                  class="btn btn-primary"
                  @click=${this._handleCreateOptimization}
                  ?disabled=${_isCreating || !_newOptimization.name.trim()}
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
    'cfd-optimization-page': OptimizationPage
  }
}
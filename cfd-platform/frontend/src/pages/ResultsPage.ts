import { LitElement, html, css } from 'lit'
import { customElement, state } from 'lit/decorators.js'
import { CfdComponent } from '../components/base'
import { pipelineService, Pipeline } from '../services/pipelineService'
import { notify } from '../services/notificationService'

interface SimulationResult {
  id: string
  name: string
  status: string
  mesh_id: string
  current_time: number
  end_time: number
  residuals?: Record<string, number>
  statistics?: Record<string, { min: number; max: number; mean: number }>
}

@customElement('cfd-results-page')
export class ResultsPage extends CfdComponent {
  static styles = css`
    ...super.styles,
    `
    .results-container {
      display: flex;
      height: 100vh;
      overflow: hidden;
    }
    .sidebar {
      width: 280px;
      background: white;
      border-right: 1px solid #e5e7eb;
      display: flex;
      flex-direction: column;
    }
    .sidebar-header {
      padding: 16px;
      border-bottom: 1px solid #e5e7eb;
    }
    .sidebar-header h2 {
      font-size: 16px;
      font-weight: 600;
    }
    .sidebar-content {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }
    .field-group {
      margin-bottom: 16px;
    }
    .field-group h3 {
      font-size: 12px;
      font-weight: 500;
      color: #6b7280;
      text-transform: uppercase;
      margin-bottom: 8px;
    }
    .field-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
    }
    .field-item:hover {
      background: #f3f4f6;
    }
    .field-item.selected {
      background: #dbeafe;
      color: #1e40af;
    }
    .field-color {
      width: 12px;
      height: 12px;
      border-radius: 2px;
    }
    .main-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .tabs {
      display: flex;
      background: white;
      border-bottom: 1px solid #e5e7eb;
      padding: 0 16px;
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
    .viewer-container {
      flex: 1;
      position: relative;
      background: #1a1a2e;
    }
    .viewer-3d {
      width: 100%;
      height: 100%;
    }
    .residuals-container {
      flex: 1;
      padding: 24px;
      overflow-y: auto;
      background: white;
    }
    .residuals-chart {
      background: white;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
    }
    .residual-item {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 12px 0;
      border-bottom: 1px solid #e5e7eb;
    }
    .residual-name {
      width: 80px;
      font-weight: 500;
    }
    .residual-value {
      flex: 1;
      height: 8px;
      background: #e5e7eb;
      border-radius: 4px;
      overflow: hidden;
    }
    .residual-fill {
      height: 100%;
      background: #2563eb;
    }
    .residual-number {
      width: 100px;
      text-align: right;
      font-family: monospace;
      font-size: 14px;
    }
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
    }
    .stat-card {
      background: white;
      border-radius: 8px;
      padding: 16px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .stat-card h4 {
      font-size: 12px;
      font-weight: 500;
      color: #6b7280;
      text-transform: uppercase;
      margin-bottom: 8px;
    }
    .stat-value {
      font-size: 24px;
      font-weight: 600;
    }
    .stat-row {
      display: flex;
      justify-content: space-between;
      padding: 4px 0;
      font-size: 14px;
    }
    .stat-label {
      color: #6b7280;
    }
    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #6b7280;
    }
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #6b7280;
    }
  `

  @state() private _simulation: SimulationResult | null = null
  @state() private _isLoading = true
  @state() private _activeTab: 'visualization' | 'residuals' | 'statistics' = 'visualization'
  @state() private _selectedField = 'p'
  @state() private _availableFields = ['p', 'U', 'T', 'k', 'epsilon']

  private _simulationId: string = ''
  private _pollInterval: number | null = null

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
      const simulation = await pipelineService.getSimulation(this._simulationId)
      this._simulation = simulation as SimulationResult
      this._isLoading = false
    } catch (error) {
      console.error('Failed to load simulation:', error)
      this._isLoading = false
    }
  }

  private _getFieldColor(field: string): string {
    const colors: Record<string, string> = {
      p: '#2563eb',
      U: '#dc2626',
      T: '#f59e0b',
      k: '#10b981',
      epsilon: '#8b5cf6',
    }
    return colors[field] || '#6b7280'
  }

  private _getFieldLabel(field: string): string {
    const labels: Record<string, string> = {
      p: 'Pressure (p)',
      U: 'Velocity (U)',
      T: 'Temperature (T)',
      k: 'Turbulent Kinetic Energy (k)',
      epsilon: 'Dissipation Rate (ε)',
    }
    return labels[field] || field
  }

  private _getResidualColor(value: number): string {
    if (value < 1e-3) return '#10b981'
    if (value < 1e-1) return '#f59e0b'
    return '#dc2626'
  }

  render() {
    const { _simulation, _isLoading, _activeTab, _selectedField, _availableFields } = this

    return html`
      <div class="results-container">
        <!-- Sidebar -->
        <div class="sidebar">
          <div class="sidebar-header">
            <h2>Results</h2>
            ${_simulation ? html`<p class="text-sm text-gray-500">${_simulation.name}</p>` : ''}
          </div>
          <div class="sidebar-content">
            <div class="field-group">
              <h3>Field Selection</h3>
              ${_availableFields.map(field => html`
                <div
                  class="field-item ${_selectedField === field ? 'selected' : ''}"
                  @click=${() => this._selectedField = field}
                >
                  <div class="field-color" style="background: ${this._getFieldColor(field)}"></div>
                  <span>${this._getFieldLabel(field)}</span>
                </div>
              `)}
            </div>
          </div>
        </div>

        <!-- Main Content -->
        <div class="main-content">
          <div class="tabs">
            <div
              class="tab ${_activeTab === 'visualization' ? 'active' : ''}"
              @click=${() => this._activeTab = 'visualization'}
            >
              Visualization
            </div>
            <div
              class="tab ${_activeTab === 'residuals' ? 'active' : ''}"
              @click=${() => this._activeTab = 'residuals'}
            >
              Residuals
            </div>
            <div
              class="tab ${_activeTab === 'statistics' ? 'active' : ''}"
              @click=${() => this._activeTab = 'statistics'}
            >
              Statistics
            </div>
          </div>

          ${_isLoading ? html`
            <div class="loading">Loading...</div>
          ` : !_simulation ? html`
            <div class="empty-state">
              <p>Simulation not found</p>
            </div>
          ` : _activeTab === 'visualization' ? html`
            <div class="viewer-container">
              <viewer-3d
                class="viewer-3d"
                .simulationId=${this._simulationId}
                .field=${_selectedField}
              ></viewer-3d>
            </div>
          ` : _activeTab === 'residuals' ? html`
            <div class="residuals-container">
              <h2 class="text-lg font-semibold mb-4">Solver Residuals</h2>
              ${_simulation.residuals ? html`
                <div class="residuals-chart">
                  ${Object.entries(_simulation.residuals).map(([name, value]) => html`
                    <div class="residual-item">
                      <div class="residual-name">${name}</div>
                      <div class="residual-value">
                        <div
                          class="residual-fill"
                          style="width: ${Math.min(100, Math.max(0, -Math.log10(value || 1e-10) * 10))}%; background: ${this._getResidualColor(value)}"
                        ></div>
                      </div>
                      <div class="residual-number">${value?.toExponential(2) || '-'}</div>
                    </div>
                  `)}
                </div>
              ` : html`
                <div class="empty-state">No residual data available</div>
              `}
            </div>
          ` : html`
            <div class="residuals-container">
              <h2 class="text-lg font-semibold mb-4">Field Statistics</h2>
              ${_simulation.statistics && _simulation.statistics[_selectedField] ? html`
                <div class="stats-grid">
                  <div class="stat-card">
                    <h4>Minimum</h4>
                    <div class="stat-value">${_simulation.statistics[_selectedField].min.toFixed(4)}</div>
                  </div>
                  <div class="stat-card">
                    <h4>Maximum</h4>
                    <div class="stat-value">${_simulation.statistics[_selectedField].max.toFixed(4)}</div>
                  </div>
                  <div class="stat-card">
                    <h4>Mean</h4>
                    <div class="stat-value">${_simulation.statistics[_selectedField].mean.toFixed(4)}</div>
                  </div>
                  <div class="stat-card">
                    <h4>Range</h4>
                    <div class="stat-value">${(_simulation.statistics[_selectedField].max - _simulation.statistics[_selectedField].min).toFixed(4)}</div>
                  </div>
                </div>
              ` : html`
                <div class="empty-state">No statistics available for ${this._getFieldLabel(_selectedField)}</div>
              `}
            </div>
          `}
        </div>
      </div>
    `
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'cfd-results-page': ResultsPage
  }
}
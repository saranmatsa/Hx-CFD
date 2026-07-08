import { LitElement, html, css } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'
import { CfdComponent } from './base'

interface Optimization {
  id: string
  name: string
  algorithm: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress?: number
  best_objective?: number
}

@customElement('optimization-panel')
export class OptimizationPanel extends CfdComponent {
  static styles = css`
    :host {
      display: block;
    }
    .panel {
      background: white;
      border-radius: 0.5rem;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
      padding: 1rem;
    }
    .empty {
      background: #f3f4f6;
      border-radius: 0.5rem;
      padding: 1rem;
      color: #6b7280;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1rem;
    }
    .title {
      font-weight: 600;
      font-size: 1.125rem;
    }
    .subtitle {
      font-size: 0.875rem;
      color: #6b7280;
    }
    .status {
      padding: 0.25rem 0.5rem;
      border-radius: 0.25rem;
      font-size: 0.875rem;
    }
    .status.completed { color: #10b981; }
    .status.running { color: #f59e0b; }
    .status.failed { color: #ef4444; }
    .status.pending { color: #6b7280; }
    .section {
      margin-bottom: 1rem;
    }
    .label {
      display: block;
      font-size: 0.875rem;
      font-weight: 500;
      color: #374151;
      margin-bottom: 0.25rem;
    }
    .progress-bar {
      width: 100%;
      background: #e5e7eb;
      border-radius: 9999px;
      height: 0.5rem;
    }
    .progress-fill {
      background: #2563eb;
      height: 0.5rem;
      border-radius: 9999px;
      transition: width 0.3s ease;
    }
    .progress-text {
      font-size: 0.875rem;
      color: #6b7280;
      margin-top: 0.25rem;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }
    .value {
      font-size: 1.125rem;
      font-family: monospace;
    }
    input[type="range"] {
      width: 100%;
    }
    .actions {
      display: flex;
      gap: 0.5rem;
    }
    .btn {
      flex: 1;
      padding: 0.5rem 1rem;
      border-radius: 0.5rem;
      color: white;
      border: none;
      cursor: pointer;
      font-weight: 500;
    }
    .btn-start {
      background: #059669;
    }
    .btn-start:hover {
      background: #047857;
    }
    .btn-delete {
      background: #dc2626;
    }
    .btn-delete:hover {
      background: #b91c1c;
    }
  `

  @property({ type: String }) optimizationId = ''
  @property({ type: String }) className = ''

  @state() private _optimizations: Optimization[] = []
  @state() private _selectedIteration = 0
  @state() private _isLoading = false

  // These would be connected to the optimization service
  // For now, using placeholder methods
  private startOptimization(id: string) {
    console.log('Start optimization:', id)
    // TODO: Connect to optimizationService
  }

  private deleteOptimization(id: string) {
    console.log('Delete optimization:', id)
    // TODO: Connect to optimizationService
  }

  private getStatusClass(status: string): string {
    switch (status) {
      case 'completed': return 'completed'
      case 'running': return 'running'
      case 'failed': return 'failed'
      default: return 'pending'
    }
  }

  render() {
    const optimization = this._optimizations.find(o => o.id === this.optimizationId)

    if (!optimization) {
      return html`
        <div class="empty ${this.className}">
          <p>Select an optimization to view details</p>
        </div>
      `
    }

    const progress = optimization.progress || 0

    return html`
      <div class="panel ${this.className}">
        <div class="header">
          <div>
            <h3 class="title">${optimization.name}</h3>
            <p class="subtitle">${optimization.algorithm}</p>
          </div>
          <span class="status ${this.getStatusClass(optimization.status)}">
            ${optimization.status}
          </span>
        </div>

        <div class="section">
          <label class="label">Progress</label>
          <div class="progress-bar">
            <div class="progress-fill" style="width: ${progress * 100}%"></div>
          </div>
          <p class="progress-text">${(progress * 100).toFixed(1)}%</p>
        </div>

        <div class="section">
          <div class="grid">
            <div>
              <label class="label">Best Objective</label>
              <p class="value">${optimization.best_objective?.toFixed(6) || 'N/A'}</p>
            </div>
            <div>
              <label class="label">Iteration</label>
              <p class="value">${this._selectedIteration}</p>
            </div>
          </div>
        </div>

        <div class="section">
          <label class="label">Iteration Slider</label>
          <input
            type="range"
            min="0"
            max="100"
            .value="${this._selectedIteration}"
            @input="${(e: Event) => this._selectedIteration = parseInt((e.target as HTMLInputElement).value)}"
          />
        </div>

        <div class="actions">
          ${optimization.status === 'pending' ? html`
            <button
              class="btn btn-start"
              @click="${() => this.startOptimization(optimization.id)}"
            >
              Start
            </button>
          ` : ''}
          <button
            class="btn btn-delete"
            @click="${() => this.deleteOptimization(optimization.id)}"
          >
            Delete
          </button>
        </div>
      </div>
    `
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'optimization-panel': OptimizationPanel
  }
}
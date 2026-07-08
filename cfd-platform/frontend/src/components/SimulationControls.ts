import { LitElement, html, css } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'
import { CfdComponent } from './base'

type SimulationStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

interface SimulationStatusData {
  status: SimulationStatus
  progress: number
  current_stage?: string
}

@customElement('simulation-controls')
export class SimulationControls extends CfdComponent {
  static styles = css`
    :host {
      display: block;
    }
    .container {
      background: white;
      border-radius: 0.5rem;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid #e5e7eb;
    }
    .title {
      font-weight: 600;
    }
    .status-badge {
      padding: 0.25rem 0.5rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 500;
    }
    .status-badge.running {
      background: #dcfce7;
      color: #15803d;
    }
    .status-badge.completed {
      background: #dbeafe;
      color: #1d4ed8;
    }
    .status-badge.failed {
      background: #fee2e2;
      color: #dc2626;
    }
    .status-badge.pending,
    .status-badge.cancelled {
      background: #f3f4f6;
      color: #4b5563;
    }
    .progress-section {
      padding: 0.75rem 1rem;
      border-bottom: 1px solid #e5e7eb;
      background: #f9fafb;
    }
    .progress-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.5rem;
    }
    .stage {
      font-size: 0.875rem;
      color: #4b5563;
    }
    .progress-value {
      font-size: 0.875rem;
      color: #6b7280;
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
      transition: width 0.5s ease;
    }
    .actions {
      padding: 1rem;
    }
    .btn {
      width: 100%;
      padding: 0.5rem 1rem;
      border-radius: 0.375rem;
      color: white;
      border: none;
      cursor: pointer;
      font-weight: 500;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
    }
    .btn-cancel {
      background: #dc2626;
    }
    .btn-cancel:hover {
      background: #b91c1c;
    }
    .btn-cancel:disabled {
      background: #9ca3af;
      cursor: not-allowed;
    }
    .btn-restart {
      background: #2563eb;
    }
    .btn-restart:hover {
      background: #1d4ed8;
    }
    .btn-restart:disabled {
      background: #9ca3af;
      cursor: not-allowed;
    }
    .btn-settings {
      background: #6b7280;
    }
    .btn-settings:hover {
      background: #4b5563;
    }
    .space-y-3 > * + * {
      margin-top: 0.75rem;
    }
    .icon {
      width: 1.25rem;
      height: 1.25rem;
    }
  `

  @property({ type: String }) simulationId = ''
  @property({ type: String }) status: SimulationStatus = 'pending'

  @state() private _statusData: SimulationStatusData | null = null
  @state() private _showSettings = false
  @state() private _isCancelling = false
  @state() private _isRestarting = false
  @state() private _settings = {
    endTime: 100,
    writeInterval: 10,
    residualPrint: true,
  }

  // These would be connected to the pipeline/simulation service
  private async cancelSimulation() {
    this._isCancelling = true
    try {
      console.log('Cancel simulation:', this.simulationId)
      // TODO: Connect to pipelineService.cancel()
      this.dispatchEvent(new CustomEvent('status-change', { 
        detail: { status: 'cancelled' } 
      }))
    } finally {
      this._isCancelling = false
    }
  }

  private async restartSimulation() {
    this._isRestarting = true
    try {
      console.log('Restart simulation:', this.simulationId)
      // TODO: Connect to pipelineService.restart()
      this.dispatchEvent(new CustomEvent('status-change', { 
        detail: { status: 'running' } 
      }))
    } finally {
      this._isRestarting = false
    }
  }

  private getStatusClass(status: string): string {
    switch (status) {
      case 'running': return 'running'
      case 'completed': return 'completed'
      case 'failed': return 'failed'
      case 'cancelled': return 'cancelled'
      default: return 'pending'
    }
  }

  private formatStatus(status: string): string {
    return status.charAt(0).toUpperCase() + status.slice(1)
  }

  render() {
    const currentStatus = this._statusData?.status || this.status
    const progress = this._statusData?.progress || 0
    const stage = this._statusData?.current_stage

    return html`
      <div class="container">
        <!-- Header -->
        <div class="header">
          <h3 class="title">Simulation Controls</h3>
          <span class="status-badge ${this.getStatusClass(currentStatus)}">
            ${this.formatStatus(currentStatus)}
          </span>
        </div>

        <!-- Progress (only when running) -->
        ${currentStatus === 'running' ? html`
          <div class="progress-section">
            <div class="progress-header">
              <span class="stage">${stage || 'Processing...'}</span>
              <span class="progress-value">${progress}%</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" style="width: ${progress}%"></div>
            </div>
          </div>
        ` : ''}

        <!-- Actions -->
        <div class="actions space-y-3">
          ${currentStatus === 'running' ? html`
            <button
              class="btn btn-cancel"
              ?disabled="${this._isCancelling}"
              @click="${this.cancelSimulation}"
            >
              <svg class="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
              </svg>
              ${this._isCancelling ? 'Cancelling...' : 'Cancel Simulation'}
            </button>
          ` : ''}

          ${currentStatus === 'completed' || currentStatus === 'failed' || currentStatus === 'cancelled' ? html`
            <button
              class="btn btn-restart"
              ?disabled="${this._isRestarting}"
              @click="${this.restartSimulation}"
            >
              <svg class="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              ${this._isRestarting ? 'Restarting...' : 'Restart Simulation'}
            </button>
          ` : ''}

          <button
            class="btn btn-settings"
            @click="${() => this._showSettings = !this._showSettings}"
          >
            <svg class="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Settings
          </button>
        </div>
      </div>
    `
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'simulation-controls': SimulationControls
  }
}
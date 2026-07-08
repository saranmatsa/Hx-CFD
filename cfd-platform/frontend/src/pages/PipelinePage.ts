import { LitElement, html, css } from 'lit'
import { customElement, state } from 'lit/decorators.js'
import { CfdComponent } from '../components/base'
import { pipelineService, Pipeline, PipelineStage } from '../services/pipelineService'
import { notify } from '../services/notificationService'

@customElement('cfd-pipeline-page')
export class PipelinePage extends CfdComponent {
  static styles = css`
    ...super.styles,
    `
    .pipeline-container {
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
    .btn-secondary {
      background: white;
      border: 1px solid #d1d5db;
      color: #374151;
    }
    .btn-secondary:hover {
      background: #f9fafb;
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
    .pipeline-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .pipeline-item {
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 16px;
    }
    .pipeline-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .pipeline-title {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .pipeline-title h3 {
      font-size: 16px;
      font-weight: 600;
    }
    .pipeline-id {
      font-size: 12px;
      color: #6b7280;
      font-family: monospace;
    }
    .status-badge {
      display: inline-block;
      padding: 4px 8px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 500;
    }
    .status-running { background: #dbeafe; color: #1e40af; }
    .status-completed { background: #d1fae5; color: #065f46; }
    .status-failed { background: #fee2e2; color: #991b1b; }
    .status-pending { background: #f3f4f6; color: #4b5563; }
    .stages {
      display: flex;
      gap: 8px;
      margin-top: 12px;
    }
    .stage {
      flex: 1;
      padding: 12px;
      border-radius: 6px;
      text-align: center;
      font-size: 12px;
      font-weight: 500;
    }
    .stage-pending { background: #f3f4f6; color: #6b7280; }
    .stage-running { background: #dbeafe; color: #1e40af; }
    .stage-completed { background: #d1fae5; color: #065f46; }
    .stage-failed { background: #fee2e2; color: #991b1b; }
    .stage-icon {
      font-size: 16px;
      margin-bottom: 4px;
    }
    .pipeline-actions {
      display: flex;
      gap: 8px;
    }
    .empty-state {
      padding: 48px;
      text-align: center;
      color: #6b7280;
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

  @state() private _pipelines: Pipeline[] = []
  @state() private _isLoading = true

  private _pollInterval: number | null = null

  connectedCallback() {
    super.connectedCallback()
    this._loadPipelines()
    this._startPolling()
  }

  disconnectedCallback() {
    super.disconnectedCallback()
    this._stopPolling()
  }

  private _startPolling() {
    this._pollInterval = window.setInterval(() => {
      this._loadPipelines()
    }, 5000)
  }

  private _stopPolling() {
    if (this._pollInterval) {
      clearInterval(this._pollInterval)
      this._pollInterval = null
    }
  }

  private async _loadPipelines() {
    try {
      const pipelines = await pipelineService.list()
      this._pipelines = pipelines
      this._isLoading = false
    } catch (error) {
      console.error('Failed to load pipelines:', error)
      this._isLoading = false
    }
  }

  private _handleCancelPipeline(id: string) {
    pipelineService.cancel(id).then(() => {
      notify.success('Pipeline cancelled')
      this._loadPipelines()
    }).catch(() => {
      notify.error('Failed to cancel pipeline')
    })
  }

  private _handleRestartPipeline(id: string) {
    pipelineService.restart(id).then(() => {
      notify.success('Pipeline restarted')
      this._loadPipelines()
    }).catch(() => {
      notify.error('Failed to restart pipeline')
    })
  }

  private _handleDeletePipeline(id: string) {
    if (!confirm('Are you sure you want to delete this pipeline?')) return
    pipelineService.delete(id).then(() => {
      notify.success('Pipeline deleted')
      this._loadPipelines()
    }).catch(() => {
      notify.error('Failed to delete pipeline')
    })
  }

  private _getStageStatus(pipeline: Pipeline, stageName: string): string {
    const stageOrder = ['geometry', 'meshing', 'simulation', 'visualization']
    const currentStageIndex = stageOrder.indexOf(pipeline.current_stage || 'geometry')
    const stageIndex = stageOrder.indexOf(stageName)

    if (pipeline.status === 'failed') {
      return stageIndex === currentStageIndex ? 'failed' : stageIndex < currentStageIndex ? 'completed' : 'pending'
    }
    if (pipeline.status === 'completed') {
      return 'completed'
    }
    if (stageIndex < currentStageIndex) {
      return 'completed'
    }
    if (stageIndex === currentStageIndex) {
      return 'running'
    }
    return 'pending'
  }

  private _getStageIcon(stageName: string): string {
    const icons: Record<string, string> = {
      geometry: '📐',
      meshing: '🔲',
      simulation: '⚙️',
      visualization: '📊',
    }
    return icons[stageName] || '•'
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
    const { _pipelines, _isLoading } = this

    return html`
      <div class="pipeline-container">
        <div class="header">
          <h1 class="text-2xl font-bold">Pipeline Jobs</h1>
          <button class="btn btn-secondary" @click=${() => window.location.href = '/upload'}>
            New Pipeline
          </button>
        </div>

        <div class="card">
          ${_isLoading ? html`
            <div class="loading">
              <div class="spinner"></div>
            </div>
          ` : _pipelines.length === 0 ? html`
            <div class="empty-state">
              <p>No pipelines yet.</p>
              <button class="btn btn-secondary" style="margin-top: 16px" @click=${() => window.location.href = '/upload'}>
                Create your first pipeline
              </button>
            </div>
          ` : html`
            <div class="pipeline-list">
              ${_pipelines.map(pipeline => html`
                <div class="pipeline-item">
                  <div class="pipeline-header">
                    <div class="pipeline-title">
                      <h3>Pipeline ${pipeline.name || pipeline.id.slice(0, 8)}</h3>
                      <span class="pipeline-id">${pipeline.id}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                      <span class="status-badge ${this._getStatusClass(pipeline.status)}">
                        ${pipeline.status}
                      </span>
                      <div class="pipeline-actions">
                        ${pipeline.status === 'running' ? html`
                          <button class="btn btn-sm btn-secondary" @click=${() => this._handleCancelPipeline(pipeline.id)}>
                            Cancel
                          </button>
                        ` : ''}
                        ${pipeline.status === 'failed' || pipeline.status === 'completed' ? html`
                          <button class="btn btn-sm btn-secondary" @click=${() => this._handleRestartPipeline(pipeline.id)}>
                            Restart
                          </button>
                        ` : ''}
                        <button class="btn btn-sm btn-danger" @click=${() => this._handleDeletePipeline(pipeline.id)}>
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>

                  <div class="stages">
                    ${['geometry', 'meshing', 'simulation', 'visualization'].map(stage => {
                      const stageStatus = this._getStageStatus(pipeline, stage)
                      return html`
                        <div class="stage stage-${stageStatus}">
                          <div class="stage-icon">${this._getStageIcon(stage)}</div>
                          <div>${stage.charAt(0).toUpperCase() + stage.slice(1)}</div>
                        </div>
                      `
                    })}
                  </div>
                </div>
              `)}
            </div>
          `}
        </div>
      </div>
    `
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'cfd-pipeline-page': PipelinePage
  }
}
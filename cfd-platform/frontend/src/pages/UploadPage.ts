import { LitElement, html, css } from 'lit'
import { customElement, state } from 'lit/decorators.js'
import { CfdComponent } from '../components/base'
import { pipelineService, PipelineConfig } from '../services/pipelineService'
import { projectService } from '../services/projectService'
import { notify } from '../services/notificationService'

interface UploadState {
  file: File | null
  config: PipelineConfig
  isUploading: boolean
  error: string | null
}

@customElement('cfd-upload-page')
export class UploadPage extends CfdComponent {
  static styles = css`
    ...super.styles,
    `
    .upload-container {
      max-width: 800px;
      margin: 0 auto;
      padding: 24px;
    }
    .drop-zone {
      border: 2px dashed #d1d5db;
      border-radius: 8px;
      padding: 48px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
    }
    .drop-zone:hover, .drop-zone.drag-over {
      border-color: #3b82f6;
      background: #eff6ff;
    }
    .form-section {
      background: white;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      padding: 24px;
      margin-bottom: 24px;
    }
    .form-section h2 {
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
    .checkbox-group {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .checkbox-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      cursor: pointer;
    }
    .checkbox-item:hover {
      background: #f9fafb;
    }
    .checkbox-item input {
      width: auto;
    }
    .button-group {
      display: flex;
      justify-content: flex-end;
      gap: 16px;
    }
    .btn {
      padding: 12px 24px;
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
    .btn-primary {
      background: #2563eb;
      border: 1px solid #2563eb;
      color: white;
    }
    .btn-primary:hover:not(:disabled) {
      background: #1d4ed8;
    }
    .btn-primary:disabled {
      background: #9ca3af;
      cursor: not-allowed;
    }
    .error-message {
      margin-top: 16px;
      padding: 16px;
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 6px;
      color: #b91c1c;
    }
    .spinner {
      display: inline-block;
      width: 20px;
      height: 20px;
      border: 2px solid #ffffff;
      border-radius: 50%;
      border-top-color: transparent;
      animation: spin 1s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `

  @state() private _state: UploadState = {
    file: null,
    config: {
      project_id: '',
      geometry_file: '',
      mesh: {
        element_size: 0.01,
        growth_rate: 1.2,
        num_boundary_layers: 3,
      },
      solver: {
        solver: 'simpleFoam',
        end_time: 1000,
      },
      visualization: {
        fields: ['p', 'U'],
      },
    },
    isUploading: false,
    error: null,
  }

  @state() private _dragOver = false

  private _projectId: string = ''

  connectedCallback() {
    super.connectedCallback()
    const params = new URLSearchParams(window.location.search)
    this._projectId = params.get('project') || ''
    if (this._projectId) {
      this._state = { ...this._state, config: { ...this._state.config, project_id: this._projectId } }
    }
  }

  private _handleDragOver(e: DragEvent) {
    e.preventDefault()
    this._dragOver = true
  }

  private _handleDragLeave(e: DragEvent) {
    e.preventDefault()
    this._dragOver = false
  }

  private _handleDrop(e: DragEvent) {
    e.preventDefault()
    this._dragOver = false
    const files = e.dataTransfer?.files
    if (files && files.length > 0) {
      this._handleFileSelect(files[0])
    }
  }

  private _handleFileInput(e: Event) {
    const input = e.target as HTMLInputElement
    if (input.files && input.files.length > 0) {
      this._handleFileSelect(input.files[0])
    }
  }

  private _handleFileSelect(file: File) {
    this._state = { ...this._state, file, error: null }
  }

  private _updateConfig<K extends keyof PipelineConfig>(key: K, value: PipelineConfig[K]) {
    this._state = {
      ...this._state,
      config: { ...this._state.config, [key]: value },
    }
  }

  private _updateMeshConfig(key: string, value: any) {
    this._state = {
      ...this._state,
      config: {
        ...this._state.config,
        mesh: { ...this._state.config.mesh, [key]: value },
      },
    }
  }

  private _updateSolverConfig(key: string, value: any) {
    this._state = {
      ...this._state,
      config: {
        ...this._state.config,
        solver: { ...this._state.config.solver, [key]: value },
      },
    }
  }

  private _toggleField(field: string) {
    const fields = this._state.config.visualization?.fields || []
    const newFields = fields.includes(field)
      ? fields.filter(f => f !== field)
      : [...fields, field]
    this._state = {
      ...this._state,
      config: {
        ...this._state.config,
        visualization: { ...this._state.config.visualization, fields: newFields },
      },
    }
  }

  private async _handleSubmit() {
    if (!this._state.file) {
      this._state = { ...this._state, error: 'Please select a file' }
      return
    }

    this._state = { ...this._state, isUploading: true, error: null }

    try {
      // Upload geometry file
      const formData = new FormData()
      formData.append('file', this._state.file)
      formData.append('project_id', this._state.config.project_id)

      const uploadResponse = await fetch('/api/v1/geometry/upload', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        body: formData,
      })

      if (!uploadResponse.ok) {
        throw new Error('Failed to upload geometry file')
      }

      const { geometry_id } = await uploadResponse.json()

      // Start pipeline
      const config: PipelineConfig = {
        ...this._state.config,
        geometry_file: geometry_id,
      }

      await pipelineService.start(config)
      notify.success('Pipeline started successfully')
      window.location.href = '/pipeline'
    } catch (error) {
      this._state = {
        ...this._state,
        isUploading: false,
        error: error instanceof Error ? error.message : 'Failed to start pipeline',
      }
    }
  }

  private _handleCancel() {
    window.location.href = this._projectId ? `/projects/${this._projectId}` : '/projects'
  }

  render() {
    const { file, config, isUploading, error } = this._state

    return html`
      <div class="upload-container">
        <h1 class="text-2xl font-bold mb-6">Upload Geometry</h1>

        <!-- Drop Zone -->
        <div
          class="drop-zone ${this._dragOver ? 'drag-over' : ''}"
          @dragover=${this._handleDragOver}
          @dragleave=${this._handleDragLeave}
          @drop=${this._handleDrop}
          @click=${() => (document.querySelector('#file-input') as HTMLInputElement)?.click()}
        >
          <input
            type="file"
            id="file-input"
            accept=".stl,.step,.stp,.obj,.iges,.igs"
            style="display: none"
            @change=${this._handleFileInput}
          />
          ${file ? html`
            <div class="text-blue-600">
              <svg class="w-12 h-12 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p class="font-medium">${file.name}</p>
              <p class="text-sm text-gray-500">${(file.size / 1024).toFixed(1)} KB</p>
            </div>
          ` : html`
            <div class="text-gray-500">
              <svg class="w-12 h-12 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p class="font-medium">Drop geometry file here or click to browse</p>
              <p class="text-sm">Supported formats: STL, STEP, OBJ, IGES</p>
            </div>
          `}
        </div>

        <!-- Mesh Configuration -->
        <div class="form-section">
          <h2>Mesh Configuration</h2>
          <div class="form-grid">
            <div class="form-group">
              <label>Element Size</label>
              <input
                type="number"
                .value=${String(config.mesh?.element_size || 0.01)}
                @input=${(e: Event) => this._updateMeshConfig('element_size', parseFloat((e.target as HTMLInputElement).value))}
                step="0.001"
                min="0.0001"
              />
            </div>
            <div class="form-group">
              <label>Growth Rate</label>
              <input
                type="number"
                .value=${String(config.mesh?.growth_rate || 1.2)}
                @input=${(e: Event) => this._updateMeshConfig('growth_rate', parseFloat((e.target as HTMLInputElement).value))}
                step="0.1"
                min="1"
                max="2"
              />
            </div>
            <div class="form-group">
              <label>Boundary Layers</label>
              <input
                type="number"
                .value=${String(config.mesh?.num_boundary_layers || 3)}
                @input=${(e: Event) => this._updateMeshConfig('num_boundary_layers', parseInt((e.target as HTMLInputElement).value))}
                min="0"
                max="10"
              />
            </div>
          </div>
        </div>

        <!-- Solver Configuration -->
        <div class="form-section">
          <h2>Solver Configuration</h2>
          <div class="form-grid">
            <div class="form-group">
              <label>Solver</label>
              <select
                .value=${config.solver?.solver || 'simpleFoam'}
                @change=${(e: Event) => this._updateSolverConfig('solver', (e.target as HTMLSelectElement).value)}
              >
                <option value="simpleFoam">simpleFoam (Steady-state)</option>
                <option value="icoFoam">icoFoam (Transient, incompressible)</option>
                <option value="pisoFoam">pisoFoam (Transient, incompressible)</option>
                <option value="pimpleFoam">pimpleFoam (Transient, RANS/LES)</option>
                <option value="buoyantSimpleFoam">buoyantSimpleFoam (Buoyancy)</option>
              </select>
            </div>
            <div class="form-group">
              <label>End Time</label>
              <input
                type="number"
                .value=${String(config.solver?.end_time || 1000)}
                @input=${(e: Event) => this._updateSolverConfig('end_time', parseFloat((e.target as HTMLInputElement).value))}
                min="0"
              />
            </div>
          </div>
        </div>

        <!-- Visualization Fields -->
        <div class="form-section">
          <h2>Visualization Fields</h2>
          <div class="checkbox-group">
            ${['p', 'U', 'T', 'k', 'epsilon', 'omega'].map(field => html`
              <label class="checkbox-item">
                <input
                  type="checkbox"
                  ?checked=${config.visualization?.fields?.includes(field)}
                  @change=${() => this._toggleField(field)}
                />
                <span>${field === 'U' ? 'Velocity' : field === 'p' ? 'Pressure' : field}</span>
              </label>
            `)}
          </div>
        </div>

        <!-- Actions -->
        <div class="button-group">
          <button class="btn btn-secondary" @click=${this._handleCancel}>Cancel</button>
          <button
            class="btn btn-primary"
            @click=${this._handleSubmit}
            ?disabled=${!file || isUploading}
          >
            ${isUploading ? html`<span class="spinner"></span> Starting Pipeline...` : 'Start Pipeline'}
          </button>
        </div>

        <!-- Error Message -->
        ${error ? html`
          <div class="error-message">${error}</div>
        ` : ''}
      </div>
    `
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'cfd-upload-page': UploadPage
  }
}
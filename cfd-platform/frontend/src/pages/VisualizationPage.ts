import { LitElement, html, css } from 'lit'
import { customElement, state } from 'lit/decorators.js'
import { CfdComponent } from '../components/base'
import { visualizationService } from '../services/visualizationService'
import { simulationService } from '../services/simulationService'
import { getColormapOptions, getDefaultFieldOptions, VisualizationType, ColormapType } from '../utils/visualizationUtils'

interface VisualizationConfig {
  type: VisualizationType
  field: string
  colormap: ColormapType
  opacity: number
  show_edges: boolean
  vector_scale: number
  num_streamlines: number
  iso_value: number
  slice_normal: 'x' | 'y' | 'z'
  slice_position: number
}

@customElement('cfd-visualization-page')
export class VisualizationPage extends CfdComponent {
  static styles = css`
    ...super.styles,
    `
    .visualization-container {
      display: flex;
      height: 100vh;
      overflow: hidden;
    }
    .sidebar {
      width: 320px;
      background: white;
      border-right: 1px solid #e5e7eb;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
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
      padding: 16px;
    }
    .form-section {
      margin-bottom: 24px;
    }
    .form-section h3 {
      font-size: 12px;
      font-weight: 500;
      color: #6b7280;
      text-transform: uppercase;
      margin-bottom: 12px;
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
    .btn {
      width: 100%;
      padding: 10px 16px;
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
    .btn-group {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .btn-option {
      flex: 1;
      min-width: 80px;
      padding: 8px 12px;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      background: white;
      font-size: 12px;
      cursor: pointer;
      text-align: center;
    }
    .btn-option:hover {
      background: #f3f4f6;
    }
    .btn-option.selected {
      background: #dbeafe;
      border-color: #2563eb;
      color: #1e40af;
    }
    .colormap-preview {
      display: flex;
      height: 24px;
      border-radius: 4px;
      overflow: hidden;
      margin-top: 8px;
    }
    .slider-container {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .slider {
      flex: 1;
      height: 4px;
      background: #e5e7eb;
      border-radius: 2px;
      -webkit-appearance: none;
    }
    .slider::-webkit-slider-thumb {
      -webkit-appearance: none;
      width: 16px;
      height: 16px;
      background: #2563eb;
      border-radius: 50%;
      cursor: pointer;
    }
    .slider-value {
      width: 50px;
      text-align: right;
      font-size: 14px;
      font-family: monospace;
    }
    .main-content {
      flex: 1;
      position: relative;
      background: #1a1a2e;
    }
    .viewer-3d {
      width: 100%;
      height: 100%;
    }
    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #6b7280;
    }
  `

  @state() private _simulationId = ''
  @state() private _config: VisualizationConfig = {
    type: 'contour',
    field: 'p',
    colormap: 'viridis',
    opacity: 1.0,
    show_edges: false,
    vector_scale: 1.0,
    num_streamlines: 10,
    iso_value: 0.5,
    slice_normal: 'z',
    slice_position: 0.5,
  }
  @state() private _isLoading = false

  private _colormaps = getColormapOptions()
  private _fieldOptions = getDefaultFieldOptions()

  connectedCallback() {
    super.connectedCallback()
    const params = new URLSearchParams(window.location.search)
    this._simulationId = params.get('id') || ''
    if (this._simulationId) {
      this._loadSimulation()
    }
  }

  private async _loadSimulation() {
    try {
      const sim = await simulationService.get(this._simulationId)
      this._isLoading = false
    } catch (error) {
      console.error('Failed to load simulation:', error)
      this._isLoading = false
    }
  }

  private _handleApplyVisualization() {
    visualizationService.updateConfig(this._config)
    const viewer = this.shadowRoot?.querySelector('viewer-3d') as any
    if (viewer) {
      viewer.updateVisualization(this._config)
    }
  }

  private _handleResetVisualization() {
    this._config = {
      type: 'contour',
      field: 'p',
      colormap: 'viridis',
      opacity: 1.0,
      show_edges: false,
      vector_scale: 1.0,
      num_streamlines: 10,
      iso_value: 0.5,
      slice_normal: 'z',
      slice_position: 0.5,
    }
    this._handleApplyVisualization()
  }

  private _getColormapGradient(colormap: ColormapType): string {
    const gradients: Record<ColormapType, string> = {
      viridis: 'linear-gradient(to right, #440154, #31688e, #35b779, #fde725)',
      plasma: 'linear-gradient(to right, #0d0887, #9c179e, #ed7953, #f0f921)',
      inferno: 'linear-gradient(to right, #000004, #bc3754, #fcffa4)',
      magma: 'linear-gradient(to right, #000004, #3b0f70, #8c2981, #fdb42f)',
      coolwarm: 'linear-gradient(to right, #3b4cc0, #f7f7f7, #b40426)',
      RdBu: 'linear-gradient(to right, #2166ac, #f7f7f7, #b2182b)',
    }
    return gradients[colormap] || gradients.viridis
  }

  render() {
    const { _config, _isLoading } = this

    return html`
      <div class="visualization-container">
        <!-- Sidebar -->
        <div class="sidebar">
          <div class="sidebar-header">
            <h2>Visualization Controls</h2>
          </div>
          <div class="sidebar-content">
            <!-- Visualization Type -->
            <div class="form-section">
              <h3>Visualization Type</h3>
              <div class="btn-group">
                <button
                  class="btn-option ${_config.type === 'contour' ? 'selected' : ''}"
                  @click=${() => this._config = { ...this._config, type: 'contour' }}
                >
                  Contour
                </button>
                <button
                  class="btn-option ${_config.type === 'vector' ? 'selected' : ''}"
                  @click=${() => this._config = { ...this._config, type: 'vector' }}
                >
                  Vector
                </button>
                <button
                  class="btn-option ${_config.type === 'streamline' ? 'selected' : ''}"
                  @click=${() => this._config = { ...this._config, type: 'streamline' }}
                >
                  Streamline
                </button>
                <button
                  class="btn-option ${_config.type === 'iso-surface' ? 'selected' : ''}"
                  @click=${() => this._config = { ...this._config, type: 'iso-surface' }}
                >
                  Iso-Surface
                </button>
                <button
                  class="btn-option ${_config.type === 'slice' ? 'selected' : ''}"
                  @click=${() => this._config = { ...this._config, type: 'slice' }}
                >
                  Slice
                </button>
              </div>
            </div>

            <!-- Field Selection -->
            <div class="form-section">
              <h3>Field</h3>
              <div class="form-group">
                <select
                  .value=${_config.field}
                  @change=${(e: Event) => this._config = { ...this._config, field: (e.target as HTMLSelectElement).value }}
                >
                  ${this._fieldOptions.map(opt => html`
                    <option value=${opt.value}>${opt.label}</option>
                  `)}
                </select>
              </div>
            </div>

            <!-- Colormap -->
            <div class="form-section">
              <h3>Colormap</h3>
              <div class="form-group">
                <select
                  .value=${_config.colormap}
                  @change=${(e: Event) => this._config = { ...this._config, colormap: (e.target as HTMLSelectElement).value as ColormapType }}
                >
                  ${this._colormaps.map(opt => html`
                    <option value=${opt.value}>${opt.label}</option>
                  `)}
                </select>
                <div class="colormap-preview" style="background: ${this._getColormapGradient(_config.colormap)}"></div>
              </div>
            </div>

            <!-- Opacity -->
            <div class="form-section">
              <h3>Opacity</h3>
              <div class="slider-container">
                <input
                  type="range"
                  class="slider"
                  min="0"
                  max="1"
                  step="0.1"
                  .value=${String(_config.opacity)}
                  @input=${(e: Event) => this._config = { ...this._config, opacity: parseFloat((e.target as HTMLInputElement).value) }}
                />
                <span class="slider-value">${_config.opacity.toFixed(1)}</span>
              </div>
            </div>

            <!-- Type-specific options -->
            ${_config.type === 'vector' ? html`
              <div class="form-section">
                <h3>Vector Scale</h3>
                <div class="slider-container">
                  <input
                    type="range"
                    class="slider"
                    min="0.1"
                    max="5"
                    step="0.1"
                    .value=${String(_config.vector_scale)}
                    @input=${(e: Event) => this._config = { ...this._config, vector_scale: parseFloat((e.target as HTMLInputElement).value) }}
                  />
                  <span class="slider-value">${_config.vector_scale.toFixed(1)}</span>
                </div>
              </div>
            ` : ''}

            ${_config.type === 'streamline' ? html`
              <div class="form-section">
                <h3>Number of Streamlines</h3>
                <div class="form-group">
                  <input
                    type="number"
                    .value=${String(_config.num_streamlines)}
                    @input=${(e: Event) => this._config = { ...this._config, num_streamlines: parseInt((e.target as HTMLInputElement).value) }}
                    min="1"
                    max="100"
                  />
                </div>
              </div>
            ` : ''}

            ${_config.type === 'iso-surface' ? html`
              <div class="form-section">
                <h3>Iso-Value</h3>
                <div class="slider-container">
                  <input
                    type="range"
                    class="slider"
                    min="0"
                    max="1"
                    step="0.01"
                    .value=${String(_config.iso_value)}
                    @input=${(e: Event) => this._config = { ...this._config, iso_value: parseFloat((e.target as HTMLInputElement).value) }}
                  />
                  <span class="slider-value">${_config.iso_value.toFixed(2)}</span>
                </div>
              </div>
            ` : ''}

            ${_config.type === 'slice' ? html`
              <div class="form-section">
                <h3>Slice Normal</h3>
                <div class="form-group">
                  <select
                    .value=${_config.slice_normal}
                    @change=${(e: Event) => this._config = { ...this._config, slice_normal: (e.target as HTMLSelectElement).value as 'x' | 'y' | 'z' }}
                  >
                    <option value="x">X-axis</option>
                    <option value="y">Y-axis</option>
                    <option value="z">Z-axis</option>
                  </select>
                </div>
                <h3>Slice Position</h3>
                <div class="slider-container">
                  <input
                    type="range"
                    class="slider"
                    min="0"
                    max="1"
                    step="0.01"
                    .value=${String(_config.slice_position)}
                    @input=${(e: Event) => this._config = { ...this._config, slice_position: parseFloat((e.target as HTMLInputElement).value) }}
                  />
                  <span class="slider-value">${_config.slice_position.toFixed(2)}</span>
                </div>
              </div>
            ` : ''}

            <!-- Show Edges -->
            <div class="form-section">
              <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                <input
                  type="checkbox"
                  .checked=${_config.show_edges}
                  @change=${(e: Event) => this._config = { ...this._config, show_edges: (e.target as HTMLInputElement).checked }}
                />
                <span>Show Mesh Edges</span>
              </label>
            </div>

            <!-- Actions -->
            <div class="form-section" style="display: flex; gap: 8px;">
              <button class="btn btn-primary" @click=${this._handleApplyVisualization}>
                Apply
              </button>
              <button class="btn btn-secondary" @click=${this._handleResetVisualization}>
                Reset
              </button>
            </div>
          </div>
        </div>

        <!-- Main Content -->
        <div class="main-content">
          ${_isLoading ? html`
            <div class="loading">Loading...</div>
          ` : html`
            <viewer-3d
              class="viewer-3d"
              .simulationId=${this._simulationId}
              .config=${this._config}
            ></viewer-3d>
          `}
        </div>
      </div>
    `
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'cfd-visualization-page': VisualizationPage
  }
}
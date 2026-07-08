/**
 * Parameter Editor Component
 * Live slider binding with real-time updates
 */

import { LitElement, html, css } from 'lit';
import { customElement, state, query } from 'lit/decorators.js';
import { workspaceStore, useParameters } from '../../stores/workspaceStore';
import { eventBus, createDebouncedParameterEmitter } from '../../services/EventBus';
import type { ParameterBase, ParameterChangeEvent } from '../../types/workspace';

interface ParameterConfig extends ParameterBase {
  id: string;
  category: 'geometry' | 'aerodynamic' | 'material';
}

@customElement('parameter-editor')
export class ParameterEditor extends LitElement {
  static styles = css`
    :host {
      display: block;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .section {
      margin-bottom: 24px;
    }

    .section-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid #2a2a3a;
    }

    .section-icon {
      width: 18px;
      height: 18px;
      fill: #3b82f6;
    }

    .section-title {
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #888;
    }

    .parameter-group {
      margin-bottom: 16px;
    }

    .parameter-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }

    .parameter-name {
      font-size: 13px;
      color: #e0e0e0;
    }

    .parameter-value {
      font-size: 13px;
      font-weight: 600;
      color: #3b82f6;
      font-variant-numeric: tabular-nums;
      min-width: 60px;
      text-align: right;
    }

    .parameter-value.changed {
      color: #22c55e;
      animation: valueFlash 0.3s ease;
    }

    @keyframes valueFlash {
      0% { color: #22c55e; }
      100% { color: #3b82f6; }
    }

    .slider-container {
      position: relative;
      height: 24px;
      display: flex;
      align-items: center;
    }

    .slider {
      -webkit-appearance: none;
      appearance: none;
      width: 100%;
      height: 4px;
      background: #2a2a3a;
      border-radius: 2px;
      outline: none;
      cursor: pointer;
    }

    .slider::-webkit-slider-thumb {
      -webkit-appearance: none;
      appearance: none;
      width: 14px;
      height: 14px;
      background: #3b82f6;
      border-radius: 50%;
      cursor: pointer;
      transition: transform 0.1s ease, box-shadow 0.1s ease;
      box-shadow: 0 2px 6px rgba(59, 130, 246, 0.4);
    }

    .slider::-webkit-slider-thumb:hover {
      transform: scale(1.2);
      box-shadow: 0 2px 10px rgba(59, 130, 246, 0.6);
    }

    .slider::-moz-range-thumb {
      width: 14px;
      height: 14px;
      background: #3b82f6;
      border-radius: 50%;
      cursor: pointer;
      border: none;
    }

    .slider:focus {
      outline: none;
    }

    .slider:focus::-webkit-slider-thumb {
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
    }

    .slider-limits {
      display: flex;
      justify-content: space-between;
      font-size: 10px;
      color: #666;
      margin-top: 2px;
    }

    .input-group {
      display: flex;
      gap: 8px;
      margin-top: 8px;
    }

    .value-input {
      flex: 1;
      background: #1a1a24;
      border: 1px solid #2a2a3a;
      border-radius: 4px;
      padding: 6px 10px;
      color: #e0e0e0;
      font-size: 13px;
      font-variant-numeric: tabular-nums;
      outline: none;
      transition: border-color 0.15s ease;
    }

    .value-input:focus {
      border-color: #3b82f6;
    }

    .unit-label {
      display: flex;
      align-items: center;
      padding: 0 10px;
      background: #1a1a24;
      border: 1px solid #2a2a3a;
      border-radius: 4px;
      font-size: 12px;
      color: #888;
    }

    .quick-actions {
      display: flex;
      gap: 8px;
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid #2a2a3a;
    }

    .action-btn {
      flex: 1;
      padding: 8px 12px;
      background: #1a1a24;
      border: 1px solid #2a2a3a;
      border-radius: 4px;
      color: #e0e0e0;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }

    .action-btn:hover {
      background: #2a2a3a;
      border-color: #3a3a4a;
    }

    .action-btn svg {
      width: 14px;
      height: 14px;
      fill: currentColor;
    }

    .preset-selector {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      margin-top: 12px;
    }

    .preset-btn {
      padding: 10px;
      background: #1a1a24;
      border: 1px solid #2a2a3a;
      border-radius: 6px;
      color: #e0e0e0;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.15s ease;
      text-align: center;
    }

    .preset-btn:hover {
      background: #2a2a3a;
      border-color: #3b82f6;
    }

    .preset-btn.active {
      background: rgba(59, 130, 246, 0.15);
      border-color: #3b82f6;
      color: #3b82f6;
    }

    .change-indicator {
      position: absolute;
      right: -20px;
      width: 6px;
      height: 6px;
      background: #22c55e;
      border-radius: 50%;
      opacity: 0;
      transition: opacity 0.2s ease;
    }

    .change-indicator.visible {
      opacity: 1;
    }
  `;

  @state() private parameters: Record<string, number> = {};
  @state() private changedParams: Set<string> = new Set();
  @state() private activePreset: string | null = null;

  private debouncedUpdate: (id: string, value: number) => void;
  private unsubscribe: (() => void)[] = [];

  // Parameter configurations
  private parameterConfigs: ParameterConfig[] = [
    // Geometry parameters
    { id: 'chordLength', name: 'Chord Length', unit: 'm', min: 0.5, max: 3, step: 0.01, default: 1, category: 'geometry' },
    { id: 'wingSpan', name: 'Wing Span', unit: 'm', min: 5, max: 50, step: 0.1, default: 10, category: 'geometry' },
    { id: 'thickness', name: 'Thickness Ratio', unit: '', min: 0.02, max: 0.25, step: 0.001, default: 0.1, category: 'geometry' },
    { id: 'sweepAngle', name: 'Sweep Angle', unit: '°', min: 0, max: 45, step: 0.5, default: 20, category: 'geometry' },
    { id: 'dihedral', name: 'Dihedral Angle', unit: '°', min: 0, max: 15, step: 0.5, default: 3, category: 'geometry' },
    
    // Aerodynamic parameters
    { id: 'velocity', name: 'Velocity', unit: 'm/s', min: 0, max: 500, step: 1, default: 50, category: 'aerodynamic' },
    { id: 'angleOfAttack', name: 'Angle of Attack', unit: '°', min: -10, max: 25, step: 0.1, default: 5, category: 'aerodynamic' },
    { id: 'altitude', name: 'Altitude', unit: 'm', min: 0, max: 15000, step: 100, default: 0, category: 'aerodynamic' },
    { id: 'sideslipAngle', name: 'Sideslip Angle', unit: '°', min: -20, max: 20, step: 0.5, default: 0, category: 'aerodynamic' },
    
    // Material parameters
    { id: 'materialDensity', name: 'Material Density', unit: 'kg/m³', min: 1000, max: 5000, step: 10, default: 2700, category: 'material' },
    { id: 'youngsModulus', name: "Young's Modulus", unit: 'GPa', min: 50, max: 200, step: 1, default: 70, category: 'material' },
  ];

  // Presets
  private presets: Record<string, Record<string, number>> = {
    'cruise': { velocity: 200, altitude: 10000, angleOfAttack: 3 },
    'takeoff': { velocity: 80, altitude: 0, angleOfAttack: 12 },
    'landing': { velocity: 70, altitude: 0, angleOfAttack: 15 },
    'maneuvers': { velocity: 150, altitude: 5000, angleOfAttack: 20 },
  };

  constructor() {
    super();
    // Create debounced updater for slider changes (100ms)
    this.debouncedUpdate = createDebouncedParameterEmitter(100)((id, value) => {
      workspaceStore.setParameter(id, value);
    }) as any;
  }

  connectedCallback() {
    super.connectedCallback();
    this.setupSubscriptions();
    this.initializeParameters();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.unsubscribe.forEach(unsub => unsub());
  }

  private setupSubscriptions() {
    const unsubParams = useParameters((params) => {
      this.parameters = params;
      this.requestUpdate();
    });
    this.unsubscribe.push(unsubParams);
  }

  private initializeParameters() {
    const initialParams: Record<string, number> = {};
    this.parameterConfigs.forEach(config => {
      initialParams[config.id] = config.default;
    });
    workspaceStore.setParameters(initialParams);
  }

  private handleSliderInput(id: string, value: number) {
    // Immediate visual update
    this.parameters = { ...this.parameters, [id]: value };
    this.requestUpdate();

    // Debounced store update (for analysis triggering)
    this.debouncedUpdate(id, value);
  }

  private handleSliderChange(id: string, value: number) {
    // Final value commit
    workspaceStore.setParameter(id, value);
    
    // Show change indicator
    this.changedParams.add(id);
    this.requestUpdate();
    
    setTimeout(() => {
      this.changedParams.delete(id);
      this.requestUpdate();
    }, 500);
  }

  private handleInputChange(id: string, value: string) {
    const numValue = parseFloat(value);
    if (!isNaN(numValue)) {
      const config = this.parameterConfigs.find(c => c.id === id);
      if (config) {
        const clampedValue = Math.max(config.min, Math.min(config.max, numValue));
        workspaceStore.setParameter(id, clampedValue);
      }
    }
  }

  private applyPreset(presetName: string) {
    const preset = this.presets[presetName];
    if (preset) {
      this.activePreset = presetName;
      workspaceStore.setParameters(preset);
    }
  }

  private resetToDefaults() {
    this.activePreset = null;
    const defaults: Record<string, number> = {};
    this.parameterConfigs.forEach(config => {
      defaults[config.id] = config.default;
    });
    workspaceStore.setParameters(defaults);
  }

  private undoLastChange() {
    const history = eventBus.getParameterHistory();
    if (history.length > 0) {
      const lastChange = history[history.length - 1];
      workspaceStore.setParameter(lastChange.parameterId, lastChange.oldValue);
    }
  }

  private renderParameter(config: ParameterConfig) {
    const value = this.parameters[config.id] ?? config.default;
    const isChanged = this.changedParams.has(config.id);

    return html`
      <div class="parameter-group">
        <div class="parameter-header">
          <span class="parameter-name">${config.name}</span>
          <span class="parameter-value ${isChanged ? 'changed' : ''}">
            ${typeof value === 'number' ? value.toFixed(config.step < 1 ? 2 : 0) : value}
            ${config.unit ? html`<span style="color: #666; font-weight: 400"> ${config.unit}</span>` : ''}
          </span>
        </div>
        <div class="slider-container">
          <input
            type="range"
            class="slider"
            min=${config.min}
            max=${config.max}
            step=${config.step}
            .value=${String(value)}
            @input=${(e: InputEvent) => this.handleSliderInput(config.id, parseFloat((e.target as HTMLInputElement).value))}
            @change=${(e: InputEvent) => this.handleSliderChange(config.id, parseFloat((e.target as HTMLInputElement).value))}
          />
          <div class="change-indicator ${isChanged ? 'visible' : ''}"></div>
        </div>
        <div class="slider-limits">
          <span>${config.min}${config.unit ? ' ' + config.unit : ''}</span>
          <span>${config.max}${config.unit ? ' ' + config.unit : ''}</span>
        </div>
        <div class="input-group">
          <input
            type="number"
            class="value-input"
            min=${config.min}
            max=${config.max}
            step=${config.step}
            .value=${String(value)}
            @change=${(e: InputEvent) => this.handleInputChange(config.id, (e.target as HTMLInputElement).value)}
          />
          ${config.unit ? html`<span class="unit-label">${config.unit}</span>` : ''}
        </div>
      </div>
    `;
  }

  private renderSection(title: string, icon: string, params: ParameterConfig[]) {
    return html`
      <div class="section">
        <div class="section-header">
          <svg class="section-icon" viewBox="0 0 24 24">${icon}</svg>
          <span class="section-title">${title}</span>
        </div>
        ${params.map(p => this.renderParameter(p))}
      </div>
    `;
  }

  render() {
    const geometryParams = this.parameterConfigs.filter(p => p.category === 'geometry');
    const aeroParams = this.parameterConfigs.filter(p => p.category === 'aerodynamic');
    const materialParams = this.parameterConfigs.filter(p => p.category === 'material');

    return html`
      ${this.renderSection('Geometry', '<path d="M3 3h18v18H3z"/>', geometryParams)}
      ${this.renderSection('Aerodynamics', '<path d="M12 2L2 12h3v8h14v-8h3L12 2z"/>', aeroParams)}
      ${this.renderSection('Material', '<path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16z"/>', materialParams)}

      <div class="section">
        <div class="section-header">
          <svg class="section-icon" viewBox="0 0 24 24">
            <path d="M13 3v6h8l-10 12v-6H3l10-12z"/>
          </svg>
          <span class="section-title">Quick Presets</span>
        </div>
        <div class="preset-selector">
          ${Object.keys(this.presets).map(name => html`
            <button 
              class="preset-btn ${this.activePreset === name ? 'active' : ''}"
              @click=${() => this.applyPreset(name)}
            >
              ${name.charAt(0).toUpperCase() + name.slice(1)}
            </button>
          `)}
        </div>
      </div>

      <div class="quick-actions">
        <button class="action-btn" @click=${this.undoLastChange}>
          <svg viewBox="0 0 24 24"><path d="M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z"/></svg>
          Undo
        </button>
        <button class="action-btn" @click=${this.resetToDefaults}>
          <svg viewBox="0 0 24 24"><path d="M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
          Reset
        </button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'parameter-editor': ParameterEditor;
  }
}
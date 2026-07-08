/**
 * Main Workspace Container
 * Orchestrates all workspace components and manages layout
 */

import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { workspaceStore, useStore, useParameters, useCurrentResult } from '../../stores/workspaceStore';
import { eventBus } from '../../services/EventBus';
import { analysisEngine } from '../../engine/progressiveAnalysis';

@customElement('engineering-workspace')
export class EngineeringWorkspace extends LitElement {
  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100vh;
      background: #0a0a0f;
      color: #e0e0e0;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      overflow: hidden;
    }

    .workspace {
      display: grid;
      grid-template-rows: 56px 1fr 32px;
      grid-template-columns: 320px 1fr 280px;
      grid-template-areas:
        "header header header"
        "parameters visualization dashboard"
        "statusbar statusbar statusbar";
      height: 100%;
      gap: 1px;
      background: #1a1a24;
    }

    .header {
      grid-area: header;
      background: linear-gradient(180deg, #12121a 0%, #0d0d14 100%);
      border-bottom: 1px solid #2a2a3a;
      display: flex;
      align-items: center;
      padding: 0 20px;
      gap: 24px;
    }

    .header-title {
      font-size: 16px;
      font-weight: 600;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .header-title svg {
      width: 24px;
      height: 24px;
      fill: #3b82f6;
    }

    .header-controls {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-left: auto;
    }

    .fidelity-badge {
      padding: 4px 12px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .fidelity-badge.instant {
      background: rgba(34, 197, 94, 0.15);
      color: #22c55e;
      border: 1px solid rgba(34, 197, 94, 0.3);
    }

    .fidelity-badge.medium {
      background: rgba(234, 179, 8, 0.15);
      color: #eab308;
      border: 1px solid rgba(234, 179, 8, 0.3);
    }

    .fidelity-badge.high {
      background: rgba(168, 85, 247, 0.15);
      color: #a855f7;
      border: 1px solid rgba(168, 85, 247, 0.3);
    }

    .btn {
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s ease;
      border: none;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .btn-primary {
      background: #3b82f6;
      color: white;
    }

    .btn-primary:hover {
      background: #2563eb;
    }

    .btn-primary:disabled {
      background: #3b82f680;
      cursor: not-allowed;
    }

    .btn-secondary {
      background: #2a2a3a;
      color: #e0e0e0;
      border: 1px solid #3a3a4a;
    }

    .btn-secondary:hover {
      background: #3a3a4a;
    }

    .btn-danger {
      background: #dc2626;
      color: white;
    }

    .btn-danger:hover {
      background: #b91c1c;
    }

    .parameters-panel {
      grid-area: parameters;
      background: #12121a;
      overflow-y: auto;
      padding: 16px;
    }

    .visualization-area {
      grid-area: visualization;
      background: #0d0d14;
      position: relative;
      overflow: hidden;
    }

    .dashboard-panel {
      grid-area: dashboard;
      background: #12121a;
      overflow-y: auto;
      padding: 16px;
    }

    .statusbar {
      grid-area: statusbar;
      background: #0d0d14;
      border-top: 1px solid #2a2a3a;
      display: flex;
      align-items: center;
      padding: 0 16px;
      gap: 24px;
      font-size: 11px;
      color: #888;
    }

    .status-item {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #22c55e;
    }

    .status-dot.warning {
      background: #eab308;
    }

    .status-dot.error {
      background: #dc2626;
    }

    .status-dot.analyzing {
      background: #3b82f6;
      animation: pulse 1s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }

    .progress-bar {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: #1a1a24;
    }

    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #3b82f6, #8b5cf6);
      transition: width 0.3s ease;
    }

    .loading-overlay {
      position: absolute;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
      z-index: 100;
    }

    .spinner {
      width: 40px;
      height: 40px;
      border: 3px solid #2a2a3a;
      border-top-color: #3b82f6;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .loading-text {
      color: #888;
      font-size: 13px;
    }

    .fidelity-selector {
      display: flex;
      gap: 4px;
      background: #1a1a24;
      padding: 4px;
      border-radius: 6px;
    }

    .fidelity-option {
      padding: 6px 12px;
      border-radius: 4px;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.15s ease;
      border: none;
      background: transparent;
      color: #888;
    }

    .fidelity-option:hover {
      color: #e0e0e0;
    }

    .fidelity-option.active {
      background: #3b82f6;
      color: white;
    }
  `;

  @state() private isAnalyzing = false;
  @state() private currentFidelity: 'instant' | 'medium' | 'high' = 'instant';
  @state() private progress = 0;
  @state() private systemStatus = 'ready';

  private unsubscribe: (() => void)[] = [];

  connectedCallback() {
    super.connectedCallback();
    this.setupSubscriptions();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.unsubscribe.forEach(unsub => unsub());
  }

  private setupSubscriptions() {
    // Subscribe to store changes
    const unsubStore = useStore((state) => {
      this.isAnalyzing = state.isAnalyzing;
      this.requestUpdate();
    });
    this.unsubscribe.push(unsubStore);

    // Listen for analysis progress
    const unsubProgress = eventBus.on('ANALYSIS_PROGRESS', (event: any) => {
      this.progress = event.data.progress * 100;
      this.requestUpdate();
    });
    this.unsubscribe.push(unsubProgress);

    // Listen for analysis complete
    const unsubComplete = eventBus.on('ANALYSIS_COMPLETE', () => {
      this.progress = 100;
      setTimeout(() => {
        this.progress = 0;
        this.requestUpdate();
      }, 500);
    });
    this.unsubscribe.push(unsubComplete);
  }

  private async runAnalysis() {
    const params = workspaceStore.getParameters();
    await analysisEngine.triggerAnalysis(params, this.currentFidelity);
  }

  private cancelAnalysis() {
    analysisEngine.cancelCurrentAnalysis();
  }

  private setFidelity(fidelity: 'instant' | 'medium' | 'high') {
    this.currentFidelity = fidelity;
  }

  render() {
    return html`
      <div class="workspace">
        <header class="header">
          <div class="header-title">
            <svg viewBox="0 0 24 24">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
            Engineering Analysis Workspace
          </div>

          <div class="fidelity-selector">
            <button 
              class="fidelity-option ${this.currentFidelity === 'instant' ? 'active' : ''}"
              @click=${() => this.setFidelity('instant')}
            >
              Instant
            </button>
            <button 
              class="fidelity-option ${this.currentFidelity === 'medium' ? 'active' : ''}"
              @click=${() => this.setFidelity('medium')}
            >
              Medium
            </button>
            <button 
              class="fidelity-option ${this.currentFidelity === 'high' ? 'active' : ''}"
              @click=${() => this.setFidelity('high')}
            >
              High-Fidelity
            </button>
          </div>

          <div class="header-controls">
            <span class="fidelity-badge ${this.currentFidelity}">
              ${this.currentFidelity}
            </span>
            
            ${this.isAnalyzing
              ? html`<button class="btn btn-danger" @click=${this.cancelAnalysis}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="6" y="6" width="12" height="12"/>
                  </svg>
                  Cancel
                </button>`
              : html`<button class="btn btn-primary" @click=${this.runAnalysis}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <polygon points="5,3 19,12 5,21"/>
                  </svg>
                  Run Analysis
                </button>`
            }
          </div>
        </header>

        <aside class="parameters-panel">
          <parameter-editor></parameter-editor>
        </aside>

        <main class="visualization-area">
          <model-viewer></model-viewer>
          ${this.isAnalyzing ? html`
            <div class="loading-overlay">
              <div class="spinner"></div>
              <div class="loading-text">Running ${this.currentFidelity} analysis...</div>
            </div>
          ` : ''}
          <div class="progress-bar">
            <div class="progress-fill" style="width: ${this.progress}%"></div>
          </div>
        </main>

        <aside class="dashboard-panel">
          <metrics-dashboard></metrics-dashboard>
        </aside>

        <footer class="statusbar">
          <div class="status-item">
            <span class="status-dot ${this.systemStatus === 'ready' ? '' : 'analyzing'}"></span>
            ${this.systemStatus === 'ready' ? 'Ready' : 'Analyzing...'}
          </div>
          <div class="status-item">
            <span class="status-dot"></span>
            WebSocket: Connected
          </div>
          <div class="status-item">
            Cache: Active
          </div>
          <div class="status-item" style="margin-left: auto">
            Progressive Analysis Engine v1.0
          </div>
        </footer>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'engineering-workspace': EngineeringWorkspace;
  }
}
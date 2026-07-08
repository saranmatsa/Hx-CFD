/**
 * Frontend Application Shell
 * Main entry point that integrates all workspace components
 */

import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { EventBus } from '../services/EventBus';
import { workspaceStore } from '../stores/workspaceStore';
import { AnalysisWebSocket } from '../services/analysisService';
import { ProgressiveAnalysisEngine } from '../engine/progressiveAnalysis';

// Import all components
import './workspace/EngineeringWorkspace';
import './parameters/ParameterEditor';
import './visualization/ModelViewer';
import './dashboard/MetricsDashboard';

// Type imports
import type { WorkspaceState, AnalysisResult, ParameterChangeEvent } from '../types/workspace';

export interface AppConfig {
  apiUrl?: string;
  wsUrl?: string;
  enableDebug?: boolean;
  defaultFidelity?: 'instant' | 'medium' | 'high';
  autoConnect?: boolean;
}

const DEFAULT_CONFIG: Required<AppConfig> = {
  apiUrl: 'http://localhost:8080/api',
  wsUrl: 'ws://localhost:8080',
  enableDebug: false,
  defaultFidelity: 'instant',
  autoConnect: true
};

@customElement('cfd-app-shell')
export class CFDAppShell extends LitElement {
  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100vh;
      background: #0a0a0f;
      color: #e0e0e0;
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      overflow: hidden;
    }

    .app-container {
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 20px;
      background: linear-gradient(180deg, #1a1a24 0%, #12121a 100%);
      border-bottom: 1px solid #2a2a3a;
      z-index: 100;
    }

    .logo {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .logo-icon {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, #00d4ff 0%, #0066ff 100%);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 18px;
    }

    .logo-text {
      font-size: 20px;
      font-weight: 600;
      background: linear-gradient(90deg, #00d4ff, #0066ff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .connection-status {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      background: #1a1a24;
      border-radius: 20px;
      font-size: 12px;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #666;
    }

    .status-dot.connected {
      background: #00ff88;
      box-shadow: 0 0 8px #00ff88;
    }

    .status-dot.connecting {
      background: #ffaa00;
      animation: pulse 1s infinite;
    }

    .status-dot.disconnected {
      background: #ff4444;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }

    .main-content {
      flex: 1;
      display: flex;
      overflow: hidden;
    }

    .sidebar {
      width: 320px;
      background: #0f0f18;
      border-right: 1px solid #1a1a2a;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .sidebar-header {
      padding: 16px;
      border-bottom: 1px solid #1a1a2a;
    }

    .sidebar-title {
      font-size: 14px;
      font-weight: 600;
      color: #888;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .sidebar-content {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }

    .workspace-area {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .workspace-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 20px;
      background: #0f0f18;
      border-bottom: 1px solid #1a1a2a;
    }

    .toolbar-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .fidelity-selector {
      display: flex;
      background: #1a1a24;
      border-radius: 8px;
      padding: 4px;
    }

    .fidelity-btn {
      padding: 8px 16px;
      border: none;
      background: transparent;
      color: #888;
      font-size: 13px;
      font-weight: 500;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s;
    }

    .fidelity-btn:hover {
      color: #e0e0e0;
    }

    .fidelity-btn.active {
      background: linear-gradient(135deg, #00d4ff 0%, #0066ff 100%);
      color: white;
    }

    .run-btn {
      padding: 10px 24px;
      border: none;
      background: linear-gradient(135deg, #00d4ff 0%, #0066ff 100%);
      color: white;
      font-size: 14px;
      font-weight: 600;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .run-btn:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
    }

    .run-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .workspace-content {
      flex: 1;
      display: grid;
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr 1fr;
      gap: 1px;
      background: #1a1a2a;
      overflow: hidden;
    }

    .panel {
      background: #0a0a0f;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .panel-header {
      padding: 12px 16px;
      background: #0f0f18;
      border-bottom: 1px solid #1a1a2a;
      font-size: 12px;
      font-weight: 600;
      color: #888;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .panel-content {
      flex: 1;
      overflow: hidden;
    }

    .metrics-panel {
      grid-column: 1 / 2;
      grid-row: 2 / 3;
    }

    .loading-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(10, 10, 15, 0.9);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .loading-content {
      text-align: center;
    }

    .loading-spinner {
      width: 48px;
      height: 48px;
      border: 3px solid #1a1a2a;
      border-top-color: #00d4ff;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin: 0 auto 16px;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .loading-text {
      color: #888;
      font-size: 14px;
    }

    .error-toast {
      position: fixed;
      bottom: 20px;
      right: 20px;
      padding: 16px 24px;
      background: #2a1a1a;
      border: 1px solid #ff4444;
      border-radius: 8px;
      color: #ff6666;
      font-size: 14px;
      z-index: 1001;
      animation: slideIn 0.3s ease;
    }

    @keyframes slideIn {
      from {
        transform: translateX(100%);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }
  `;

  private config: Required<AppConfig>;
  private eventBus: EventBus;
  private wsService: AnalysisWebSocket | null = null;
  private analysisEngine: ProgressiveAnalysisEngine;
  private debouncedParameterEmitter: (params: Record<string, number>) => void;

  @state() private connectionStatus: 'connected' | 'connecting' | 'disconnected' = 'disconnected';
  @state() private currentFidelity: 'instant' | 'medium' | 'high' = 'instant';
  @state() private isAnalyzing = false;
  @state() private analysisProgress = 0;
  @state() private error: string | null = null;
  @state() private workspaceState: WorkspaceState | null = null;

  constructor(config: AppConfig = {}) {
    super();
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.eventBus = EventBus.getInstance();
    this.analysisEngine = new ProgressiveAnalysisEngine();
    
    // Create debounced parameter emitter
    this.debouncedParameterEmitter = this.eventBus.createDebouncedParameterEmitter(100);
    
    // Subscribe to store updates
    workspaceStore.subscribe((state) => {
      this.workspaceState = state;
    });
  }

  connectedCallback() {
    super.connectedCallback();
    
    if (this.config.autoConnect) {
      this.connect();
    }

    // Listen for analysis events
    this.eventBus.onParameterChange((params) => {
      this.handleParameterChange(params);
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.disconnect();
  }

  private connect() {
    this.connectionStatus = 'connecting';
    
    try {
      this.wsService = new AnalysisWebSocket(this.config.wsUrl);
      
      this.wsService.onOpen(() => {
        this.connectionStatus = 'connected';
        this.log('WebSocket connected');
      });

      this.wsService.onMessage((message) => {
        this.handleWSMessage(message);
      });

      this.wsService.onClose(() => {
        this.connectionStatus = 'disconnected';
        this.log('WebSocket disconnected');
      });

      this.wsService.onError((error) => {
        this.connectionStatus = 'disconnected';
        this.error = 'Connection error';
        this.log('WebSocket error:', error);
      });

      this.wsService.connect();
    } catch (err) {
      this.connectionStatus = 'disconnected';
      this.error = 'Failed to connect';
      this.log('Connection error:', err);
    }
  }

  private disconnect() {
    if (this.wsService) {
      this.wsService.disconnect();
      this.wsService = null;
    }
  }

  private handleWSMessage(message: any) {
    switch (message.type) {
      case 'analysisStart':
        this.isAnalyzing = true;
        this.analysisProgress = 0;
        break;

      case 'analysisProgress':
        this.analysisProgress = message.progress || 0;
        break;

      case 'analysisComplete':
        this.isAnalyzing = false;
        this.analysisProgress = 100;
        if (message.result) {
          this.handleAnalysisResult(message.result);
        }
        break;

      case 'analysisError':
        this.isAnalyzing = false;
        this.error = message.error;
        setTimeout(() => { this.error = null; }, 5000);
        break;

      case 'metricsUpdate':
        workspaceStore.updateMetrics(message.metrics);
        break;

      case 'parameterChange':
        workspaceStore.updateParameters(message.parameters);
        break;
    }
  }

  private handleParameterChange(params: Record<string, number>) {
    // Emit debounced update
    this.debouncedParameterEmitter(params);

    // Update store
    workspaceStore.updateParameters(params);

    // If connected, send to server
    if (this.wsService && this.connectionStatus === 'connected') {
      this.wsService.sendParameterChange(params);
    }

    // Trigger instant analysis for preview
    if (this.currentFidelity === 'instant') {
      this.runInstantAnalysis(params);
    }
  }

  private async runInstantAnalysis(params: Record<string, number>) {
    try {
      const result = await this.analysisEngine.analyzeInstant(params);
      workspaceStore.setCurrentResult(result);
    } catch (err) {
      this.log('Instant analysis error:', err);
    }
  }

  private handleAnalysisResult(result: AnalysisResult) {
    workspaceStore.setCurrentResult(result);
    
    if (result.convergenceHistory) {
      workspaceStore.updateConvergence(result.convergenceHistory);
    }
  }

  private async runAnalysis() {
    if (!this.workspaceState) return;

    this.isAnalyzing = true;
    this.analysisProgress = 0;

    try {
      if (this.wsService && this.connectionStatus === 'connected') {
        // Use WebSocket for real-time updates
        await this.wsService.requestAnalysis(
          this.workspaceState.parameters,
          this.currentFidelity
        );
      } else {
        // Fallback to HTTP
        const result = await this.analysisEngine.analyze(
          this.workspaceState.parameters,
          this.currentFidelity
        );
        this.handleAnalysisResult(result);
      }
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Analysis failed';
      setTimeout(() => { this.error = null; }, 5000);
    } finally {
      this.isAnalyzing = false;
    }
  }

  private setFidelity(fidelity: 'instant' | 'medium' | 'high') {
    this.currentFidelity = fidelity;
    workspaceStore.setFidelity(fidelity);
  }

  private log(...args: any[]) {
    if (this.config.enableDebug) {
      console.log('[CFDAppShell]', ...args);
    }
  }

  render() {
    return html`
      <div class="app-container">
        <!-- Header -->
        <header class="header">
          <div class="logo">
            <div class="logo-icon">C</div>
            <span class="logo-text">CFD Platform</span>
          </div>
          
          <div class="header-actions">
            <div class="connection-status">
              <span class="status-dot ${this.connectionStatus}"></span>
              <span>${this.connectionStatus === 'connected' ? 'Connected' : 
                       this.connectionStatus === 'connecting' ? 'Connecting...' : 'Disconnected'}</span>
            </div>
          </div>
        </header>

        <!-- Main Content -->
        <div class="main-content">
          <!-- Sidebar -->
          <aside class="sidebar">
            <div class="sidebar-header">
              <span class="sidebar-title">Parameters</span>
            </div>
            <div class="sidebar-content">
              <parameter-editor></parameter-editor>
            </div>
          </aside>

          <!-- Workspace Area -->
          <main class="workspace-area">
            <!-- Toolbar -->
            <div class="workspace-toolbar">
              <div class="toolbar-group">
                <div class="fidelity-selector">
                  <button 
                    class="fidelity-btn ${this.currentFidelity === 'instant' ? 'active' : ''}"
                    @click=${() => this.setFidelity('instant')}
                  >
                    Instant
                  </button>
                  <button 
                    class="fidelity-btn ${this.currentFidelity === 'medium' ? 'active' : ''}"
                    @click=${() => this.setFidelity('medium')}
                  >
                    Medium
                  </button>
                  <button 
                    class="fidelity-btn ${this.currentFidelity === 'high' ? 'active' : ''}"
                    @click=${() => this.setFidelity('high')}
                  >
                    High
                  </button>
                </div>
              </div>

              <div class="toolbar-group">
                <button 
                  class="run-btn" 
                  @click=${this.runAnalysis}
                  ?disabled=${this.isAnalyzing}
                >
                  ${this.isAnalyzing ? 'Analyzing...' : 'Run Analysis'}
                </button>
              </div>
            </div>

            <!-- Workspace Grid -->
            <div class="workspace-content">
              <!-- 3D View - Top Left -->
              <div class="panel">
                <div class="panel-header">3D View</div>
                <div class="panel-content">
                  <model-viewer view="perspective"></model-viewer>
                </div>
              </div>

              <!-- Metrics - Top Right -->
              <div class="panel metrics-panel">
                <div class="panel-header">Metrics Dashboard</div>
                <div class="panel-content">
                  <metrics-dashboard></metrics-dashboard>
                </div>
              </div>

              <!-- Front View - Bottom Left -->
              <div class="panel">
                <div class="panel-header">Front View</div>
                <div class="panel-content">
                  <model-viewer view="front"></model-viewer>
                </div>
              </div>

              <!-- Side View - Bottom Right -->
              <div class="panel">
                <div class="panel-header">Side View</div>
                <div class="panel-content">
                  <model-viewer view="side"></model-viewer>
                </div>
              </div>
            </div>
          </main>
        </div>

        <!-- Loading Overlay -->
        ${this.isAnalyzing ? html`
          <div class="loading-overlay">
            <div class="loading-content">
              <div class="loading-spinner"></div>
              <div class="loading-text">Running ${this.currentFidelity} analysis... ${this.analysisProgress}%</div>
            </div>
          </div>
        ` : ''}

        <!-- Error Toast -->
        ${this.error ? html`
          <div class="error-toast">${this.error}</div>
        ` : ''}
      </div>
    `;
  }
}

// Export for use in other modules
export { CFDAppShell };

// Auto-initialize when DOM is ready
declare global {
  interface Window {
    CFDAppShell: typeof CFDAppShell;
  }
}

window.CFDAppShell = CFDAppShell;
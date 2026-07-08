/**
 * Metrics Dashboard Component
 * Real-time engineering metrics visualization
 */

import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { workspaceStore, useCurrentResult, useSystemResources } from '../../stores/workspaceStore';
import { eventBus } from '../../services/EventBus';
import type { AnalysisResult, EngineeringMetrics, ConvergenceData, ResidualHistory, SystemResources } from '../../types/workspace';

interface MetricCard {
  id: string;
  label: string;
  value: string;
  unit: string;
  trend?: 'up' | 'down' | 'stable';
  color?: string;
}

@customElement('metrics-dashboard')
export class MetricsDashboard extends LitElement {
  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      background: #0d0d14;
      overflow-y: auto;
    }

    .dashboard {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .section-title {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #666;
      margin-bottom: 8px;
    }

    /* Metric Cards Grid */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
    }

    .metric-card {
      background: #141420;
      border: 1px solid #1e1e2a;
      border-radius: 8px;
      padding: 14px;
      transition: border-color 0.2s ease;
    }

    .metric-card:hover {
      border-color: #2a2a3a;
    }

    .metric-card.primary {
      background: linear-gradient(135deg, #1a1a2e 0%, #141420 100%);
      border-color: #2a2a3a;
    }

    .metric-label {
      font-size: 11px;
      color: #888;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .metric-label svg {
      width: 14px;
      height: 14px;
      fill: currentColor;
    }

    .metric-value {
      font-size: 24px;
      font-weight: 600;
      color: #fff;
      font-variant-numeric: tabular-nums;
      line-height: 1.2;
    }

    .metric-value.small {
      font-size: 18px;
    }

    .metric-unit {
      font-size: 12px;
      color: #666;
      margin-left: 4px;
    }

    .metric-trend {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-top: 6px;
      font-size: 11px;
    }

    .trend-up {
      color: #22c55e;
    }

    .trend-down {
      color: #ef4444;
    }

    .trend-stable {
      color: #888;
    }

    .trend-icon {
      width: 12px;
      height: 12px;
    }

    /* Performance Metrics */
    .performance-section {
      background: #141420;
      border: 1px solid #1e1e2a;
      border-radius: 8px;
      padding: 14px;
    }

    .performance-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }

    .perf-item {
      text-align: center;
    }

    .perf-value {
      font-size: 20px;
      font-weight: 600;
      color: #fff;
      font-variant-numeric: tabular-nums;
    }

    .perf-label {
      font-size: 10px;
      color: #666;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-top: 4px;
    }

    /* Convergence Plot */
    .convergence-section {
      background: #141420;
      border: 1px solid #1e1e2a;
      border-radius: 8px;
      padding: 14px;
    }

    .plot-container {
      position: relative;
      height: 160px;
      margin-top: 8px;
    }

    .plot-canvas {
      width: 100%;
      height: 100%;
      display: block;
    }

    .plot-legend {
      display: flex;
      gap: 16px;
      margin-top: 8px;
      justify-content: center;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 10px;
      color: #888;
    }

    .legend-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }

    /* Residual History */
    .residual-section {
      background: #141420;
      border: 1px solid #1e1e2a;
      border-radius: 8px;
      padding: 14px;
    }

    .residual-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 8px;
    }

    .residual-item {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .residual-name {
      font-size: 11px;
      color: #888;
      width: 60px;
    }

    .residual-bar-container {
      flex: 1;
      height: 6px;
      background: #1e1e2a;
      border-radius: 3px;
      overflow: hidden;
    }

    .residual-bar {
      height: 100%;
      border-radius: 3px;
      transition: width 0.3s ease;
    }

    .residual-value {
      font-size: 11px;
      color: #666;
      width: 80px;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }

    /* System Resources */
    .resources-section {
      background: #141420;
      border: 1px solid #1e1e2a;
      border-radius: 8px;
      padding: 14px;
    }

    .resource-bar {
      margin-bottom: 12px;
    }

    .resource-bar:last-child {
      margin-bottom: 0;
    }

    .resource-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 6px;
    }

    .resource-label {
      font-size: 11px;
      color: #888;
    }

    .resource-value {
      font-size: 11px;
      color: #666;
      font-variant-numeric: tabular-nums;
    }

    .resource-track {
      height: 6px;
      background: #1e1e2a;
      border-radius: 3px;
      overflow: hidden;
    }

    .resource-fill {
      height: 100%;
      border-radius: 3px;
      transition: width 0.3s ease;
    }

    .cpu-fill {
      background: linear-gradient(90deg, #3b82f6, #8b5cf6);
    }

    .memory-fill {
      background: linear-gradient(90deg, #22c55e, #10b981);
    }

    .gpu-fill {
      background: linear-gradient(90deg, #f59e0b, #ef4444);
    }

    /* Status Indicators */
    .status-row {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }

    .status-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      background: #1a1a24;
      border-radius: 4px;
      font-size: 11px;
    }

    .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
    }

    .status-dot.green {
      background: #22c55e;
      box-shadow: 0 0 6px #22c55e;
    }

    .status-dot.yellow {
      background: #eab308;
      box-shadow: 0 0 6px #eab308;
    }

    .status-dot.red {
      background: #ef4444;
      box-shadow: 0 0 6px #ef4444;
    }

    .status-dot.blue {
      background: #3b82f6;
      box-shadow: 0 0 6px #3b82f6;
    }

    .status-text {
      color: #888;
    }

    .status-value {
      color: #fff;
      font-weight: 500;
    }

    /* Convergence Status */
    .convergence-status {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: #1a1a24;
      border-radius: 6px;
      margin-top: 8px;
    }

    .convergence-icon {
      width: 20px;
      height: 20px;
    }

    .converged {
      color: #22c55e;
    }

    .diverging {
      color: #ef4444;
    }

    .iterating {
      color: #eab308;
    }

    /* Iteration Progress */
    .iteration-bar {
      margin-top: 8px;
    }

    .iteration-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 4px;
    }

    .iteration-label {
      font-size: 10px;
      color: #666;
    }

    .iteration-value {
      font-size: 10px;
      color: #888;
      font-variant-numeric: tabular-nums;
    }

    .iteration-track {
      height: 4px;
      background: #1e1e2a;
      border-radius: 2px;
      overflow: hidden;
    }

    .iteration-fill {
      height: 100%;
      background: #3b82f6;
      border-radius: 2px;
      transition: width 0.3s ease;
    }

    /* No Data State */
    .no-data {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px;
      color: #666;
      text-align: center;
    }

    .no-data svg {
      width: 48px;
      height: 48px;
      fill: #333;
      margin-bottom: 12px;
    }

    .no-data-text {
      font-size: 13px;
    }
  `;

  @state() private currentResult: AnalysisResult | null = null;
  @state() private systemResources: SystemResources | null = null;
  @state() private convergenceHistory: ConvergenceData[] = [];
  @state() private residualHistory: ResidualHistory[] = [];
  @state() private isAnalyzing = false;

  private unsubscribe: (() => void)[] = [];
  private convergenceCanvas: HTMLCanvasElement | null = null;
  private convergenceCtx: CanvasRenderingContext2D | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.setupSubscriptions();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.unsubscribe.forEach(unsub => unsub());
  }

  private setupSubscriptions() {
    const unsubResult = useCurrentResult((result) => {
      this.currentResult = result;
      if (result?.convergenceHistory) {
        this.convergenceHistory = result.convergenceHistory;
        this.renderConvergencePlot();
      }
      if (result?.residualHistory) {
        this.residualHistory = result.residualHistory;
      }
    });
    this.unsubscribe.push(unsubResult);

    const unsubResources = useSystemResources((resources) => {
      this.systemResources = resources;
    });
    this.unsubscribe.push(subResources);

    const unsubProgress = eventBus.on('ANALYSIS_UPDATE', (data: any) => {
      if (data.convergence) {
        this.convergenceHistory = [...this.convergenceHistory, data.convergence];
        this.renderConvergencePlot();
      }
      if (data.residuals) {
        this.residualHistory = data.residuals;
      }
    });
    this.unsubscribe.push(subProgress);

    const unsubAnalyzing = workspaceStore.subscribe((state) => {
      this.isAnalyzing = state.isAnalyzing;
    });
    this.unsubscribe.push(subAnalyzing);
  }

  private renderConvergencePlot() {
    if (!this.convergenceCanvas || !this.convergenceCtx) return;

    const ctx = this.convergenceCtx;
    const width = this.convergenceCanvas.width;
    const height = this.convergenceCanvas.height;
    const padding = { top: 10, right: 10, bottom: 25, left: 40 };

    // Clear
    ctx.fillStyle = '#141420';
    ctx.fillRect(0, 0, width, height);

    if (this.convergenceHistory.length < 2) return;

    // Find data ranges
    const iterations = this.convergenceHistory.map(c => c.iteration);
    const residuals = this.convergenceHistory.map(c => c.residual);
    const minIter = Math.min(...iterations);
    const maxIter = Math.max(...iterations);
    const minRes = Math.min(...residuals);
    const maxRes = Math.max(...residuals);

    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;

    // Scale functions
    const scaleX = (iter: number) => padding.left + ((iter - minIter) / (maxIter - minIter || 1)) * plotWidth;
    const scaleY = (res: number) => padding.top + plotHeight - ((res - minRes) / (maxRes - minRes || 1)) * plotHeight;

    // Draw grid
    ctx.strokeStyle = '#1e1e2a';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (plotHeight / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
    }

    // Draw convergence line
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.beginPath();
    this.convergenceHistory.forEach((point, i) => {
      const x = scaleX(point.iteration);
      const y = scaleY(point.residual);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Draw points
    ctx.fillStyle = '#3b82f6';
    this.convergenceHistory.forEach((point) => {
      const x = scaleX(point.iteration);
      const y = scaleY(point.residual);
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
    });

    // Draw axes labels
    ctx.fillStyle = '#666';
    ctx.font = '10px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Iteration', width / 2, height - 5);

    ctx.save();
    ctx.translate(12, height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Residual', 0, 0);
    ctx.restore();

    // Y-axis ticks
    ctx.textAlign = 'right';
    ctx.fillText(maxRes.toExponential(1), padding.left - 5, padding.top + 4);
    ctx.fillText(minRes.toExponential(1), padding.left - 5, height - padding.bottom);
  }

  firstUpdated() {
    this.convergenceCanvas = this.shadowRoot?.querySelector('#convergence-plot') as HTMLCanvasElement;
    if (this.convergenceCanvas) {
      this.convergenceCtx = this.convergenceCanvas.getContext('2d');
      this.resizeCanvas();
      this.renderConvergencePlot();
    }

    window.addEventListener('resize', () => {
      this.resizeCanvas();
      this.renderConvergencePlot();
    });
  }

  private resizeCanvas() {
    if (this.convergenceCanvas) {
      const parent = this.convergenceCanvas.parentElement;
      if (parent) {
        this.convergenceCanvas.width = parent.clientWidth;
        this.convergenceCanvas.height = parent.clientHeight;
      }
    }
  }

  private getMetrics(): MetricCard[] {
    if (!this.currentResult?.metrics) return [];

    const metrics = this.currentResult.metrics;
    return [
      {
        id: 'cl',
        label: 'Lift Coefficient',
        value: metrics.lift?.toFixed(3) || '—',
        unit: '',
        trend: this.getTrend('lift'),
        color: '#3b82f6'
      },
      {
        id: 'cd',
        label: 'Drag Coefficient',
        value: metrics.drag?.toFixed(4) || '—',
        unit: '',
        trend: this.getTrend('drag'),
        color: '#ef4444'
      },
      {
        id: 'ld',
        label: 'Lift/Drag Ratio',
        value: metrics.liftToDrag?.toFixed(1) || '—',
        unit: '',
        trend: this.getTrend('liftToDrag'),
        color: '#22c55e'
      },
      {
        id: 'cm',
        label: 'Moment Coefficient',
        value: metrics.moment?.toFixed(3) || '—',
        unit: '',
        color: '#f59e0b'
      },
      {
        id: 'clmax',
        label: 'Max Lift Coefficient',
        value: metrics.maxLiftCoefficient?.toFixed(3) || '—',
        unit: '',
        color: '#8b5cf6'
      },
      {
        id: 'stall',
        label: 'Stall Angle',
        value: metrics.stallAngle?.toFixed(1) || '—',
        unit: '°',
        color: '#ec4899'
      }
    ];
  }

  private getTrend(metricId: string): 'up' | 'down' | 'stable' {
    // Simplified trend detection
    if (this.convergenceHistory.length < 3) return 'stable';
    const recent = this.convergenceHistory.slice(-3);
    const diff = recent[2].residual - recent[0].residual;
    if (Math.abs(diff) < 1e-6) return 'stable';
    return diff < 0 ? 'down' : 'up';
  }

  private getConvergenceStatus(): { text: string; class: string; icon: string } {
    if (!this.currentResult?.convergenceHistory?.length) {
      return { text: 'No Data', class: '', icon: '○' };
    }

    const lastConvergence = this.currentResult.convergenceHistory[this.currentResult.convergenceHistory.length - 1];
    const residual = lastConvergence.residual;

    if (residual < 1e-6) {
      return { text: 'Converged', class: 'converged', icon: '✓' };
    } else if (residual > 1) {
      return { text: 'Diverging', class: 'diverging', icon: '✗' };
    } else {
      return { text: `Iter ${lastConvergence.iteration}`, class: 'iterating', icon: '◐' };
    }
  }

  private getResourceColor(percentage: number): string {
    if (percentage < 50) return '#22c55e';
    if (percentage < 80) return '#eab308';
    return '#ef4444';
  }

  render() {
    const hasData = !!this.currentResult;
    const metrics = this.getMetrics();
    const convergenceStatus = this.getConvergenceStatus();
    const currentIteration = this.convergenceHistory.length > 0 
      ? this.convergenceHistory[this.convergenceHistory.length - 1].iteration 
      : 0;
    const maxIterations = 100;

    return html`
      <div class="dashboard">
        ${!hasData ? html`
          <div class="no-data">
            <svg viewBox="0 0 24 24"><path d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/></svg>
            <div class="no-data-text">Run an analysis to see metrics</div>
          </div>
        ` : html`
          <!-- Performance Metrics -->
          <div>
            <div class="section-title">Aerodynamic Coefficients</div>
            <div class="metrics-grid">
              ${metrics.map(metric => html`
                <div class="metric-card ${metric.id === 'ld' ? 'primary' : ''}">
                  <div class="metric-label">
                    ${metric.label}
                  </div>
                  <div class="metric-value">
                    ${metric.value}
                    ${metric.unit ? html`<span class="metric-unit">${metric.unit}</span>` : ''}
                  </div>
                  ${metric.trend ? html`
                    <div class="metric-trend trend-${metric.trend}">
                      ${metric.trend === 'up' ? html`
                        <svg class="trend-icon" viewBox="0 0 24 24"><path fill="currentColor" d="M7 14l5-5 5 5z"/></svg>
                        Improving
                      ` : metric.trend === 'down' ? html`
                        <svg class="trend-icon" viewBox="0 0 24 24"><path fill="currentColor" d="M7 10l5 5 5-5z"/></svg>
                        Worsening
                      ` : html`
                        <svg class="trend-icon" viewBox="0 0 24 24"><path fill="currentColor" d="M6 12h12"/></svg>
                        Stable
                      `}
                    </div>
                  ` : ''}
                </div>
              `)}
            </div>
          </div>

          <!-- Convergence Plot -->
          <div class="convergence-section">
            <div class="section-title">Convergence History</div>
            <div class="plot-container">
              <canvas id="convergence-plot" class="plot-canvas"></canvas>
            </div>
            <div class="plot-legend">
              <div class="legend-item">
                <div class="legend-dot" style="background: #3b82f6"></div>
                <span>Residual</span>
              </div>
            </div>
            <div class="convergence-status">
              <span class="convergence-icon ${convergenceStatus.class}">${convergenceStatus.icon}</span>
              <span class="${convergenceStatus.class}">${convergenceStatus.text}</span>
            </div>
            <div class="iteration-bar">
              <div class="iteration-header">
                <span class="iteration-label">Progress</span>
                <span class="iteration-value">${currentIteration} / ${maxIterations}</span>
              </div>
              <div class="iteration-track">
                <div class="iteration-fill" style="width: ${(currentIteration / maxIterations) * 100}%"></div>
              </div>
            </div>
          </div>

          <!-- Residual History -->
          ${this.residualHistory.length > 0 ? html`
            <div class="residual-section">
              <div class="section-title">Equation Residuals</div>
              <div class="residual-list">
                ${this.residualHistory.slice(0, 6).map(res => html`
                  <div class="residual-item">
                    <span class="residual-name">${res.equation}</span>
                    <div class="residual-bar-container">
                      <div 
                        class="residual-bar" 
                        style="width: ${Math.min(100, Math.max(0, (1 - Math.log10(res.residual + 1e-10) / -10) * 100))}%; background: ${this.getResourceColor(100 - (1 - Math.log10(res.residual + 1e-10) / -10) * 100)}"
                      ></div>
                    </div>
                    <span class="residual-value">${res.residual.toExponential(2)}</span>
                  </div>
                `)}
              </div>
            </div>
          ` : ''}

          <!-- System Resources -->
          ${this.systemResources ? html`
            <div class="resources-section">
              <div class="section-title">System Resources</div>
              <div class="resource-bar">
                <div class="resource-header">
                  <span class="resource-label">CPU Usage</span>
                  <span class="resource-value">${this.systemResources.cpuPercent.toFixed(0)}%</span>
                </div>
                <div class="resource-track">
                  <div class="resource-fill cpu-fill" style="width: ${this.systemResources.cpuPercent}%"></div>
                </div>
              </div>
              <div class="resource-bar">
                <div class="resource-header">
                  <span class="resource-label">Memory</span>
                  <span class="resource-value">${(this.systemResources.memoryUsed / 1024 / 1024 / 1024).toFixed(1)} / ${(this.systemResources.memoryTotal / 1024 / 1024 / 1024).toFixed(1)} GB</span>
                </div>
                <div class="resource-track">
                  <div class="resource-fill memory-fill" style="width: ${(this.systemResources.memoryUsed / this.systemResources.memoryTotal) * 100}%"></div>
                </div>
              </div>
              ${this.systemResources.gpuPercent !== undefined ? html`
                <div class="resource-bar">
                  <div class="resource-header">
                    <span class="resource-label">GPU Usage</span>
                    <span class="resource-value">${this.systemResources.gpuPercent.toFixed(0)}%</span>
                  </div>
                  <div class="resource-track">
                    <div class="resource-fill gpu-fill" style="width: ${this.systemResources.gpuPercent}%"></div>
                  </div>
                </div>
              ` : ''}
            </div>
          ` : ''}

          <!-- Status Row -->
          <div class="status-row">
            <div class="status-badge">
              <div class="status-dot ${this.isAnalyzing ? 'yellow' : 'green'}"></div>
              <span class="status-text">Status:</span>
              <span class="status-value">${this.isAnalyzing ? 'Analyzing...' : 'Ready'}</span>
            </div>
            <div class="status-badge">
              <div class="status-dot blue"></div>
              <span class="status-text">Fidelity:</span>
              <span class="status-value">${this.currentResult?.fidelity || 'N/A'}</span>
            </div>
            <div class="status-badge">
              <div class="status-dot green"></div>
              <span class="status-text">Mesh:</span>
              <span class="status-value">${this.currentResult?.meshQuality?.elementCount?.toLocaleString() || 'N/A'}</span>
            </div>
          </div>
        `}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'metrics-dashboard': MetricsDashboard;
  }
}
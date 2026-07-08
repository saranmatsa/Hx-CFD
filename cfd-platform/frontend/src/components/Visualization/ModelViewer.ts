/**
 * 3D Model Viewer Component
 * Multi-view synchronized visualization
 */

import { LitElement, html, css } from 'lit';
import { customElement, state, query } from 'lit/decorators.js';
import { workspaceStore, useCurrentResult } from '../../stores/workspaceStore';
import { eventBus } from '../../services/EventBus';
import type { AnalysisResult, ScalarField, VectorField, StreamlineData, ViewState } from '../../types/workspace';

type ViewMode = '3d' | 'pressure' | 'velocity' | 'temperature' | 'mesh';

@customElement('model-viewer')
export class ModelViewer extends LitElement {
  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      position: relative;
      background: #0d0d14;
    }

    .viewer-container {
      display: grid;
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr 1fr;
      gap: 1px;
      height: 100%;
      background: #1a1a24;
    }

    .viewer-pane {
      position: relative;
      background: #0d0d14;
      overflow: hidden;
    }

    .viewer-pane.main {
      grid-column: 1 / 2;
      grid-row: 1 / 3;
    }

    .viewer-canvas {
      width: 100%;
      height: 100%;
      display: block;
    }

    .view-label {
      position: absolute;
      top: 12px;
      left: 12px;
      padding: 4px 10px;
      background: rgba(0, 0, 0, 0.7);
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #888;
      pointer-events: none;
    }

    .view-controls {
      position: absolute;
      bottom: 12px;
      left: 12px;
      right: 12px;
      display: flex;
      gap: 8px;
      justify-content: center;
    }

    .view-btn {
      padding: 6px 12px;
      background: rgba(0, 0, 0, 0.7);
      border: 1px solid #2a2a3a;
      border-radius: 4px;
      color: #888;
      font-size: 11px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .view-btn:hover {
      background: rgba(30, 30, 40, 0.9);
      color: #e0e0e0;
    }

    .view-btn.active {
      background: rgba(59, 130, 246, 0.2);
      border-color: #3b82f6;
      color: #3b82f6;
    }

    .colorbar {
      position: absolute;
      right: 12px;
      top: 50%;
      transform: translateY(-50%);
      width: 16px;
      height: 200px;
      border-radius: 4px;
      overflow: hidden;
    }

    .colorbar-gradient {
      width: 100%;
      height: 100%;
    }

    .colorbar-labels {
      position: absolute;
      right: 36px;
      top: 50%;
      transform: translateY(-50%);
      height: 200px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      font-size: 10px;
      color: #888;
    }

    .colorbar-title {
      position: absolute;
      right: 48px;
      top: calc(50% - 120px);
      writing-mode: vertical-rl;
      text-orientation: mixed;
      transform: rotate(180deg);
      font-size: 10px;
      color: #666;
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .legend {
      position: absolute;
      top: 12px;
      right: 12px;
      background: rgba(0, 0, 0, 0.7);
      border-radius: 6px;
      padding: 12px;
      font-size: 11px;
      min-width: 140px;
    }

    .legend-title {
      font-weight: 600;
      color: #fff;
      margin-bottom: 8px;
      padding-bottom: 6px;
      border-bottom: 1px solid #2a2a3a;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
      color: #aaa;
    }

    .legend-color {
      width: 12px;
      height: 12px;
      border-radius: 2px;
    }

    .legend-value {
      margin-left: auto;
      font-variant-numeric: tabular-nums;
      color: #888;
    }

    .cross-section {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 60%;
      height: 60%;
      border: 1px dashed #3b82f6;
      opacity: 0.5;
      pointer-events: none;
    }

    .cross-section-label {
      position: absolute;
      top: -20px;
      left: 50%;
      transform: translateX(-50%);
      background: #3b82f6;
      padding: 2px 8px;
      border-radius: 3px;
      font-size: 10px;
      color: white;
    }

    .loading-overlay {
      position: absolute;
      inset: 0;
      background: rgba(13, 13, 20, 0.9);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
    }

    .loading-spinner {
      width: 32px;
      height: 32px;
      border: 2px solid #2a2a3a;
      border-top-color: #3b82f6;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .loading-text {
      font-size: 12px;
      color: #888;
    }

    .no-data {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
      color: #666;
    }

    .no-data svg {
      width: 48px;
      height: 48px;
      fill: #333;
    }

    .no-data-text {
      font-size: 13px;
    }

    .camera-controls {
      position: absolute;
      bottom: 12px;
      right: 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .camera-btn {
      width: 32px;
      height: 32px;
      background: rgba(0, 0, 0, 0.7);
      border: 1px solid #2a2a3a;
      border-radius: 4px;
      color: #888;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s ease;
    }

    .camera-btn:hover {
      background: rgba(30, 30, 40, 0.9);
      color: #e0e0e0;
    }

    .camera-btn svg {
      width: 16px;
      height: 16px;
      fill: currentColor;
    }

    .slice-controls {
      position: absolute;
      left: 12px;
      bottom: 12px;
      background: rgba(0, 0, 0, 0.7);
      border-radius: 6px;
      padding: 8px 12px;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .slice-label {
      font-size: 11px;
      color: #888;
    }

    .slice-slider {
      width: 100px;
      height: 4px;
      -webkit-appearance: none;
      background: #2a2a3a;
      border-radius: 2px;
      outline: none;
    }

    .slice-slider::-webkit-slider-thumb {
      -webkit-appearance: none;
      width: 12px;
      height: 12px;
      background: #3b82f6;
      border-radius: 50%;
      cursor: pointer;
    }
  `;

  @state() private currentResult: AnalysisResult | null = null;
  @state() private viewMode: ViewMode = '3d';
  @state() private isLoading = false;
  @state() private slicePosition = 0.5;
  @state() private cameraAngle = { x: 30, y: 45 };
  @state() private showStreamlines = true;
  @state() private showPressure = true;
  @state() private showVelocity = false;

  private unsubscribe: (() => void)[] = [];
  private canvas3D: HTMLCanvasElement | null = null;
  private ctx3D: CanvasRenderingContext2D | null = null;

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
      if (result) {
        this.renderVisualization();
      }
    });
    this.unsubscribe.push(unsubResult);

    const unsubMetrics = eventBus.on('METRICS_STREAM', () => {
      if (this.currentResult) {
        this.renderVisualization();
      }
    });
    this.unsubscribe.push(subMetrics);
  }

  private setViewMode(mode: ViewMode) {
    this.viewMode = mode;
    this.renderVisualization();
  }

  private rotateCamera(dx: number, dy: number) {
    this.cameraAngle = {
      x: Math.max(-90, Math.min(90, this.cameraAngle.x + dy)),
      y: (this.cameraAngle.y + dx) % 360
    };
    this.renderVisualization();
  }

  private resetCamera() {
    this.cameraAngle = { x: 30, y: 45 };
    this.slicePosition = 0.5;
    this.renderVisualization();
  }

  private zoomIn() {
    this.renderVisualization();
  }

  private zoomOut() {
    this.renderVisualization();
  }

  private renderVisualization() {
    if (!this.canvas3D || !this.ctx3D) return;

    const ctx = this.ctx3D;
    const width = this.canvas3D.width;
    const height = this.canvas3D.height;

    // Clear canvas
    ctx.fillStyle = '#0d0d14';
    ctx.fillRect(0, 0, width, height);

    if (!this.currentResult) {
      this.renderNoDataMessage(ctx, width, height);
      return;
    }

    // Render based on view mode
    switch (this.viewMode) {
      case 'pressure':
        this.renderPressureField(ctx, width, height);
        break;
      case 'velocity':
        this.renderVelocityField(ctx, width, height);
        break;
      case 'temperature':
        this.renderTemperatureField(ctx, width, height);
        break;
      case 'mesh':
        this.renderMesh(ctx, width, height);
        break;
      case '3d':
      default:
        this.render3DView(ctx, width, height);
    }
  }

  private renderNoDataMessage(ctx: CanvasRenderingContext2D, width: number, height: number) {
    ctx.fillStyle = '#666';
    ctx.font = '13px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('No analysis results yet', width / 2, height / 2 - 10);
    ctx.fillStyle = '#444';
    ctx.font = '11px Inter, sans-serif';
    ctx.fillText('Run an analysis to see results', width / 2, height / 2 + 10);
  }

  private render3DView(ctx: CanvasRenderingContext2D, width: number, height: number) {
    const centerX = width / 2;
    const centerY = height / 2;
    const scale = Math.min(width, height) * 0.3;

    // Apply camera rotation
    const rotX = this.cameraAngle.x * Math.PI / 180;
    const rotY = this.cameraAngle.y * Math.PI / 180;

    // Draw coordinate axes
    this.drawAxes(ctx, centerX, centerY, scale, rotX, rotY);

    // Draw wing shape (simplified)
    this.drawWingShape(ctx, centerX, centerY, scale, rotX, rotY);

    // Draw streamlines if enabled
    if (this.showStreamlines && this.currentResult?.streamlines) {
      this.drawStreamlines(ctx, centerX, centerY, scale, rotX, rotY);
    }

    // Draw pressure contours if enabled
    if (this.showPressure && this.currentResult?.scalarFields?.pressure) {
      this.drawPressureContours(ctx, centerX, centerY, scale, rotX, rotY);
    }
  }

  private drawAxes(ctx: CanvasRenderingContext2D, cx: number, cy: number, scale: number, rotX: number, rotY: number) {
    const axes = [
      { dir: [1, 0, 0], color: '#dc2626', label: 'X' },
      { dir: [0, 1, 0], color: '#22c55e', label: 'Y' },
      { dir: [0, 0, 1], color: '#3b82f6', label: 'Z' }
    ];

    ctx.font = '10px Inter, sans-serif';
    axes.forEach(axis => {
      const rotated = this.rotate3D(axis.dir, rotX, rotY);
      const endX = cx + rotated[0] * scale * 1.2;
      const endY = cy - rotated[1] * scale * 1.2;
      
      ctx.strokeStyle = axis.color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(endX, endY);
      ctx.stroke();

      ctx.fillStyle = axis.color;
      ctx.fillText(axis.label, endX + 5, endY - 5);
    });
  }

  private drawWingShape(ctx: CanvasRenderingContext2D, cx: number, cy: number, scale: number, rotX: number, rotY: number) {
    // Simplified wing cross-section (airfoil shape)
    const chord = 1.5 * scale;
    const thickness = 0.15 * chord;

    // Airfoil points
    const points: [number, number][] = [];
    for (let t = 0; t <= 1; t += 0.05) {
      const x = t * chord - chord / 2;
      const y = thickness * Math.sin(Math.PI * t) * (t < 0.5 ? 1 : -1);
      points.push([x, y]);
    }

    // Transform and draw
    ctx.strokeStyle = '#888';
    ctx.lineWidth = 2;
    ctx.beginPath();

    points.forEach((point, i) => {
      const rotated = this.rotate3D([point[0], point[1], 0], rotX, rotY);
      const screenX = cx + rotated[0];
      const screenY = cy - rotated[1];

      if (i === 0) {
        ctx.moveTo(screenX, screenY);
      } else {
        ctx.lineTo(screenX, screenY);
      }
    });

    ctx.stroke();

    // Draw wing planform
    const span = 2 * scale;
    ctx.strokeStyle = '#666';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx - chord / 2, cy);
    ctx.lineTo(cx - chord / 2, cy - span / 2);
    ctx.moveTo(cx + chord / 2, cy);
    ctx.lineTo(cx + chord / 2, cy - span / 2);
    ctx.stroke();
  }

  private drawStreamlines(ctx: CanvasRenderingContext2D, cx: number, cy: number, scale: number, rotX: number, rotY: number) {
    if (!this.currentResult?.streamlines) return;

    const streamlines = this.currentResult.streamlines;
    const colors = ['#3b82f6', '#8b5cf6', '#ec4899'];

    streamlines.forEach((streamline, idx) => {
      if (streamline.points.length < 2) return;

      ctx.strokeStyle = colors[idx % colors.length];
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 0.7;
      ctx.beginPath();

      streamline.points.forEach((point, i) => {
        const scaled = [point[0] * scale * 0.5, point[1] * scale * 0.5, point[2] * scale * 0.5];
        const rotated = this.rotate3D(scaled, rotX, rotY);
        const screenX = cx + rotated[0];
        const screenY = cy - rotated[1];

        if (i === 0) {
          ctx.moveTo(screenX, screenY);
        } else {
          ctx.lineTo(screenX, screenY);
        }
      });

      ctx.stroke();
      ctx.globalAlpha = 1;
    });
  }

  private drawPressureContours(ctx: CanvasRenderingContext2D, cx: number, cy: number, scale: number, rotX: number, rotY: number) {
    if (!this.currentResult?.scalarFields?.pressure) return;

    const pressure = this.currentResult.scalarFields.pressure;
    const minP = Math.min(...pressure.values);
    const maxP = Math.max(...pressure.values);

    // Draw contour lines
    const numContours = 8;
    for (let i = 0; i <= numContours; i++) {
      const level = minP + (maxP - minP) * (i / numContours);
      const alpha = 0.3 + 0.4 * (i / numContours);
      
      ctx.strokeStyle = `rgba(59, 130, 246, ${alpha})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      
      // Simplified contour visualization
      const offset = (i - numContours / 2) * 10;
      ctx.arc(cx, cy + offset, 50 + i * 10, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  private renderPressureField(ctx: CanvasRenderingContext2D, width: number, height: number) {
    if (!this.currentResult?.scalarFields?.pressure) return;

    const pressure = this.currentResult.scalarFields.pressure;
    const values = pressure.values;
    const gridSize = Math.sqrt(values.length);
    
    const cellWidth = width / gridSize;
    const cellHeight = height / gridSize;

    // Create color map (blue = low, red = high)
    const minP = Math.min(...values);
    const maxP = Math.max(...values);
    const range = maxP - minP || 1;

    for (let i = 0; i < gridSize; i++) {
      for (let j = 0; j < gridSize; j++) {
        const value = values[i * gridSize + j];
        const normalized = (value - minP) / range;
        
        // Blue to red gradient
        const r = Math.floor(255 * normalized);
        const g = Math.floor(100 * normalized);
        const b = Math.floor(255 * (1 - normalized));
        
        ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
        ctx.fillRect(j * cellWidth, i * cellHeight, cellWidth + 1, cellHeight + 1);
      }
    }
  }

  private renderVelocityField(ctx: CanvasRenderingContext2D, width: number, height: number) {
    if (!this.currentResult?.vectorFields?.velocity) return;

    const velocity = this.currentResult.vectorFields.velocity;
    const vectors = velocity.vectors;
    const gridSize = Math.sqrt(vectors.length);
    
    const cellWidth = width / gridSize;
    const cellHeight = height / gridSize;

    // Find max magnitude for scaling
    let maxMag = 0;
    vectors.forEach(v => {
      const mag = Math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2);
      maxMag = Math.max(maxMag, mag);
    });

    vectors.forEach((vector, idx) => {
      const i = Math.floor(idx / gridSize);
      const j = idx % gridSize;
      
      const cx = (j + 0.5) * cellWidth;
      const cy = (i + 0.5) * cellHeight;
      
      const mag = Math.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2);
      const normalized = mag / maxMag;
      
      // Color by magnitude
      const hue = 240 - normalized * 240; // Blue to red
      ctx.strokeStyle = `hsl(${hue}, 80%, 50%)`;
      ctx.lineWidth = 1;
      
      // Draw arrow
      const scale = cellWidth * 0.4;
      const dx = (vector[0] / (mag || 1)) * scale * normalized;
      const dy = (vector[1] / (mag || 1)) * scale * normalized;
      
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + dx, cy + dy);
      ctx.stroke();
    });
  }

  private renderTemperatureField(ctx: CanvasRenderingContext2D, width: number, height: number) {
    if (!this.currentResult?.scalarFields?.temperature) return;

    const temp = this.currentResult.scalarFields.temperature;
    const values = temp.values;
    const gridSize = Math.sqrt(values.length);
    
    const cellWidth = width / gridSize;
    const cellHeight = height / gridSize;

    const minT = Math.min(...values);
    const maxT = Math.max(...values);
    const range = maxT - minT || 1;

    for (let i = 0; i < gridSize; i++) {
      for (let j = 0; j < gridSize; j++) {
        const value = values[i * gridSize + j];
        const normalized = (value - minT) / range;
        
        // Cool to hot gradient
        const r = Math.floor(255 * normalized);
        const g = Math.floor(200 * (1 - Math.abs(normalized - 0.5) * 2));
        const b = Math.floor(255 * (1 - normalized));
        
        ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
        ctx.fillRect(j * cellWidth, i * cellHeight, cellWidth + 1, cellHeight + 1);
      }
    }
  }

  private renderMesh(ctx: CanvasRenderingContext2D, width: number, height: number) {
    if (!this.currentResult?.meshQuality) return;

    const mesh = this.currentResult.meshQuality;
    
    ctx.strokeStyle = '#3a3a4a';
    ctx.lineWidth = 0.5;

    // Draw simplified mesh representation
    const gridSize = 20;
    const cellW = width / gridSize;
    const cellH = height / gridSize;

    for (let i = 0; i < gridSize; i++) {
      for (let j = 0; j < gridSize; j++) {
        const quality = mesh.averageQuality || 0.9;
        const alpha = 0.3 + 0.7 * quality;
        
        ctx.strokeStyle = `rgba(59, 130, 246, ${alpha})`;
        ctx.strokeRect(j * cellW, i * cellH, cellW, cellH);
      }
    }

    // Draw element count
    ctx.fillStyle = '#888';
    ctx.font = '12px Inter, sans-serif';
    ctx.fillText(`Elements: ${mesh.elementCount?.toLocaleString() || 'N/A'}`, 12, height - 12);
  }

  private rotate3D(point: number[], rotX: number, rotY: number): number[] {
    let [x, y, z] = point;
    
    // Rotate around Y axis
    const cosY = Math.cos(rotY);
    const sinY = Math.sin(rotY);
    const x1 = x * cosY + z * sinY;
    const z1 = -x * sinY + z * cosY;
    
    // Rotate around X axis
    const cosX = Math.cos(rotX);
    const sinX = Math.sin(rotX);
    const y1 = y * cosX - z1 * sinX;
    const z2 = y * sinX + z1 * cosX;
    
    return [x1, y1, z2];
  }

  firstUpdated() {
    this.canvas3D = this.shadowRoot?.querySelector('#canvas-3d') as HTMLCanvasElement;
    if (this.canvas3D) {
      this.ctx3D = this.canvas3D.getContext('2d');
      this.resizeCanvas();
      this.renderVisualization();
    }

    window.addEventListener('resize', () => this.resizeCanvas());
  }

  private resizeCanvas() {
    if (this.canvas3D) {
      const parent = this.canvas3D.parentElement;
      if (parent) {
        this.canvas3D.width = parent.clientWidth;
        this.canvas3D.height = parent.clientHeight;
        this.renderVisualization();
      }
    }
  }

  private getColorbarGradient(): string {
    switch (this.viewMode) {
      case 'pressure':
        return 'linear-gradient(to top, #3b82f6, #22c55e, #eab308, #ef4444)';
      case 'velocity':
        return 'linear-gradient(to top, #3b82f6, #8b5cf6, #ec4899, #ef4444)';
      case 'temperature':
        return 'linear-gradient(to top, #3b82f6, #22c55e, #eab308, #ef4444)';
      default:
        return 'linear-gradient(to top, #3b82f6, #8b5cf6)';
    }
  }

  private getColorbarTitle(): string {
    switch (this.viewMode) {
      case 'pressure': return 'Pressure (Pa)';
      case 'velocity': return 'Velocity (m/s)';
      case 'temperature': return 'Temperature (K)';
      default: return '';
    }
  }

  render() {
    const hasData = !!this.currentResult;

    return html`
      <div class="viewer-container">
        <!-- Main 3D View -->
        <div class="viewer-pane main">
          <span class="view-label">3D View</span>
          <canvas 
            id="canvas-3d" 
            class="viewer-canvas"
            @wheel=${(e: WheelEvent) => {
              e.preventDefault();
              if (e.deltaY < 0) this.zoomIn();
              else this.zoomOut();
            }}
          ></canvas>
          
          ${hasData ? html`
            <div class="legend">
              <div class="legend-title">Current Results</div>
              ${this.currentResult?.metrics ? html`
                <div class="legend-item">
                  <span class="legend-color" style="background: #3b82f6"></span>
                  <span>CL</span>
                  <span class="legend-value">${this.currentResult.metrics.lift?.toFixed(3) || 'N/A'}</span>
                </div>
                <div class="legend-item">
                  <span class="legend-color" style="background: #22c55e"></span>
                  <span>CD</span>
                  <span class="legend-value">${this.currentResult.metrics.drag?.toFixed(4) || 'N/A'}</span>
                </div>
                <div class="legend-item">
                  <span class="legend-color" style="background: #eab308"></span>
                  <span>L/D</span>
                  <span class="legend-value">${this.currentResult.metrics.liftToDrag?.toFixed(1) || 'N/A'}</span>
                </div>
              ` : ''}
            </div>
          ` : ''}

          <div class="view-controls">
            <button class="view-btn ${this.viewMode === '3d' ? 'active' : ''}" @click=${() => this.setViewMode('3d')}>3D</button>
            <button class="view-btn ${this.viewMode === 'pressure' ? 'active' : ''}" @click=${() => this.setViewMode('pressure')}>Pressure</button>
            <button class="view-btn ${this.viewMode === 'velocity' ? 'active' : ''}" @click=${() => this.setViewMode('velocity')}>Velocity</button>
            <button class="view-btn ${this.viewMode === 'temperature' ? 'active' : ''}" @click=${() => this.setViewMode('temperature')}>Thermal</button>
            <button class="view-btn ${this.viewMode === 'mesh' ? 'active' : ''}" @click=${() => this.setViewMode('mesh')}>Mesh</button>
          </div>

          <div class="camera-controls">
            <button class="camera-btn" @click=${() => this.rotateCamera(0, -10)} title="Rotate Up">
              <svg viewBox="0 0 24 24"><path d="M7.41 15.41L12 10.83l4.59 4.58L18 14l-6-6-6 6z"/></svg>
            </button>
            <button class="camera-btn" @click=${() => this.rotateCamera(0, 10)} title="Rotate Down">
              <svg viewBox="0 0 24 24"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z"/></svg>
            </button>
            <button class="camera-btn" @click=${() => this.rotateCamera(-10, 0)} title="Rotate Left">
              <svg viewBox="0 0 24 24"><path d="M15.41 16.59L10.83 12l4.58-4.59L14 6l-6 6 6 6z"/></svg>
            </button>
            <button class="camera-btn" @click=${() => this.rotateCamera(10, 0)} title="Rotate Right">
              <svg viewBox="0 0 24 24"><path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z"/></svg>
            </button>
            <button class="camera-btn" @click=${this.resetCamera} title="Reset View">
              <svg viewBox="0 0 24 24"><path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/></svg>
            </button>
          </div>

          ${this.viewMode !== '3d' && this.viewMode !== 'mesh' ? html`
            <div class="colorbar">
              <div class="colorbar-gradient" style="background: ${this.getColorbarGradient()}"></div>
            </div>
            <div class="colorbar-labels">
              <span>High</span>
              <span>Mid</span>
              <span>Low</span>
            </div>
            <div class="colorbar-title">${this.getColorbarTitle()}</div>
          ` : ''}
        </div>

        <!-- Cross-section View -->
        <div class="viewer-pane">
          <span class="view-label">Cross-Section</span>
          <canvas class="viewer-canvas" id="canvas-section"></canvas>
          <div class="cross-section">
            <span class="cross-section-label">Slice at ${(this.slicePosition * 100).toFixed(0)}%</span>
          </div>
        </div>

        <!-- Top View -->
        <div class="viewer-pane">
          <span class="view-label">Top View</span>
          <canvas class="viewer-canvas" id="canvas-top"></canvas>
        </div>
      </div>

      ${this.isLoading ? html`
        <div class="loading-overlay">
          <div class="loading-spinner"></div>
          <div class="loading-text">Rendering visualization...</div>
        </div>
      ` : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'model-viewer': ModelViewer;
  }
}
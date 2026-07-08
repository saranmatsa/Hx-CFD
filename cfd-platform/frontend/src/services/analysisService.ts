/**
 * WebSocket Service for Real-Time Analysis Communication
 * Handles streaming results, progressive updates, and bidirectional events
 */

import type {
  WSMessage,
  WSAnalysisRequest,
  WSAnalysisResponse,
  WSMetricsStream,
  ParameterChangeEvent,
  EngineeringMetrics,
  AnalysisResult,
  FidelityLevel
} from '../types/workspace';
import { eventBus, emitMetricsStream, emitAnalysisUpdate, emitParameterChange } from './EventBus';

type MessageHandler = (message: WSMessage) => void;

class AnalysisWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private messageQueue: WSMessage[] = [];
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private isConnected = false;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private correlationId = 0;
  private pendingRequests: Map<string, {
    resolve: (value: unknown) => void;
    reject: (error: Error) => void;
    timeout: ReturnType<typeof setTimeout>;
  }> = new Map();

  constructor(url: string = 'ws://localhost:8765') {
    this.url = url;
  }

  /**
   * Connect to WebSocket server
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
          console.log('[WS] Connected to analysis server');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.startPing();
          this.flushMessageQueue();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data) as WSMessage;
            this.handleMessage(message);
          } catch (error) {
            console.error('[WS] Failed to parse message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('[WS] WebSocket error:', error);
        };

        this.ws.onclose = () => {
          console.log('[WS] Connection closed');
          this.isConnected = false;
          this.stopPing();
          this.attemptReconnect();
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.stopPing();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
  }

  /**
   * Send message to server
   */
  private send(message: WSMessage): void {
    if (this.ws && this.isConnected) {
      this.ws.send(JSON.stringify(message));
    } else {
      this.messageQueue.push(message);
    }
  }

  /**
   * Flush queued messages
   */
  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (message) {
        this.send(message);
      }
    }
  }

  /**
   * Handle incoming message
   */
  private handleMessage(message: WSMessage): void {
    // Handle response to pending requests
    if (message.correlationId && this.pendingRequests.has(message.correlationId)) {
      const pending = this.pendingRequests.get(message.correlationId)!;
      clearTimeout(pending.timeout);
      pending.resolve(message.payload);
      this.pendingRequests.delete(message.correlationId);
    }

    // Emit to registered handlers
    const handlers = this.handlers.get(message.type) || new Set();
    handlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error(`[WS] Handler error for ${message.type}:`, error);
      }
    });

    // Handle specific message types
    switch (message.type) {
      case 'ANALYSIS_RESPONSE':
        this.handleAnalysisResponse(message as unknown as WSAnalysisResponse);
        break;
      case 'METRICS_STREAM':
        this.handleMetricsStream(message as unknown as WSMetricsStream);
        break;
      case 'CONVERGENCE':
        this.handleConvergence(message);
        break;
      case 'PARAMETER_CHANGE':
        this.handleParameterChange(message);
        break;
      case 'ERROR':
        this.handleError(message);
        break;
    }
  }

  private handleAnalysisResponse(message: WSAnalysisResponse): void {
    emitAnalysisUpdate({
      id: message.payload.resultId,
      status: message.payload.status,
      progress: message.payload.progress,
      metrics: message.payload.metrics
    } as Partial<AnalysisResult>, true);
  }

  private handleMetricsStream(message: WSMetricsStream): void {
    emitMetricsStream(message.payload.metrics);
  }

  private handleConvergence(message: WSMessage): void {
    eventBus.emit({
      type: 'CONVERGENCE',
      data: message.payload as any
    });
  }

  private handleParameterChange(message: WSMessage): void {
    const payload = message.payload as any;
    emitParameterChange(payload.parameterId, payload.oldValue, payload.newValue, 'user');
  }

  private handleError(message: WSMessage): void {
    console.error('[WS] Server error:', message.payload);
  }

  /**
   * Subscribe to message type
   */
  on(type: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler);

    return () => {
      this.handlers.get(type)?.delete(handler);
    };
  }

  /**
   * Send analysis request
   */
  async requestAnalysis(
    parameters: Record<string, number>,
    fidelity: FidelityLevel = 'medium',
    incremental: boolean = true
  ): Promise<WSAnalysisResponse> {
    const correlationId = this.generateCorrelationId();
    
    const request: WSAnalysisRequest = {
      type: 'ANALYSIS_REQUEST',
      payload: { parameters, fidelity, incremental },
      timestamp: Date.now(),
      correlationId
    };

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(correlationId);
        reject(new Error('Analysis request timed out'));
      }, 60000);

      this.pendingRequests.set(correlationId, { resolve: resolve as any, reject, timeout });
      this.send(request);
    });
  }

  /**
   * Send parameter change to server
   */
  sendParameterChange(parameterId: string, oldValue: number, newValue: number): void {
    this.send({
      type: 'PARAMETER_CHANGE',
      payload: { parameterId, oldValue, newValue },
      timestamp: Date.now()
    });
  }

  /**
   * Request mesh regeneration
   */
  requestMeshRegeneration(): void {
    this.send({
      type: 'MESH_REQUEST',
      payload: { timestamp: Date.now() }
    });
  }

  /**
   * Cancel ongoing analysis
   */
  cancelAnalysis(): void {
    this.send({
      type: 'CANCEL_ANALYSIS',
      payload: { timestamp: Date.now() }
    });
  }

  /**
   * Request specific metrics
   */
  requestMetrics(metrics: string[]): void {
    this.send({
      type: 'METRICS_REQUEST',
      payload: { metrics },
      timestamp: Date.now()
    });
  }

  /**
   * Attempt to reconnect
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WS] Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`[WS] Attempting reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      this.connect().catch(() => {
        // Will trigger another reconnect attempt
      });
    }, delay);
  }

  /**
   * Start ping interval
   */
  private startPing(): void {
    this.pingInterval = setInterval(() => {
      if (this.isConnected) {
        this.send({ type: 'PING', payload: null, timestamp: Date.now() });
      }
    }, 30000);
  }

  /**
   * Stop ping interval
   */
  private stopPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private generateCorrelationId(): string {
    return `req-${++this.correlationId}-${Date.now()}`;
  }

  get connectionStatus(): boolean {
    return this.isConnected;
  }
}

// Singleton instance
export const analysisWS = new AnalysisWebSocket();

// ============================================================
// HTTP API Service (for non-streaming requests)
// ============================================================

class AnalysisAPI {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8765') {
    this.baseUrl = baseUrl;
  }

  async analyze(
    parameters: Record<string, number>,
    fidelity: FidelityLevel = 'medium'
  ): Promise<AnalysisResult> {
    const response = await fetch(`${this.baseUrl}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ parameters, fidelity })
    });

    if (!response.ok) {
      throw new Error(`Analysis failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getParameters(): Promise<Record<string, any>> {
    const response = await fetch(`${this.baseUrl}/api/parameters`);
    return response.json();
  }

  async updateParameter(id: string, value: number): Promise<void> {
    await fetch(`${this.baseUrl}/api/parameters/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value })
    });
  }

  async getMeshQuality(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/mesh/quality`);
    return response.json();
  }

  async exportResults(format: 'vtk' | 'csv' | 'json'): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/api/export?format=${format}`);
    return response.blob();
  }
}

export const analysisAPI = new AnalysisAPI();

export { AnalysisWebSocket };
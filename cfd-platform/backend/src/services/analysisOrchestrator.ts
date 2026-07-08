/**
 * Analysis Orchestration Service
 * Coordinates multi-fidelity analysis across compute resources
 */

import { EventEmitter } from 'events';
import { Worker } from 'worker_threads';
import * as path from 'path';
import * as os from 'os';

export interface AnalysisRequest {
  id: string;
  parameters: Record<string, number>;
  fidelity: 'instant' | 'medium' | 'high';
  priority?: number;
  callback?: (result: AnalysisResult) => void;
}

export interface AnalysisResult {
  id: string;
  metrics: EngineeringMetrics;
  fidelity: 'instant' | 'medium' | 'high';
  convergenceHistory?: ConvergenceData[];
  meshQuality?: MeshQualityMetrics;
  timestamp: number;
  computationTime: number;
  workerId?: string;
}

export interface EngineeringMetrics {
  lift?: number;
  drag?: number;
  moment?: number;
  liftToDrag?: number;
  maxLiftCoefficient?: number;
  stallAngle?: number;
  pressure?: number;
  temperature?: number;
  stress?: number;
  displacement?: number;
  frequency?: number;
  modeShape?: number;
}

export interface ConvergenceData {
  iteration: number;
  residual: number;
  time?: number;
}

export interface MeshQualityMetrics {
  elementCount: number;
  vertexCount: number;
  aspectRatio: { min: number; max: number; avg: number };
  skewness: { min: number; max: number; avg: number };
  orthogonality: { min: number; max: number; avg: number };
  boundingBox?: { min: number[]; max: number[] };
  meshQuality: 'excellent' | 'good' | 'fair' | 'poor';
}

export interface WorkerPool {
  maxWorkers: number;
  availableWorkers: string[];
  busyWorkers: Map<string, string[]>;
  queue: AnalysisRequest[];
}

export interface CacheEntry {
  key: string;
  result: AnalysisResult;
  timestamp: number;
  accessCount: number;
  ttl: number;
}

export class AnalysisOrchestrator extends EventEmitter {
  private workerPool: WorkerPool;
  private cache: Map<string, CacheEntry> = new Map();
  private activeAnalyses: Map<string, AnalysisRequest> = new Map();
  private results: Map<string, AnalysisResult> = new Map();
  
  private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes
  private readonly MAX_CACHE_SIZE = 100;
  private readonly WORKER_SCRIPT = path.join(__dirname, 'analysis.worker.js');

  constructor(options: { maxWorkers?: number } = {}) {
    super();
    
    const maxWorkers = options.maxWorkers || Math.max(1, os.cpus().length - 1);
    
    this.workerPool = {
      maxWorkers,
      availableWorkers: [],
      busyWorkers: new Map(),
      queue: []
    };

    this.initializeWorkerPool();
    this.startCacheCleanup();
  }

  private async initializeWorkerPool() {
    // In browser environment, use Web Workers
    if (typeof window !== 'undefined') {
      // Web Workers will be created on-demand
      this.workerPool.availableWorkers = ['browser-pool'];
      return;
    }

    // Node.js environment - create worker threads
    for (let i = 0; i < this.workerPool.maxWorkers; i++) {
      const workerId = `worker-${i}`;
      try {
        const worker = new Worker(this.WORKER_SCRIPT);
        this.workerPool.availableWorkers.push(workerId);
        
        worker.on('message', (message) => this.handleWorkerMessage(workerId, message));
        worker.on('error', (error) => this.handleWorkerError(workerId, error));
        worker.on('exit', (code) => {
          if (code !== 0) {
            console.error(`Worker ${workerId} exited with code ${code}`);
            this.workerPool.availableWorkers = this.workerPool.availableWorkers.filter(
              id => id !== workerId
            );
          }
        });
      } catch (error) {
        console.error(`Failed to create worker ${workerId}:`, error);
      }
    }
  }

  private handleWorkerMessage(workerId: string, message: any) {
    const { type, id, payload } = message;

    switch (type) {
      case 'RESULT':
        this.handleAnalysisComplete(id, payload);
        break;
      case 'PROGRESS':
        this.emit('progress', { id, ...payload });
        break;
      case 'ERROR':
        this.handleWorkerError(workerId, new Error(payload.message));
        break;
    }

    // Mark worker as available
    this.workerPool.availableWorkers.push(workerId);
    this.workerPool.busyWorkers.delete(workerId);

    // Process next in queue
    this.processQueue();
  }

  private handleWorkerError(workerId: string, error: Error) {
    console.error(`Worker ${workerId} error:`, error);
    this.emit('workerError', { workerId, error });
    
    // Remove failed worker and process queue
    this.workerPool.availableWorkers = this.workerPool.availableWorkers.filter(
      id => id !== workerId
    );
    this.workerPool.busyWorkers.delete(workerId);
    this.processQueue();
  }

  private handleAnalysisComplete(requestId: string, result: AnalysisResult) {
    this.activeAnalyses.delete(requestId);
    this.results.set(requestId, result);
    
    // Cache the result
    this.cacheResult(requestId, result);

    const request = this.activeAnalyses.get(requestId);
    if (request?.callback) {
      request.callback(result);
    }

    this.emit('analysisComplete', { id: requestId, result });
  }

  private processQueue() {
    if (this.workerPool.queue.length === 0) return;
    if (this.workerPool.availableWorkers.length === 0) return;

    // Sort by priority
    this.workerPool.queue.sort((a, b) => (b.priority || 0) - (a.priority || 0));

    const request = this.workerPool.queue.shift();
    if (request) {
      this.executeAnalysis(request);
    }
  }

  private async executeAnalysis(request: AnalysisRequest) {
    const workerId = this.workerPool.availableWorkers.shift();
    if (!workerId) {
      this.workerPool.queue.unshift(request);
      return;
    }

    this.activeAnalyses.set(request.id, request);
    this.workerPool.busyWorkers.set(workerId, [request.id]);

    // Check cache first
    const cacheKey = this.getCacheKey(request.parameters, request.fidelity);
    const cached = this.getCachedResult(cacheKey);
    if (cached) {
      this.handleAnalysisComplete(request.id, { ...cached, id: request.id });
      return;
    }

    // In browser, use Web Worker
    if (typeof window !== 'undefined') {
      this.executeInBrowser(request);
      return;
    }

    // In Node.js, use worker thread
    // Worker message would be sent here
    this.emit('analysisStarted', { id: request.id, workerId });
  }

  private executeInBrowser(request: AnalysisRequest) {
    // Create Web Worker
    const worker = new Worker(
      new URL('../workers/analysis.worker.ts', import.meta.url),
      { type: 'module' }
    );

    worker.onmessage = (event) => {
      const { type, payload } = event.data;
      
      if (type === 'RESULT') {
        this.handleAnalysisComplete(request.id, payload);
        worker.terminate();
      } else if (type === 'PROGRESS') {
        this.emit('progress', { id: request.id, ...payload });
      } else if (type === 'ERROR') {
        this.handleWorkerError('browser', new Error(payload.message));
        worker.terminate();
      }
    };

    worker.postMessage({
      type: request.fidelity === 'instant' ? 'SURROGATE' : 'ANALYZE',
      id: request.id,
      payload: {
        parameters: request.parameters,
        fidelity: request.fidelity
      }
    });
  }

  public async analyze(
    parameters: Record<string, number>,
    fidelity: 'instant' | 'medium' | 'high' = 'medium',
    options: { priority?: number; timeout?: number } = {}
  ): Promise<AnalysisResult> {
    const id = `analysis-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    return new Promise((resolve, reject) => {
      const request: AnalysisRequest = {
        id,
        parameters,
        fidelity,
        priority: options.priority,
        callback: resolve
      };

      // Set timeout
      const timeout = options.timeout || (fidelity === 'instant' ? 1000 : fidelity === 'medium' ? 30000 : 300000);
      const timeoutId = setTimeout(() => {
        this.activeAnalyses.delete(id);
        reject(new Error(`Analysis ${id} timed out after ${timeout}ms`));
      }, timeout);

      request.callback = (result) => {
        clearTimeout(timeoutId);
        resolve(result);
      };

      this.workerPool.queue.push(request);
      this.processQueue();
    });
  }

  public cancel(id: string): boolean {
    const index = this.workerPool.queue.findIndex(r => r.id === id);
    if (index !== -1) {
      this.workerPool.queue.splice(index, 1);
      return true;
    }
    
    if (this.activeAnalyses.has(id)) {
      this.activeAnalyses.delete(id);
      this.emit('analysisCancelled', { id });
      return true;
    }

    return false;
  }

  public getActiveAnalyses(): string[] {
    return Array.from(this.activeAnalyses.keys());
  }

  public getQueueLength(): number {
    return this.workerPool.queue.length;
  }

  // Cache management
  private getCacheKey(parameters: Record<string, number>, fidelity: string): string {
    const sortedParams = Object.entries(parameters)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([k, v]) => `${k}:${v.toFixed(4)}`)
      .join('|');
    return `${fidelity}:${sortedParams}`;
  }

  private cacheResult(key: string, result: AnalysisResult) {
    // Evict old entries if cache is full
    if (this.cache.size >= this.MAX_CACHE_SIZE) {
      const oldest = Array.from(this.cache.entries())
        .sort((a, b) => a[1].timestamp - b[1].timestamp)[0];
      this.cache.delete(oldest[0]);
    }

    this.cache.set(key, {
      key,
      result,
      timestamp: Date.now(),
      accessCount: 1,
      ttl: this.CACHE_TTL
    });
  }

  private getCachedResult(key: string): AnalysisResult | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    // Check TTL
    if (Date.now() - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      return null;
    }

    // Update access count
    entry.accessCount++;
    entry.timestamp = Date.now();

    return entry.result;
  }

  public clearCache(): void {
    this.cache.clear();
  }

  private startCacheCleanup() {
    setInterval(() => {
      const now = Date.now();
      for (const [key, entry] of this.cache.entries()) {
        if (now - entry.timestamp > entry.ttl) {
          this.cache.delete(key);
        }
      }
    }, 60000); // Every minute
  }

  public dispose() {
    this.activeAnalyses.clear();
    this.workerPool.queue = [];
    this.cache.clear();
    this.removeAllListeners();
  }
}

// Singleton instance
let orchestratorInstance: AnalysisOrchestrator | null = null;

export function getOrchestrator(): AnalysisOrchestrator {
  if (!orchestratorInstance) {
    orchestratorInstance = new AnalysisOrchestrator();
  }
  return orchestratorInstance;
}

export function createOrchestrator(options?: { maxWorkers?: number }): AnalysisOrchestrator {
  if (orchestratorInstance) {
    orchestratorInstance.dispose();
  }
  orchestratorInstance = new AnalysisOrchestrator(options);
  return orchestratorInstance;
}
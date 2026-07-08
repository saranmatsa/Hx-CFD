/**
 * Progressive Analysis Engine
 * Manages three-tier fidelity system: instant surrogate → medium fidelity → high-fidelity
 */

import type {
  ParameterChangeEvent,
  AnalysisResult,
  EngineeringMetrics,
  FidelityLevel,
  SolverConfig,
  CacheEntry
} from '../types/workspace';
import { eventBus, createDebouncedParameterEmitter } from '../services/EventBus';
import { analysisWS, analysisAPI } from '../services/analysisService';
import { workspaceStore } from '../stores/workspaceStore';

interface AnalysisJob {
  id: string;
  fidelity: FidelityLevel;
  status: 'pending' | 'running' | 'completed' | 'cancelled';
  startTime: number;
  result?: AnalysisResult;
  cancel: () => void;
}

class ProgressiveAnalysisEngine {
  private surrogateCache: Map<string, CacheEntry> = new Map();
  private analysisJobs: Map<string, AnalysisJob> = new Map();
  private currentJobId: string | null = null;
  private parameterHistory: ParameterChangeEvent[] = [];
  private maxHistorySize = 50;
  private debouncedAnalyze: (params: Record<string, number>) => void;
  private surrogateModel: SurrogateModel | null = null;

  constructor() {
    // Create debounced analyzer for slider updates (100ms)
    this.debouncedAnalyze = createDebouncedParameterEmitter(100)(
      (params) => this.triggerAnalysis(params, 'instant')
    );

    this.setupEventListeners();
    this.initializeSurrogate();
  }

  private setupEventListeners(): void {
    // Listen for parameter changes
    eventBus.onParameterChange((event) => {
      this.parameterHistory.push(event);
      if (this.parameterHistory.length > this.maxHistorySize) {
        this.parameterHistory.shift();
      }
      
      // Trigger instant surrogate analysis
      this.debouncedAnalyze(workspaceStore.getParameters());
    });

    // Listen for analysis requests
    eventBus.on('ANALYSIS_REQUEST', (event) => {
      const { parameters, fidelity } = event.data as any;
      this.triggerAnalysis(parameters, fidelity);
    });

    // Listen for cancel requests
    eventBus.on('CANCEL_ANALYSIS', () => {
      this.cancelCurrentAnalysis();
    });
  }

  private async initializeSurrogate(): Promise<void> {
    // Initialize surrogate model for instant predictions
    this.surrogateModel = new SurrogateModel();
    await this.surrogateModel.load();
  }

  /**
   * Trigger analysis with specified fidelity
   */
  async triggerAnalysis(
    parameters: Record<string, number>,
    fidelity: FidelityLevel = 'medium'
  ): Promise<AnalysisResult | null> {
    const jobId = this.generateJobId();
    
    // Check cache first
    const cacheKey = this.getCacheKey(parameters, fidelity);
    const cached = this.getCachedResult(cacheKey);
    if (cached) {
      workspaceStore.setAnalysisResult(cached);
      return cached;
    }

    // Cancel any running analysis
    if (this.currentJobId) {
      this.cancelCurrentAnalysis();
    }

    this.currentJobId = jobId;
    workspaceStore.setAnalyzing(true, fidelity);

    try {
      let result: AnalysisResult;

      switch (fidelity) {
        case 'instant':
          result = await this.runInstantAnalysis(parameters);
          break;
        case 'medium':
          result = await this.runMediumAnalysis(parameters, jobId);
          break;
        case 'high':
          result = await this.runHighFidelityAnalysis(parameters, jobId);
          break;
        default:
          throw new Error(`Unknown fidelity level: ${fidelity}`);
      }

      // Cache the result
      this.cacheResult(cacheKey, result);
      workspaceStore.setAnalysisResult(result);
      
      return result;
    } catch (error) {
      console.error('Analysis failed:', error);
      workspaceStore.setError((error as Error).message);
      return null;
    } finally {
      workspaceStore.setAnalyzing(false);
      if (this.currentJobId === jobId) {
        this.currentJobId = null;
      }
    }
  }

  /**
   * Run instant surrogate analysis (<100ms)
   */
  private async runInstantAnalysis(
    parameters: Record<string, number>
  ): Promise<AnalysisResult> {
    const startTime = performance.now();
    
    let metrics: EngineeringMetrics;
    
    if (this.surrogateModel) {
      // Use trained surrogate model
      metrics = await this.surrogateModel.predict(parameters);
    } else {
      // Fallback to simplified analytical model
      metrics = this.computeAnalyticalMetrics(parameters);
    }

    const elapsed = performance.now() - startTime;
    console.log(`[Engine] Instant analysis completed in ${elapsed.toFixed(2)}ms`);

    return {
      id: this.generateJobId(),
      timestamp: Date.now(),
      elapsed,
      fidelity: 'instant',
      status: 'completed',
      parameters,
      metrics,
      geometry: { vertexCount: 0, faceCount: 0, cellCount: 0 },
      meshQuality: this.getDefaultMeshQuality(),
      convergence: { converged: true, iterations: 0, residual: 0 }
    };
  }

  /**
   * Run medium fidelity analysis (seconds)
   */
  private async runMediumAnalysis(
    parameters: Record<string, number>,
    jobId: string
  ): Promise<AnalysisResult> {
    const startTime = performance.now();
    
    // Create cancellable job
    const job: AnalysisJob = {
      id: jobId,
      fidelity: 'medium',
      status: 'running',
      startTime,
      cancel: () => {
        analysisWS.cancelAnalysis();
      }
    };
    this.analysisJobs.set(jobId, job);

    try {
      // Try WebSocket first for streaming results
      if (analysisWS.connectionStatus) {
        const response = await analysisWS.requestAnalysis(parameters, 'medium', true);
        return this.buildResultFromResponse(response, startTime);
      }

      // Fallback to HTTP
      const result = await analysisAPI.analyze(parameters, 'medium');
      return result;
    } finally {
      job.status = 'completed';
      this.analysisJobs.delete(jobId);
    }
  }

  /**
   * Run high-fidelity analysis (background, minutes)
   */
  private async runHighFidelityAnalysis(
    parameters: Record<string, number>,
    jobId: string
  ): Promise<AnalysisResult> {
    const startTime = performance.now();
    
    const job: AnalysisJob = {
      id: jobId,
      fidelity: 'high',
      status: 'running',
      startTime,
      cancel: () => {
        analysisWS.cancelAnalysis();
      }
    };
    this.analysisJobs.set(jobId, job);

    try {
      // High-fidelity always runs in background
      if (analysisWS.connectionStatus) {
        await analysisWS.requestAnalysis(parameters, 'high', false);
        // For high-fidelity, we don't wait for completion
        // Results will be streamed via METRICS_STREAM messages
        return {
          id: jobId,
          timestamp: Date.now(),
          elapsed: 0,
          fidelity: 'high',
          status: 'running',
          parameters,
          metrics: {} as EngineeringMetrics,
          geometry: { vertexCount: 0, faceCount: 0, cellCount: 0 },
          meshQuality: this.getDefaultMeshQuality(),
          convergence: { converged: false, iterations: 0, residual: 1 }
        };
      }

      // HTTP fallback
      return await analysisAPI.analyze(parameters, 'high');
    } finally {
      job.status = 'completed';
      this.analysisJobs.delete(jobId);
    }
  }

  private buildResultFromResponse(
    response: any,
    startTime: number
  ): AnalysisResult {
    return {
      id: response.payload?.resultId || this.generateJobId(),
      timestamp: Date.now(),
      elapsed: performance.now() - startTime,
      fidelity: response.payload?.fidelity || 'medium',
      status: response.payload?.status || 'completed',
      parameters: response.payload?.parameters || {},
      metrics: response.payload?.metrics || {} as EngineeringMetrics,
      geometry: response.payload?.geometry || { vertexCount: 0, faceCount: 0, cellCount: 0 },
      meshQuality: response.payload?.meshQuality || this.getDefaultMeshQuality(),
      convergence: response.payload?.convergence || { converged: true, iterations: 1, residual: 0.001 }
    };
  }

  /**
   * Simplified analytical model for instant predictions
   */
  private computeAnalyticalMetrics(
    parameters: Record<string, number>
  ): EngineeringMetrics {
    const velocity = parameters['velocity'] || 50;
    const angleOfAttack = parameters['angleOfAttack'] || 5;
    const altitude = parameters['altitude'] || 0;
    const chordLength = parameters['chordLength'] || 1;
    const wingArea = parameters['wingArea'] || 10;
    const wingSpan = parameters['wingSpan'] || 10;
    const materialDensity = parameters['materialDensity'] || 2700;
    const thickness = parameters['thickness'] || 0.1;

    // Air density based on altitude (simplified)
    const airDensity = 1.225 * Math.exp(-altitude / 8500);
    const speedOfSound = 343;
    const machNumber = (velocity / speedOfSound);

    // Dynamic pressure
    const dynamicPressure = 0.5 * airDensity * velocity * velocity;

    // Lift coefficient (simplified thin airfoil theory)
    const cl = 2 * Math.PI * (angleOfAttack * Math.PI / 180);

    // Drag coefficient (parabolic drag polar)
    const cd0 = 0.02; // Zero-lift drag
    const k = 0.04; // Induced drag factor
    const cd = cd0 + k * cl * cl;

    // Forces
    const lift = cl * dynamicPressure * wingArea;
    const drag = cd * dynamicPressure * wingArea;
    const liftToDrag = cd > 0 ? cl / cd : 0;

    // Pressure coefficients
    const cpMin = -2.5 - 0.8 * machNumber * machNumber;
    const cpMax = 0.5 + 0.3 * machNumber * machNumber;

    // Structural metrics
    const aspectRatio = (wingSpan * wingSpan) / wingArea;
    const rootMoment = lift * chordLength * 0.25;
    const tipDeflection = (rootMoment * wingSpan * wingSpan) / 
      (3 * 70e9 * (chordLength * thickness * thickness * thickness / 12));
    const maxStress = (rootMoment * thickness / 2) / 
      (chordLength * thickness * thickness * thickness / 12);

    // Mass and inertia
    const volume = wingArea * thickness;
    const mass = volume * materialDensity;
    const iyy = (mass / 12) * (wingSpan * wingSpan + thickness * thickness);

    // Natural frequencies (simplified)
    const firstBendingFreq = Math.sqrt(3.52 * 70e9 * iyy / (mass * wingSpan * wingSpan * wingSpan)) / (2 * Math.PI);
    const firstTorsionFreq = Math.sqrt(12.5 * 26e9 * chordLength * thickness * thickness / 
      (mass * wingSpan * chordLength * chordLength)) / (2 * Math.PI);

    return {
      aerodynamic: {
        liftForce: lift,
        dragForce: drag,
        liftToDrag,
        liftCoefficient: cl,
        dragCoefficient: cd,
        pressureCoefficientMin: cpMin,
        pressureCoefficientMax: cpMax,
        machNumber,
        reynoldsNumber: airDensity * velocity * chordLength / 1.81e-5,
        separationRisk: Math.max(0, Math.min(1, (angleOfAttack - 15) / 10)),
        stallMargin: Math.max(0, 15 - Math.abs(angleOfAttack))
      },
      structural: {
        vonMisesStress: maxStress,
        displacement: tipDeflection,
        safetyFactor: 275e6 / maxStress,
        mass,
        naturalFrequencies: [firstBendingFreq, firstTorsionFreq, firstBendingFreq * 2.5],
        modeShapes: [],
        stressConcentration: 1.5,
        fatigueDamage: 0.001 * Math.abs(angleOfAttack)
      },
      thermal: {
        temperature: 288 - 0.0065 * altitude,
        heatFlux: 0.1 * dynamicPressure * velocity,
        thermalStress: 0.001 * (288 - 0.0065 * altitude) * 26e9 * 1.2e-5,
        convectionCoefficient: 100 + 0.5 * velocity,
        criticalTemperature: 350,
        temperatureMargin: 350 - (288 - 0.0065 * altitude)
      },
      acoustic: {
        spl: 120 + 10 * Math.log10(dynamicPressure / 2e-5),
        dominantFrequency: 100 + velocity * 2,
        octaveBands: [80, 90, 100, 110, 120, 130, 140],
        noiseSource: 'boundary_layer'
      },
      multidisciplinary: {
        aeroelasticCoupling: 0.1 * machNumber,
        flutterSpeed: 500 / Math.sqrt(machNumber * machNumber + 0.1),
        divergenceSpeed: 800,
        controlAuthority: 0.9,
        handlingQualities: 0.85
      }
    };
  }

  private getDefaultMeshQuality() {
    return {
      aspectRatio: { min: 1, max: 1.5, average: 1.1 },
      skewness: { min: 0, max: 0.2, average: 0.05 },
      orthogonality: { min: 0.9, max: 1, average: 0.97 },
      yPlus: { min: 0.5, max: 2, average: 1.2 }
    };
  }

  /**
   * Cancel current analysis
   */
  cancelCurrentAnalysis(): void {
    if (this.currentJobId) {
      const job = this.analysisJobs.get(this.currentJobId);
      if (job) {
        job.cancel();
        job.status = 'cancelled';
      }
      this.analysisJobs.delete(this.currentJobId);
      this.currentJobId = null;
      workspaceStore.setAnalyzing(false);
    }
  }

  /**
   * Get cached result
   */
  private getCachedResult(key: string): AnalysisResult | null {
    const entry = this.surrogateCache.get(key);
    if (entry && Date.now() - entry.timestamp < entry.ttl) {
      return entry.result as AnalysisResult;
    }
    return null;
  }

  /**
   * Cache result
   */
  private cacheResult(key: string, result: AnalysisResult): void {
    this.surrogateCache.set(key, {
      result,
      timestamp: Date.now(),
      ttl: result.fidelity === 'instant' ? 60000 : 300000,
      hitCount: 0
    });
  }

  /**
   * Generate cache key from parameters
   */
  private getCacheKey(parameters: Record<string, number>, fidelity: string): string {
    const sorted = Object.entries(parameters)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([k, v]) => `${k}:${v.toFixed(4)}`)
      .join('|');
    return `${fidelity}:${sorted}`;
  }

  private generateJobId(): string {
    return `job-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  getParameterHistory(): ParameterChangeEvent[] {
    return [...this.parameterHistory];
  }
}

// ============================================================
// Surrogate Model for Instant Predictions
// ============================================================

class SurrogateModel {
  private modelData: Map<string, any> = new Map();
  private isLoaded = false;

  async load(): Promise<void> {
    // In production, load pre-trained model weights
    // For now, use analytical model
    this.isLoaded = true;
  }

  async predict(parameters: Record<string, number>): Promise<EngineeringMetrics> {
    if (!this.isLoaded) {
      throw new Error('Surrogate model not loaded');
    }

    // Use neural network interpolation or fallback to analytical
    return this.interpolateFromTrainingData(parameters);
  }

  private interpolateFromTrainingData(
    parameters: Record<string, number>
  ): EngineeringMetrics {
    // Simplified interpolation - in production would use actual trained model
    const engine = new ProgressiveAnalysisEngine();
    const tempStore = workspaceStore as any;
    
    // Temporarily set parameters and compute
    const originalParams = tempStore.getState().parameters;
    tempStore.setParameters(parameters);
    
    const result = engine['computeAnalyticalMetrics'](parameters);
    
    // Restore original parameters
    tempStore.setParameters(originalParams);
    
    return result;
  }
}

// Singleton instance
export const analysisEngine = new ProgressiveAnalysisEngine();
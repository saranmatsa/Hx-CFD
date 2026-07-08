/**
 * Core type definitions for the Interactive Engineering Analysis Workspace
 * This file defines all the types used across the system for type safety
 */

// ============================================================
// Parameter Types
// ============================================================

export interface ParameterBase {
  id: string;
  name: string;
  category: ParameterCategory;
  value: number;
  unit: string;
  min: number;
  max: number;
  step: number;
  description: string;
  isLive: boolean;
  lastModified: number;
}

export type ParameterCategory = 
  | 'geometry'
  | 'aerodynamics'
  | 'materials'
  | 'boundary_conditions'
  | 'mesh'
  | 'solver'
  | 'structural';

export interface GeometryParameters extends ParameterBase {
  category: 'geometry';
  subType: 'wing' | 'fuselage' | 'airfoil' | 'general';
}

export interface AerodynamicParameters extends ParameterBase {
  category: 'aerodynamics';
  subType: 'flow' | 'control';
}

export interface MaterialParameters extends ParameterBase {
  category: 'materials';
  subType: 'structural' | 'coating';
}

// ============================================================
// Analysis Result Types
// ============================================================

export interface AnalysisResult {
  id: string;
  timestamp: number;
  parameters: Record<string, number>;
  metrics: EngineeringMetrics;
  fidelity: FidelityLevel;
  status: AnalysisStatus;
  progress: number;
  duration: number;
  cacheHit: boolean;
}

export type FidelityLevel = 'instant' | 'medium' | 'high';

export type AnalysisStatus = 
  | 'pending'
  | 'running'
  | 'streaming'
  | 'completed'
  | 'error'
  | 'cancelled';

export interface EngineeringMetrics {
  // Aerodynamic metrics
  lift: MetricValue;
  drag: MetricValue;
  liftToDragRatio: MetricValue;
  pressureCoefficient: ScalarField;
  velocityDistribution: VectorField;
  streamlines: StreamlineData;
  vorticity: ScalarField;
  turbulenceIntensity: ScalarField;
  
  // Dimensionless numbers
  reynoldsNumber: MetricValue;
  machNumber: MetricValue;
  
  // Structural metrics
  stress: TensorField;
  strain: TensorField;
  displacement: VectorField;
  factorOfSafety: ScalarField;
  
  // Mass properties
  mass: MetricValue;
  centerOfGravity: Vector3D;
  surfaceArea: MetricValue;
  volume: MetricValue;
  
  // Mesh metrics
  meshQuality: MeshQualityMetrics;
  cellCount: number;
  
  // Solver metrics
  convergence: ConvergenceData;
  residuals: ResidualHistory;
}

export interface MetricValue {
  value: number;
  unit: string;
  confidence: number;
  isEstimate: boolean;
  timestamp: number;
}

export interface ScalarField {
  data: Float32Array;
  min: number;
  max: number;
  unit: string;
  confidence: number;
}

export interface VectorField {
  data: Float32Array; // Interleaved x, y, z components
  min: number;
  max: number;
  unit: string;
  confidence: number;
}

export interface TensorField {
  data: Float32Array; // Interleaved tensor components
  components: string[];
  unit: string;
  confidence: number;
}

export interface Vector3D {
  x: number;
  y: number;
  z: number;
  unit: string;
}

export interface StreamlineData {
  lines: Streamline[];
  maxVelocity: number;
  minVelocity: number;
}

export interface Streamline {
  points: Vector3D[];
  velocities: number[];
  pressure: number[];
}

export interface MeshQualityMetrics {
  minQuality: number;
  maxQuality: number;
  averageQuality: number;
  aspectRatio: number;
  skewness: number;
  orthogonality: number;
}

export interface ConvergenceData {
  converged: boolean;
  iterations: number;
  residual: number;
  time: number;
}

export interface ResidualHistory {
  iterations: number[];
  residuals: number[];
  energy: number[];
  continuity: number[];
  momentum: number[];
}

// ============================================================
// System Resource Types
// ============================================================

export interface SystemResources {
  cpu: ResourceMetric;
  gpu: ResourceMetric;
  memory: ResourceMetric;
  estimatedSolveTime: number;
}

export interface ResourceMetric {
  usage: number;
  available: number;
  unit: string;
}

// ============================================================
// Event Types
// ============================================================

export interface ParameterChangeEvent {
  type: 'PARAMETER_CHANGE';
  parameterId: string;
  oldValue: number;
  newValue: number;
  timestamp: number;
  source: 'user' | 'optimization' | 'import';
}

export interface AnalysisUpdateEvent {
  type: 'ANALYSIS_UPDATE';
  result: Partial<AnalysisResult>;
  isPartial: boolean;
}

export interface MetricsStreamEvent {
  type: 'METRICS_STREAM';
  metrics: Partial<EngineeringMetrics>;
  timestamp: number;
}

export interface ConvergenceEvent {
  type: 'CONVERGENCE';
  data: ConvergenceData;
}

export type WorkspaceEvent = 
  | ParameterChangeEvent 
  | AnalysisUpdateEvent 
  | MetricsStreamEvent 
  | ConvergenceEvent;

// ============================================================
// State Types
// ============================================================

export interface WorkspaceState {
  parameters: Record<string, ParameterBase>;
  currentResult: AnalysisResult | null;
  resultHistory: AnalysisResult[];
  systemResources: SystemResources;
  isAnalyzing: boolean;
  fidelityLevel: FidelityLevel;
  cacheSize: number;
  undoStack: WorkspaceState[];
  redoStack: WorkspaceState[];
}

export interface ViewState {
  activeView: '3d' | 'cfd' | 'structural' | 'dashboard';
  cameraPosition: Vector3D;
  cameraTarget: Vector3D;
  showStreamlines: boolean;
  showPressure: boolean;
  showDisplacement: boolean;
  colormap: string;
  isPlaying: boolean;
  playbackSpeed: number;
}

// ============================================================
// WebSocket Message Types
// ============================================================

export interface WSMessage {
  type: string;
  payload: unknown;
  timestamp: number;
  correlationId?: string;
}

export interface WSAnalysisRequest {
  type: 'ANALYSIS_REQUEST';
  payload: {
    parameters: Record<string, number>;
    fidelity: FidelityLevel;
    incremental: boolean;
  };
}

export interface WSAnalysisResponse {
  type: 'ANALYSIS_RESPONSE';
  payload: {
    resultId: string;
    status: AnalysisStatus;
    progress: number;
    metrics?: Partial<EngineeringMetrics>;
  };
}

export interface WSMetricsStream {
  type: 'METRICS_STREAM';
  payload: {
    metrics: Partial<EngineeringMetrics>;
    isFinal: boolean;
  };
}

// ============================================================
// Solver Types
// ============================================================

export interface SolverConfig {
  type: 'cfd' | 'structural' | 'thermal' | 'coupled';
  maxIterations: number;
  convergenceTolerance: number;
  relaxationFactor: number;
  parallelEnabled: boolean;
  gpuAccelerated: boolean;
}

export interface SolverResult {
  converged: boolean;
  iterations: number;
  finalResidual: number;
  solveTime: number;
  metrics: Partial<EngineeringMetrics>;
}

// ============================================================
// Cache Types
// ============================================================

export interface CacheEntry {
  key: string;
  parameters: Record<string, number>;
  result: AnalysisResult;
  timestamp: number;
  accessCount: number;
  size: number;
}

export interface CacheConfig {
  maxSize: number;
  maxAge: number;
  enableCompression: boolean;
}

// ============================================================
// Plugin Types
// ============================================================

export interface SolverPlugin {
  id: string;
  name: string;
  type: 'cfd' | 'structural' | 'thermal' | 'optimization';
  execute: (params: Record<string, number>, config: SolverConfig) => Promise<SolverResult>;
  getMetadata: () => PluginMetadata;
}

export interface PluginMetadata {
  name: string;
  version: string;
  author: string;
  description: string;
  inputs: ParameterDefinition[];
  outputs: string[];
}

// ============================================================
// Utility Types
// ============================================================

export interface ParameterDefinition {
  name: string;
  type: 'number' | 'string' | 'boolean' | 'array';
  default: unknown;
  min?: number;
  max?: number;
  unit?: string;
}

export interface HistoryEntry {
  timestamp: number;
  action: string;
  parameters: Record<string, number>;
  result?: AnalysisResult;
}

export interface OptimizationConfig {
  objective: string;
  constraints: Record<string, { min?: number; max?: number }>;
  algorithm: 'genetic' | 'gradient' | 'bayesian';
  maxEvaluations: number;
  tolerance: number;
}
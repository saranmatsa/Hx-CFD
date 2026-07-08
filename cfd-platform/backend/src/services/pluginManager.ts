/**
 * Plugin Architecture for Extensible Solvers
 * Allows dynamic loading and execution of custom analysis plugins
 */

import { EventEmitter } from 'events';

export interface SolverPlugin {
  id: string;
  name: string;
  version: string;
  description: string;
  author?: string;
  category: 'cfd' | 'structural' | 'thermal' | 'electromagnetic' | 'custom';
  capabilities: string[];
  parameters: ParameterDefinition[];
  execute(request: SolverRequest): Promise<SolverResult>;
  validate?(parameters: Record<string, number>): ValidationResult;
  dispose?(): void;
}

export interface ParameterDefinition {
  name: string;
  type: 'number' | 'string' | 'boolean' | 'select' | 'range';
  label: string;
  default?: any;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  options?: { value: any; label: string }[];
  description?: string;
  required?: boolean;
  visible?: (params: Record<string, number>) => boolean;
}

export interface SolverRequest {
  id: string;
  pluginId: string;
  parameters: Record<string, number>;
  geometry?: GeometryData;
  options?: Record<string, any>;
}

export interface SolverResult {
  id: string;
  success: boolean;
  metrics?: Record<string, number>;
  fields?: FieldData[];
  convergenceHistory?: ConvergencePoint[];
  meshQuality?: MeshQualityData;
  warnings?: string[];
  errors?: string[];
  computationTime: number;
  metadata?: Record<string, any>;
}

export interface GeometryData {
  type: 'box' | 'sphere' | 'cylinder' | 'airfoil' | 'stl' | 'brep';
  dimensions?: {
    width?: number;
    height?: number;
    depth?: number;
    radius?: number;
    length?: number;
  };
  vertices?: number[];
  faces?: number[];
  normals?: number[];
  stlData?: string;
  boundingBox?: { min: number[]; max: number[] };
}

export interface FieldData {
  name: string;
  type: 'scalar' | 'vector' | 'tensor';
  location: 'node' | 'cell' | 'face';
  values: number[] | number[][];
  units?: string;
  range?: { min: number; max: number };
}

export interface ConvergencePoint {
  iteration: number;
  residual: number;
  time?: number;
  value?: number;
}

export interface MeshQualityData {
  elementCount: number;
  vertexCount: number;
  elementType: string;
  aspectRatio?: { min: number; max: number; avg: number };
  skewness?: { min: number; max: number; avg: number };
  orthogonality?: { min: number; max: number; avg: number };
  quality: 'excellent' | 'good' | 'fair' | 'poor';
}

export interface ValidationResult {
  valid: boolean;
  errors: { parameter: string; message: string }[];
  warnings: { parameter: string; message: string }[];
}

export interface PluginManifest {
  id: string;
  name: string;
  version: string;
  main: string;
  dependencies?: Record<string, string>;
  permissions?: string[];
}

export type PluginStatus = 'loaded' | 'active' | 'error' | 'disabled';

export interface PluginInfo {
  id: string;
  name: string;
  version: string;
  status: PluginStatus;
  capabilities: string[];
  loadTime: number;
  executionCount: number;
  lastExecution?: number;
  error?: string;
}

export class PluginManager extends EventEmitter {
  private plugins: Map<string, SolverPlugin> = new Map();
  private pluginInfo: Map<string, PluginInfo> = new Map();
  private executionHistory: Map<string, SolverResult[]> = new Map();
  
  private readonly MAX_HISTORY_PER_PLUGIN = 100;

  constructor() {
    super();
    this.registerBuiltInPlugins();
  }

  private registerBuiltInPlugins() {
    // Register a basic surrogate model plugin
    this.register({
      id: 'surrogate',
      name: 'Surrogate Model',
      version: '1.0.0',
      description: 'Fast surrogate model for preliminary analysis',
      category: 'cfd',
      capabilities: ['instant-analysis', 'parameter-study', 'optimization'],
      parameters: [
        {
          name: 'angleOfAttack',
          type: 'range',
          label: 'Angle of Attack',
          default: 0,
          min: -15,
          max: 25,
          step: 0.5,
          unit: 'deg'
        },
        {
          name: 'reynoldsNumber',
          type: 'number',
          label: 'Reynolds Number',
          default: 1e6,
          min: 1e4,
          max: 1e8,
          unit: '-'
        },
        {
          name: 'machNumber',
          type: 'range',
          label: 'Mach Number',
          default: 0.3,
          min: 0,
          max: 0.9,
          step: 0.05
        }
      ],
      execute: async (request) => {
        const startTime = Date.now();
        const { angleOfAttack = 0, reynoldsNumber = 1e6, machNumber = 0.3 } = request.parameters;

        // Simplified lift coefficient: CL = 2π * α
        const alpha = angleOfAttack * Math.PI / 180;
        const efficiency = 0.9;
        const lift = 2 * Math.PI * alpha * efficiency * (1 + 0.01 * Math.log10(reynoldsNumber / 1e6));

        // Drag coefficient: CD = CD₀ + CL²/(πeAR)
        const cd0 = 0.02;
        const ar = 10;
        const drag = cd0 + (lift * lift) / (Math.PI * efficiency * ar);

        // Stall modeling
        const stallAngle = 15;
        const maxCL = 2 * Math.PI * stallAngle * Math.PI / 180 * efficiency;
        const actualLift = Math.abs(angleOfAttack) > stallAngle 
          ? maxCL * Math.sign(angleOfAttack) * 0.8 
          : lift;

        return {
          id: request.id,
          success: true,
          metrics: {
            lift: actualLift,
            drag,
            moment: -0.1 + 0.01 * angleOfAttack,
            liftToDrag: drag > 0.001 ? actualLift / drag : 0,
            maxLiftCoefficient: maxCL,
            stallAngle
          },
          convergenceHistory: [
            { iteration: 1, residual: 0.1 },
            { iteration: 2, residual: 0.01 },
            { iteration: 3, residual: 0.001 }
          ],
          computationTime: Date.now() - startTime,
          metadata: {
            plugin: 'surrogate',
            fidelity: 'instant'
          }
        };
      }
    });

    // Register a panel method plugin
    this.register({
      id: 'panel-method',
      name: 'Panel Method',
      version: '1.0.0',
      description: 'Classical panel method for potential flow analysis',
      category: 'cfd',
      capabilities: ['medium-fidelity', 'pressure-distribution', 'lift-distribution'],
      parameters: [
        {
          name: 'angleOfAttack',
          type: 'range',
          label: 'Angle of Attack',
          default: 5,
          min: -20,
          max: 30,
          step: 0.1,
          unit: 'deg'
        },
        {
          name: 'numPanels',
          type: 'select',
          label: 'Number of Panels',
          default: 100,
          options: [
            { value: 50, label: '50 (Fast)' },
            { value: 100, label: '100 (Balanced)' },
            { value: 200, label: '200 (Accurate)' },
            { value: 500, label: '500 (High)' }
          ]
        },
        {
          name: 'wakeLength',
          type: 'range',
          label: 'Wake Length',
          default: 5,
          min: 1,
          max: 20,
          step: 0.5,
          unit: 'chords'
        }
      ],
      execute: async (request) => {
        const startTime = Date.now();
        const { angleOfAttack = 5, numPanels = 100 } = request.parameters;

        // Simulate panel method computation
        await this.simulateComputation(500);

        const alpha = angleOfAttack * Math.PI / 180;
        const lift = 2 * Math.PI * alpha * 0.95;

        // Generate pressure distribution
        const pressures: number[] = [];
        for (let i = 0; i < numPanels; i++) {
          const x = i / numPanels;
          const cp = -2 * Math.sin(alpha) * Math.cos(2 * Math.PI * x);
          pressures.push(cp);
        }

        return {
          id: request.id,
          success: true,
          metrics: {
            lift,
            drag: 0.025 + lift * lift / (2 * Math.PI * 10),
            moment: -0.08,
            liftToDrag: lift / (0.025 + lift * lift / (2 * Math.PI * 10))
          },
          fields: [
            {
              name: 'pressure',
              type: 'scalar',
              location: 'face',
              values: pressures,
              units: 'Pa',
              range: { min: Math.min(...pressures), max: Math.max(...pressures) }
            }
          ],
          convergenceHistory: [
            { iteration: 1, residual: 0.5 },
            { iteration: 2, residual: 0.1 },
            { iteration: 3, residual: 0.02 },
            { iteration: 4, residual: 0.005 }
          ],
          computationTime: Date.now() - startTime,
          metadata: {
            plugin: 'panel-method',
            fidelity: 'medium',
            numPanels
          }
        };
      }
    });

    // Register a thermal analysis plugin
    this.register({
      id: 'thermal-solver',
      name: 'Thermal Solver',
      version: '1.0.0',
      description: 'Heat transfer analysis with conduction and convection',
      category: 'thermal',
      capabilities: ['steady-state', 'transient', 'conduction', 'convection'],
      parameters: [
        {
          name: 'thermalConductivity',
          type: 'number',
          label: 'Thermal Conductivity',
          default: 200,
          min: 1,
          max: 1000,
          unit: 'W/(m·K)'
        },
        {
          name: 'heatFlux',
          type: 'number',
          label: 'Heat Flux',
          default: 1000,
          min: 0,
          max: 100000,
          unit: 'W/m²'
        },
        {
          name: 'ambientTemperature',
          type: 'number',
          label: 'Ambient Temperature',
          default: 293,
          min: 100,
          max: 1000,
          unit: 'K'
        },
        {
          name: 'convectionCoefficient',
          type: 'number',
          label: 'Convection Coefficient',
          default: 10,
          min: 0,
          max: 1000,
          unit: 'W/(m²·K)'
        }
      ],
      execute: async (request) => {
        const startTime = Date.now();
        const { 
          thermalConductivity = 200,
          heatFlux = 1000,
          ambientTemperature = 293,
          convectionCoefficient = 10
        } = request.parameters;

        await this.simulateComputation(300);

        // Simplified thermal calculation
        const temperatureRise = heatFlux / (convectionCoefficient + thermalConductivity / 0.01);
        const maxTemperature = ambientTemperature + temperatureRise;

        return {
          id: request.id,
          success: true,
          metrics: {
            temperature: maxTemperature,
            heatFlux,
            temperatureRise,
            convectionCoefficient
          },
          computationTime: Date.now() - startTime,
          metadata: {
            plugin: 'thermal-solver',
            fidelity: 'medium'
          }
        };
      }
    });
  }

  private async simulateComputation(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  public register(plugin: SolverPlugin): void {
    if (this.plugins.has(plugin.id)) {
      throw new Error(`Plugin ${plugin.id} is already registered`);
    }

    this.plugins.set(plugin.id, plugin);
    this.pluginInfo.set(plugin.id, {
      id: plugin.id,
      name: plugin.name,
      version: plugin.version,
      status: 'loaded',
      capabilities: plugin.capabilities,
      loadTime: Date.now(),
      executionCount: 0
    });

    this.emit('pluginLoaded', { id: plugin.id, name: plugin.name });
  }

  public unregister(pluginId: string): boolean {
    const plugin = this.plugins.get(pluginId);
    if (!plugin) return false;

    if (plugin.dispose) {
      plugin.dispose();
    }

    this.plugins.delete(pluginId);
    this.pluginInfo.delete(pluginId);
    this.executionHistory.delete(pluginId);

    this.emit('pluginUnloaded', { id: pluginId });
    return true;
  }

  public get(pluginId: string): SolverPlugin | undefined {
    return this.plugins.get(pluginId);
  }

  public getAll(): SolverPlugin[] {
    return Array.from(this.plugins.values());
  }

  public getByCategory(category: SolverPlugin['category']): SolverPlugin[] {
    return this.getAll().filter(p => p.category === category);
  }

  public getInfo(pluginId: string): PluginInfo | undefined {
    return this.pluginInfo.get(pluginId);
  }

  public getAllInfo(): PluginInfo[] {
    return Array.from(this.pluginInfo.values());
  }

  public async execute(request: SolverRequest): Promise<SolverResult> {
    const plugin = this.plugins.get(request.pluginId);
    if (!plugin) {
      throw new Error(`Plugin ${request.pluginId} not found`);
    }

    // Validate parameters
    if (plugin.validate) {
      const validation = plugin.validate(request.parameters);
      if (!validation.valid) {
        return {
          id: request.id,
          success: false,
          errors: validation.errors.map(e => e.message),
          computationTime: 0
        };
      }
    }

    // Update execution count
    const info = this.pluginInfo.get(request.pluginId);
    if (info) {
      info.executionCount++;
      info.lastExecution = Date.now();
      info.status = 'active';
    }

    try {
      const result = await plugin.execute(request);

      // Store in history
      this.addToHistory(request.pluginId, result);

      this.emit('executionComplete', { 
        pluginId: request.pluginId, 
        result 
      });

      return result;
    } catch (error) {
      const errorResult: SolverResult = {
        id: request.id,
        success: false,
        errors: [error instanceof Error ? error.message : 'Unknown error'],
        computationTime: 0
      };

      if (info) {
        info.status = 'error';
        info.error = error instanceof Error ? error.message : 'Unknown error';
      }

      this.emit('executionError', { 
        pluginId: request.pluginId, 
        error 
      });

      return errorResult;
    } finally {
      if (info) {
        info.status = 'loaded';
      }
    }
  }

  private addToHistory(pluginId: string, result: SolverResult): void {
    let history = this.executionHistory.get(pluginId);
    if (!history) {
      history = [];
      this.executionHistory.set(pluginId, history);
    }

    history.push(result);

    // Trim history
    while (history.length > this.MAX_HISTORY_PER_PLUGIN) {
      history.shift();
    }
  }

  public getHistory(pluginId: string): SolverResult[] {
    return this.executionHistory.get(pluginId) || [];
  }

  public clearHistory(pluginId?: string): void {
    if (pluginId) {
      this.executionHistory.delete(pluginId);
    } else {
      this.executionHistory.clear();
    }
  }

  public enable(pluginId: string): boolean {
    const info = this.pluginInfo.get(pluginId);
    if (info && info.status === 'disabled') {
      info.status = 'loaded';
      this.emit('pluginEnabled', { id: pluginId });
      return true;
    }
    return false;
  }

  public disable(pluginId: string): boolean {
    const info = this.pluginInfo.get(pluginId);
    if (info && info.status !== 'error') {
      info.status = 'disabled';
      this.emit('pluginDisabled', { id: pluginId });
      return true;
    }
    return false;
  }

  public search(query: string): SolverPlugin[] {
    const lowerQuery = query.toLowerCase();
    return this.getAll().filter(p => 
      p.name.toLowerCase().includes(lowerQuery) ||
      p.description.toLowerCase().includes(lowerQuery) ||
      p.capabilities.some(c => c.toLowerCase().includes(lowerQuery))
    );
  }

  public dispose(): void {
    for (const plugin of this.plugins.values()) {
      if (plugin.dispose) {
        plugin.dispose();
      }
    }
    this.plugins.clear();
    this.pluginInfo.clear();
    this.executionHistory.clear();
    this.removeAllListeners();
  }
}

// Singleton instance
let pluginManagerInstance: PluginManager | null = null;

export function getPluginManager(): PluginManager {
  if (!pluginManagerInstance) {
    pluginManagerInstance = new PluginManager();
  }
  return pluginManagerInstance;
}

// Plugin loader for dynamic loading
export class PluginLoader {
  private loadedPlugins: Map<string, any> = new Map();

  public async loadFromURL(url: string): Promise<SolverPlugin> {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to load plugin from ${url}`);
    }

    const module = await response.json();
    return module as SolverPlugin;
  }

  public async loadFromFile(file: File): Promise<SolverPlugin> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const module = JSON.parse(e.target?.result as string);
          resolve(module as SolverPlugin);
        } catch (error) {
          reject(new Error('Invalid plugin format'));
        }
      };
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  }
}
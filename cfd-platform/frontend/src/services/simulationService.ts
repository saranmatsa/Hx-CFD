import { api } from './api'

export interface Simulation {
  id: string
  name: string
  project_id: string
  mesh_id?: string
  solver: string
  status: string
  progress?: number
  results_path?: string
  created_at: string
  updated_at: string
}

export interface CreateSimulationRequest {
  name: string
  project_id: string
  mesh_id?: string
  solver: string
  config?: Record<string, unknown>
}

export const simulationService = {
  list: (projectId: string) =>
    api.get<Simulation[]>(`/simulations/project/${projectId}`),
  
  get: (id: string) => api.get<Simulation>(`/simulations/${id}`),
  
  create: (data: CreateSimulationRequest) =>
    api.post<Simulation>('/simulations', data),
  
  start: (id: string) =>
    api.post<{ message: string }>(`/simulations/${id}/start`),
  
  stop: (id: string) =>
    api.post<{ message: string }>(`/simulations/${id}/stop`),
  
  delete: (id: string) => api.delete(`/simulations/${id}`),
}

// Factory function for creating simulation state manager (replaces useSimulation hook)
export function createSimulationManager() {
  return new SimulationStateManager();
}

export class SimulationStateManager {
  private _simulations: Simulation[] = [];
  private _isLoading = false;
  private _error: Error | null = null;
  private _listeners: Set<() => void> = new Set();

  get simulations() { return this._simulations; }
  get isLoading() { return this._isLoading; }
  get error() { return this._error; }

  subscribe(listener: () => void): () => void {
    this._listeners.add(listener);
    return () => this._listeners.delete(listener);
  }

  private notify() {
    this._listeners.forEach(l => l());
  }

  async loadSimulations(projectId: string) {
    this._isLoading = true;
    this._error = null;
    this.notify();

    try {
      this._simulations = await simulationService.list(projectId);
    } catch (e) {
      this._error = e as Error;
    } finally {
      this._isLoading = false;
      this.notify();
    }
  }

  async createSimulation(data: CreateSimulationRequest) {
    try {
      const simulation = await simulationService.create(data);
      this._simulations = [...this._simulations, simulation];
      this.notify();
      return simulation;
    } catch (e) {
      this._error = e as Error;
      this.notify();
      throw e;
    }
  }

  async startSimulation(id: string) {
    try {
      await simulationService.start(id);
      this._simulations = this._simulations.map(s => 
        s.id === id ? { ...s, status: 'running' } : s
      );
      this.notify();
    } catch (e) {
      this._error = e as Error;
      this.notify();
    }
  }

  async stopSimulation(id: string) {
    try {
      await simulationService.stop(id);
      this._simulations = this._simulations.map(s => 
        s.id === id ? { ...s, status: 'stopped' } : s
      );
      this.notify();
    } catch (e) {
      this._error = e as Error;
      this.notify();
    }
  }

  async deleteSimulation(id: string) {
    try {
      await simulationService.delete(id);
      this._simulations = this._simulations.filter(s => s.id !== id);
      this.notify();
    } catch (e) {
      this._error = e as Error;
      this.notify();
    }
  }
}
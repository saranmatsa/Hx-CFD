import { api } from './api'

export interface Mesh {
  id: string
  name: string
  project_id: string
  status: string
  num_cells?: number
  num_points?: number
  file_path?: string
  created_at: string
  updated_at: string
}

export interface CreateMeshRequest {
  name: string
  project_id: string
  config?: {
    element_size?: number
    growth_rate?: number
    num_boundary_layers?: number
  }
}

export const meshService = {
  list: (projectId: string) =>
    api.get<Mesh[]>(`/meshes/project/${projectId}`),
  
  get: (id: string) => api.get<Mesh>(`/meshes/${id}`),
  
  create: (data: CreateMeshRequest) =>
    api.post<Mesh>('/meshes', data),
  
  delete: (id: string) => api.delete(`/meshes/${id}`),
}

// Factory function for creating mesh state manager (replaces useMesh hook)
export function createMeshManager() {
  return new MeshStateManager();
}

export class MeshStateManager {
  private _meshes: Mesh[] = [];
  private _isLoading = false;
  private _error: Error | null = null;
  private _listeners: Set<() => void> = new Set();

  get meshes() { return this._meshes; }
  get isLoading() { return this._isLoading; }
  get error() { return this._error; }

  subscribe(listener: () => void): () => void {
    this._listeners.add(listener);
    return () => this._listeners.delete(listener);
  }

  private notify() {
    this._listeners.forEach(l => l());
  }

  async loadMeshes(projectId: string) {
    this._isLoading = true;
    this._error = null;
    this.notify();

    try {
      this._meshes = await meshService.list(projectId);
    } catch (e) {
      this._error = e as Error;
    } finally {
      this._isLoading = false;
      this.notify();
    }
  }

  async createMesh(data: CreateMeshRequest) {
    try {
      const mesh = await meshService.create(data);
      this._meshes = [...this._meshes, mesh];
      this.notify();
      return mesh;
    } catch (e) {
      this._error = e as Error;
      this.notify();
      throw e;
    }
  }

  async deleteMesh(meshId: string) {
    try {
      await meshService.delete(meshId);
      this._meshes = this._meshes.filter(m => m.id !== meshId);
      this.notify();
    } catch (e) {
      this._error = e as Error;
      this.notify();
    }
  }
}
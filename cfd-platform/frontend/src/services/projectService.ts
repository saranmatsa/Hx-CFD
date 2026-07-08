import { api } from './api'

export interface Project {
  id: string
  name: string
  description?: string
  status: string
  owner_id: string
  created_at: string
  updated_at: string
}

export interface CreateProjectRequest {
  name: string
  description?: string
}

export const projectService = {
  list: (params?: { page?: number; page_size?: number }) =>
    api.get<{ projects: Project[]; total: number }>('/projects', { params }),
  
  get: (id: string) => api.get<Project>(`/projects/${id}`),
  
  create: (data: CreateProjectRequest) =>
    api.post<Project>('/projects', data),
  
  update: (id: string, data: Partial<CreateProjectRequest>) =>
    api.patch<Project>(`/projects/${id}`, data),
  
  delete: (id: string) => api.delete(`/projects/${id}`),
}

// Factory function for creating project state manager (replaces useProjects hook)
export function createProjectManager() {
  return new ProjectStateManager();
}

export class ProjectStateManager {
  private _projects: Project[] = [];
  private _currentProject: Project | null = null;
  private _isLoading = false;
  private _error: Error | null = null;
  private _page = 1;
  private _total = 0;
  private _listeners: Set<() => void> = new Set();

  get projects() { return this._projects; }
  get currentProject() { return this._currentProject; }
  get isLoading() { return this._isLoading; }
  get error() { return this._error; }
  get page() { return this._page; }
  get total() { return this._total; }

  subscribe(listener: () => void): () => void {
    this._listeners.add(listener);
    return () => this._listeners.delete(listener);
  }

  private notify() {
    this._listeners.forEach(l => l());
  }

  async loadProjects(page = 1) {
    this._isLoading = true;
    this._error = null;
    this._page = page;
    this.notify();

    try {
      const response = await projectService.list({ page, page_size: 20 });
      this._projects = response.projects;
      this._total = response.total;
    } catch (e) {
      this._error = e as Error;
    } finally {
      this._isLoading = false;
      this.notify();
    }
  }

  async loadProject(id: string) {
    this._isLoading = true;
    this._error = null;
    this.notify();

    try {
      this._currentProject = await projectService.get(id);
    } catch (e) {
      this._error = e as Error;
    } finally {
      this._isLoading = false;
      this.notify();
    }
  }

  async createProject(data: CreateProjectRequest) {
    try {
      const project = await projectService.create(data);
      this._projects = [project, ...this._projects];
      this._currentProject = project;
      this.notify();
      return project;
    } catch (e) {
      this._error = e as Error;
      this.notify();
      throw e;
    }
  }

  async updateProject(id: string, data: Partial<CreateProjectRequest>) {
    try {
      const updated = await projectService.update(id, data);
      this._projects = this._projects.map(p => p.id === id ? updated : p);
      if (this._currentProject?.id === id) {
        this._currentProject = updated;
      }
      this.notify();
    } catch (e) {
      this._error = e as Error;
      this.notify();
    }
  }

  async deleteProject(id: string) {
    try {
      await projectService.delete(id);
      this._projects = this._projects.filter(p => p.id !== id);
      if (this._currentProject?.id === id) {
        this._currentProject = null;
      }
      this.notify();
    } catch (e) {
      this._error = e as Error;
      this.notify();
    }
  }
}
/**
 * Dashboard Page Component
 * Project listing and management
 */

import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { projectService, Project, CreateProjectRequest } from '../services/projectService';
import { pipelineService } from '../services/pipelineService';

@customElement('dashboard-page')
export class DashboardPage extends LitElement {
  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      background: #f3f4f6;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .container {
      max-width: 1280px;
      margin: 0 auto;
      padding: 24px;
    }

    /* Running Pipelines Banner */
    .pipelines-banner {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 12px;
      padding: 16px 20px;
      margin-bottom: 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .pipelines-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .pipelines-icon {
      width: 40px;
      height: 40px;
      background: #dbeafe;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .pipelines-icon svg {
      width: 20px;
      height: 20px;
      fill: #2563eb;
      animation: spin 1.5s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .pipelines-title {
      font-weight: 600;
      color: #1e40af;
    }

    .pipelines-subtitle {
      font-size: 14px;
      color: #3b82f6;
    }

    .view-pipeline-btn {
      padding: 8px 16px;
      background: #2563eb;
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      transition: background 0.15s ease;
    }

    .view-pipeline-btn:hover {
      background: #1d4ed8;
    }

    /* Header */
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }

    .header h1 {
      font-size: 28px;
      font-weight: 700;
      color: #111827;
    }

    .new-project-btn {
      padding: 10px 20px;
      background: #2563eb;
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s ease;
    }

    .new-project-btn:hover {
      background: #1d4ed8;
    }

    /* Projects Grid */
    .projects-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px;
    }

    .project-card {
      background: white;
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
      transition: box-shadow 0.2s ease, transform 0.2s ease;
      text-decoration: none;
      color: inherit;
      display: block;
    }

    .project-card:hover {
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      transform: translateY(-2px);
    }

    .project-name {
      font-size: 18px;
      font-weight: 600;
      color: #111827;
      margin-bottom: 8px;
    }

    .project-description {
      font-size: 14px;
      color: #6b7280;
      margin-bottom: 16px;
      line-height: 1.5;
    }

    .project-meta {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .status-badge {
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
    }

    .status-badge.active {
      background: #dcfce7;
      color: #166534;
    }

    .status-badge.inactive {
      background: #f3f4f6;
      color: #374151;
    }

    .project-date {
      font-size: 12px;
      color: #9ca3af;
    }

    /* Empty State */
    .empty-state {
      text-align: center;
      padding: 60px 20px;
      background: white;
      border-radius: 12px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }

    .empty-state svg {
      width: 64px;
      height: 64px;
      fill: #d1d5db;
      margin: 0 auto 16px;
    }

    .empty-state h3 {
      font-size: 18px;
      font-weight: 600;
      color: #111827;
      margin-bottom: 8px;
    }

    .empty-state p {
      font-size: 14px;
      color: #6b7280;
      margin-bottom: 24px;
    }

    .empty-state-btn {
      display: inline-flex;
      align-items: center;
      padding: 10px 20px;
      background: #2563eb;
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s ease;
    }

    .empty-state-btn:hover {
      background: #1d4ed8;
    }

    /* Loading */
    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 200px;
      color: #6b7280;
    }

    .spinner {
      width: 32px;
      height: 32px;
      border: 3px solid #e5e7eb;
      border-top-color: #2563eb;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin-right: 12px;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    /* Modal */
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .modal {
      background: white;
      border-radius: 12px;
      padding: 24px;
      width: 100%;
      max-width: 480px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    }

    .modal h2 {
      font-size: 20px;
      font-weight: 600;
      color: #111827;
      margin-bottom: 20px;
    }

    .modal-form-group {
      margin-bottom: 16px;
    }

    .modal-form-group label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      color: #374151;
      margin-bottom: 6px;
    }

    .modal-form-group input,
    .modal-form-group textarea {
      width: 100%;
      padding: 10px 14px;
      border: 1px solid #d1d5db;
      border-radius: 8px;
      font-size: 14px;
      box-sizing: border-box;
    }

    .modal-form-group textarea {
      resize: vertical;
      min-height: 80px;
    }

    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 24px;
    }

    .modal-cancel-btn {
      padding: 10px 20px;
      background: #f3f4f6;
      color: #374151;
      border: none;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
    }

    .modal-submit-btn {
      padding: 10px 20px;
      background: #2563eb;
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
    }

    .modal-submit-btn:hover {
      background: #1d4ed8;
    }
  `;

  @state() private projects: Project[] = [];
  @state() private pipelines: any[] = [];
  @state() private isLoading = true;
  @state() private showCreateModal = false;
  @state() private newProjectName = '';
  @state() private newProjectDescription = '';

  private pollInterval: number | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.loadData();
    // Poll for running pipelines every 5 seconds
    this.pollInterval = window.setInterval(() => this.loadPipelines(), 5000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }
  }

  private async loadData() {
    try {
      const data = await projectService.list();
      this.projects = data.projects || [];
      await this.loadPipelines();
    } catch (error) {
      console.error('Failed to load projects:', error);
    } finally {
      this.isLoading = false;
    }
  }

  private async loadPipelines() {
    try {
      const pipelinesData = await pipelineService.list();
      this.pipelines = pipelinesData || [];
    } catch (error) {
      console.error('Failed to load pipelines:', error);
    }
  }

  private get runningPipelines() {
    return this.pipelines.filter(p => p.status === 'running');
  }

  private openCreateModal() {
    this.showCreateModal = true;
  }

  private closeCreateModal() {
    this.showCreateModal = false;
    this.newProjectName = '';
    this.newProjectDescription = '';
  }

  private async handleCreate(e: Event) {
    e.preventDefault();
    if (!this.newProjectName.trim()) return;

    try {
      await projectService.create({
        name: this.newProjectName,
        description: this.newProjectDescription,
      });
      this.closeCreateModal();
      this.loadData();
    } catch (error) {
      console.error('Failed to create project:', error);
    }
  }

  private navigateToProject(projectId: string) {
    window.location.hash = `/projects/${projectId}`;
  }

  private navigateToPipeline() {
    window.location.hash = '/pipeline';
  }

  render() {
    if (this.isLoading) {
      return html`
        <div class="loading">
          <div class="spinner"></div>
          <span>Loading projects...</span>
        </div>
      `;
    }

    return html`
      <div class="container">
        ${this.runningPipelines.length > 0 ? html`
          <div class="pipelines-banner">
            <div class="pipelines-info">
              <div class="pipelines-icon">
                <svg viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
              </div>
              <div>
                <div class="pipelines-title">
                  ${this.runningPipelines.length} Pipeline${this.runningPipelines.length > 1 ? 's' : ''} Running
                </div>
                <div class="pipelines-subtitle">
                  ${this.runningPipelines.map(p => p.id.slice(0, 8)).join(', ')}
                </div>
              </div>
            </div>
            <button class="view-pipeline-btn" @click=${this.navigateToPipeline}>
              View Pipeline
            </button>
          </div>
        ` : ''}

        <div class="header">
          <h1>Projects</h1>
          <button class="new-project-btn" @click=${this.openCreateModal}>
            New Project
          </button>
        </div>

        ${this.projects.length > 0 ? html`
          <div class="projects-grid">
            ${this.projects.map(project => html`
              <a
                class="project-card"
                href="#"
                @click=${(e: Event) => { e.preventDefault(); this.navigateToProject(project.id); }}
              >
                <div class="project-name">${project.name}</div>
                <div class="project-description">
                  ${project.description || 'No description'}
                </div>
                <div class="project-meta">
                  <span class="status-badge ${project.status === 'active' ? 'active' : 'inactive'}">
                    ${project.status}
                  </span>
                  <span class="project-date">
                    ${new Date(project.updated_at).toLocaleDateString()}
                  </span>
                </div>
              </a>
            `)}
          </div>
        ` : html`
          <div class="empty-state">
            <svg viewBox="0 0 24 24">
              <path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
            </svg>
            <h3>No projects</h3>
            <p>Get started by creating a new project.</p>
            <button class="empty-state-btn" @click=${this.openCreateModal}>
              New Project
            </button>
          </div>
        `}

        ${this.showCreateModal ? html`
          <div class="modal-overlay" @click=${(e: Event) => {
            if ((e.target as HTMLElement).classList.contains('modal-overlay')) {
              this.closeCreateModal();
            }
          }}>
            <div class="modal">
              <h2>Create Project</h2>
              <form @submit=${this.handleCreate}>
                <div class="modal-form-group">
                  <label>Name</label>
                  <input
                    type="text"
                    .value=${this.newProjectName}
                    @input=${(e: InputEvent) => this.newProjectName = (e.target as HTMLInputElement).value}
                    required
                  />
                </div>
                <div class="modal-form-group">
                  <label>Description</label>
                  <textarea
                    .value=${this.newProjectDescription}
                    @input=${(e: InputEvent) => this.newProjectDescription = (e.target as HTMLTextAreaElement).value}
                    rows="3"
                  ></textarea>
                </div>
                <div class="modal-actions">
                  <button type="button" class="modal-cancel-btn" @click=${this.closeCreateModal}>
                    Cancel
                  </button>
                  <button type="submit" class="modal-submit-btn">
                    Create
                  </button>
                </div>
              </form>
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'dashboard-page': DashboardPage;
  }
}
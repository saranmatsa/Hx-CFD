import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { CfdComponent } from './base.js';

interface NavItem {
  name: string;
  href: string;
  icon: string;
  description: string;
}

const navigation: NavItem[] = [
  { 
    name: 'Dashboard', 
    href: '/', 
    icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
    description: 'Overview and projects'
  },
  { 
    name: 'Projects', 
    href: '/projects', 
    icon: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z',
    description: 'Manage your projects'
  },
  { 
    name: 'Upload', 
    href: '/upload', 
    icon: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12',
    description: 'Upload geometry files'
  },
  { 
    name: 'Pipeline', 
    href: '/pipeline', 
    icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
    description: 'View pipeline status'
  },
];

const tools: NavItem[] = [
  { 
    name: 'FreeCAD', 
    href: '/tools/freecad', 
    icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
    description: 'CAD modeling'
  },
  { 
    name: 'Gmsh', 
    href: '/tools/gmsh', 
    icon: 'M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5',
    description: 'Mesh generation'
  },
  { 
    name: 'OpenFOAM', 
    href: '/tools/openfoam', 
    icon: 'M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z',
    description: 'CFD solver'
  },
];

/**
 * Sidebar navigation component
 */
@customElement('cfd-sidebar')
export class CfdSidebar extends CfdComponent {
  @state() private activePath = '/';
  @state() private runningSimulations: Array<{ id: string; name: string; status: string }> = [];

  static override styles = [
    ...CfdComponent.styles,
    css`
      :host {
        display: block;
        width: 16rem;
        background: var(--cfd-color-gray-900, #111827);
        color: white;
        height: 100%;
        display: flex;
        flex-direction: column;
      }
      .logo {
        display: flex;
        align-items: center;
        height: 4rem;
        padding: 0 1rem;
        background: var(--cfd-color-gray-800, #1f2937);
      }
      .logo span {
        font-size: 1.25rem;
        font-weight: 700;
      }
      nav {
        flex: 1;
        padding: 0.5rem;
        overflow-y: auto;
      }
      .section-title {
        padding: 0.5rem 1rem;
        font-size: 0.625rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--cfd-color-gray-400, #9ca3af);
        margin-bottom: 0.25rem;
      }
      .nav-item {
        display: flex;
        align-items: center;
        padding: 0.625rem 1rem;
        margin-top: 0.25rem;
        border-radius: 0.375rem;
        text-decoration: none;
        color: var(--cfd-color-gray-300, #d1d5db);
        transition: all 0.15s;
        cursor: pointer;
      }
      .nav-item:hover {
        background: var(--cfd-color-gray-800, #1f2937);
        color: white;
      }
      .nav-item.active {
        background: var(--cfd-color-gray-800, #1f2937);
        color: white;
      }
      .nav-item svg {
        width: 1.25rem;
        height: 1.25rem;
        margin-right: 0.75rem;
        flex-shrink: 0;
      }
      .nav-item-content {
        flex: 1;
      }
      .nav-item-name {
        font-size: 0.875rem;
        font-weight: 500;
      }
      .nav-item-desc {
        font-size: 0.75rem;
        color: var(--cfd-color-gray-500, #6b7280);
      }
      .nav-item:hover .nav-item-desc {
        color: var(--cfd-color-gray-400, #9ca3af);
      }
    `
  ];

  connectedCallback() {
    super.connectedCallback();
    this.activePath = window.location.pathname;
    window.addEventListener('popstate', this.handleRouteChange);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('popstate', this.handleRouteChange);
  }

  private handleRouteChange = () => {
    this.activePath = window.location.pathname;
  };

  private navigate(href: string) {
    window.history.pushState({}, '', href);
    this.activePath = href;
    this.dispatchEvent(new CustomEvent('navigate', { detail: href, bubbles: true, composed: true }));
  }

  private isActive(href: string, exact = false) {
    if (exact) return this.activePath === href;
    return this.activePath.startsWith(href);
  }

  override render() {
    return html`
      <div class="logo">
        <span>CFD Platform</span>
      </div>
      <nav>
        <div class="section-title">Navigation</div>
        ${navigation.map(item => html`
          <div 
            class="nav-item ${this.isActive(item.href, item.href === '/') ? 'active' : ''}"
            @click=${() => this.navigate(item.href)}
          >
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=${item.icon}></path>
            </svg>
            <div class="nav-item-content">
              <div class="nav-item-name">${item.name}</div>
              <div class="nav-item-desc">${item.description}</div>
            </div>
          </div>
        `)}

        <div class="section-title" style="margin-top: 1.5rem">Tools</div>
        ${tools.map(item => html`
          <div 
            class="nav-item ${this.activePath.startsWith(item.href) ? 'active' : ''}"
            @click=${() => this.navigate(item.href)}
          >
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=${item.icon}></path>
            </svg>
            <div class="nav-item-content">
              <div class="nav-item-name">${item.name}</div>
              <div class="nav-item-desc">${item.description}</div>
            </div>
          </div>
        `)}
      </nav>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'cfd-sidebar': CfdSidebar;
  }
}
/**
 * Frontend Application Entry Point
 * Bootstraps the CFD Platform application
 */

import './components/CFDAppShell';

// Type definitions for the app
export interface AppConfig {
  apiUrl?: string;
  wsUrl?: string;
  enableDebug?: boolean;
  defaultFidelity?: 'instant' | 'medium' | 'high';
  autoConnect?: boolean;
}

// Initialize the application
function initApp(config: AppConfig = {}) {
  // Create the app shell element
  const appShell = document.createElement('cfd-app-shell') as any;
  
  // Apply configuration
  if (config.apiUrl) {
    appShell.config = config;
  }

  // Append to document body
  document.body.appendChild(appShell);

  // Log initialization
  console.log('CFD Platform initialized', {
    version: '1.0.0',
    config
  });

  return appShell;
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    initApp();
  });
} else {
  initApp();
}

// Export initialization function
export { initApp };

// Global initialization helper
declare global {
  interface Window {
    initCFDApp: (config?: AppConfig) => Element;
  }
}

window.initCFDApp = initApp;
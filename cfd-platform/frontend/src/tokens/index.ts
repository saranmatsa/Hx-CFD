// HX CFD Design System Tokens
// Based on HX-CFD-Master-Prompt-v2.md

export const tokens = {
  // Layer 1 — Structural (Brand Identity)
  color: {
    structural: {
      black: '#000000',
      titanium: {
        900: '#1C1D1E',
        700: '#2C2D2F',
        500: '#3E3F42',
        300: '#6E6F72',
      },
      white: '#F5F5F6',
      gray: {
        100: '#E5E5E6',
        200: '#C5C5C6',
        300: '#A5A5A6',
        400: '#858586',
      },
    },
    // Layer 2 — Functional (Status Signals)
    status: {
      success: '#4CAF50',
      warning: '#FF9800',
      error: '#F44336',
      active: '#4CAF50',
      selection: '#F5F5F6',
    },
    // Layer 3 — Scientific / Data Visualization
    scientific: {
      // Standard colormaps for velocity, pressure, temperature
      jet: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF0000', '#800000'],
      viridis: ['#440154', '#482878', '#3E4989', '#31688E', '#26828E', '#1F9E89', '#35B779', '#6DCD59', '#B4DE2C', '#FDE725'],
    },
  },

  // Typography
  type: {
    family: {
      ui: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      data: 'JetBrains Mono, "IBM Plex Mono", "Fira Code", monospace',
    },
    scale: {
      display: '32px',
      heading: '14px',
      body: '14px',
      caption: '12px',
      'data-lg': '16px',
      'data-sm': '13px',
    },
    weight: {
      regular: 400,
      medium: 500,
      semibold: 600,
    },
    letterSpacing: {
      heading: '0.1em',
    },
  },

  // Spacing (8px grid)
  spacing: {
    0: '0px',
    1: '4px', // Half-step for dense contexts
    2: '8px',
    3: '16px',
    4: '24px',
    5: '32px',
    6: '40px',
    7: '48px',
    8: '64px',
  },

  // Shape Language
  radius: {
    sm: '4px',
    md: '4px',
    none: '0px',
  },

  // Motion
  motion: {
    duration: {
      instant: '80ms',
      fast: '200ms',
    },
    easing: {
      standard: 'cubic-bezier(0.2, 0, 0, 1)',
    },
  },

  // Elevation
  elevation: {
    0: 'none',
    1: '0 1px 3px rgba(0, 0, 0, 0.3)',
    2: '0 4px 12px rgba(0, 0, 0, 0.4)',
    3: '0 8px 24px rgba(0, 0, 0, 0.5)',
  },

  // Iconography
  icon: {
    size: {
      sm: '16px',
      md: '20px',
      lg: '24px',
    },
  },
} as const;

export type Tokens = typeof tokens;

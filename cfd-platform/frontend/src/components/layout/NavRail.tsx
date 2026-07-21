import React from 'react';
import { tokens } from '../../tokens';

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'geometry', label: 'Geometry', icon: '🔷' },
  { id: 'meshing', label: 'Meshing', icon: '🕸️' },
  { id: 'physics', label: 'Physics', icon: '⚡' },
  { id: 'solver', label: 'Solver', icon: '🔄' },
  { id: 'results', label: 'Results', icon: '📈' },
  { id: 'reports', label: 'Reports', icon: '📄' },
  { id: 'ai-copilot', label: 'AI Copilot', icon: '🤖' },
  { id: 'extensions', label: 'Extensions', icon: '🔌' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
];

interface NavRailProps {
  activeModule: string;
  onModuleChange: (module: string) => void;
}

export const NavRail: React.FC<NavRailProps> = ({ activeModule, onModuleChange }) => {
  return (
    <nav
      style={{
        width: '131px',
        height: '100vh',
        backgroundColor: '#020204',
        display: 'flex',
        flexDirection: 'column',
        padding: '0',
      }}
    >
      {/* Main Navigation - row-based with icon + text */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0', flex: 1 }}>
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onModuleChange(item.id)}
            style={{
              width: '100%',
              height: '48px',
              display: 'flex',
              alignItems: 'center',
              gap: tokens.spacing[2],
              padding: '0 ' + tokens.spacing[3],
              backgroundColor: activeModule === item.id ? '#0C0C10' : 'transparent',
              border: 'none',
              cursor: 'pointer',
              transition: 'all ' + tokens.motion.duration.instant + ' ' + tokens.motion.easing.standard,
              color: activeModule === item.id ? tokens.color.structural.white : tokens.color.structural.titanium[300],
              fontSize: '13px',
              fontFamily: tokens.type.family.ui,
            }}
            title={item.label}
          >
            <span style={{ fontSize: '18px' }}>{item.icon}</span>
            <span style={{ fontWeight: 400 }}>{item.label}</span>
          </button>
        ))}
      </div>

      {/* Collapse button at bottom */}
      <div style={{ height: '48px', borderTop: '1px solid #0C0D0F' }}>
        <button
          style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: tokens.color.structural.titanium[300],
            fontSize: '18px',
          }}
        >
          «
        </button>
      </div>
    </nav>
  );
};

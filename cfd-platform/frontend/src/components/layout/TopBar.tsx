import React from 'react';
import { tokens } from '../../tokens';

interface TopBarProps {
  currentModule: string;
  projectName?: string;
  solverStatus?: {
    running: boolean;
    elapsed: string;
    total: string;
    iterations: number;
    totalIterations: number;
  };
}

export const TopBar: React.FC<TopBarProps> = ({
  currentModule,
  projectName = 'Aero_Turbine_Study',
  solverStatus
}) => {
  return (
    <header
      style={{
        height: '45px',
        backgroundColor: '#000002',
        borderBottom: '1px solid #0C0D0F',
        display: 'flex',
        alignItems: 'center',
        padding: '0 ' + tokens.spacing[3],
        gap: tokens.spacing[3],
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[2] }}>
        <div style={{
          width: '24px',
          height: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '16px',
          color: tokens.color.structural.white,
        }}>
          ◆
        </div>
        <span style={{
          color: tokens.color.structural.white,
          fontSize: '14px',
          fontWeight: 600,
          letterSpacing: '0.05em',
        }}>
          HX CFD
        </span>
      </div>

      {/* Collapse icon */}
      <button style={{
        width: '24px',
        height: '24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'transparent',
        border: 'none',
        color: tokens.color.structural.titanium[300],
        fontSize: '16px',
        cursor: 'pointer',
      }}>
        ≡
      </button>

      {/* Project Selector */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <span style={{
          fontSize: '10px',
          color: tokens.color.structural.titanium[300],
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}>
          PROJECT
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{
            color: tokens.color.structural.white,
            fontSize: '13px',
            fontFamily: tokens.type.family.ui,
          }}>
            {projectName}
          </span>
          <span style={{ fontSize: '10px', color: tokens.color.structural.titanium[300] }}>
            ▼
          </span>
        </div>
      </div>

      {/* Module Selector */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <span style={{
          fontSize: '10px',
          color: tokens.color.structural.titanium[300],
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}>
          MODULE
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{
            color: tokens.color.structural.white,
            fontSize: '13px',
            fontFamily: tokens.type.family.ui,
          }}>
            {currentModule}
          </span>
          <span style={{ fontSize: '10px', color: tokens.color.structural.titanium[300] }}>
            ▼
          </span>
        </div>
      </div>

      {/* Search Bar (centered) */}
      <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: tokens.spacing[2],
          padding: tokens.spacing[1] + ' ' + tokens.spacing[3],
          backgroundColor: '#07080A',
          border: '1px solid #121315',
          borderRadius: tokens.radius.sm,
          width: '300px',
        }}>
          <span style={{ fontSize: '14px', color: tokens.color.structural.titanium[300] }}>
            🔍
          </span>
          <span style={{
            color: tokens.color.structural.titanium[300],
            fontSize: '12px',
            fontFamily: tokens.type.family.ui,
          }}>
            Search / Command Palette (Ctrl + K)
          </span>
        </div>
      </div>

      {/* Right side elements */}
      <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[3] }}>
        {/* Solver Status */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span style={{
            fontSize: '10px',
            color: tokens.color.structural.titanium[300],
            textTransform: 'uppercase',
          }}>
            Solver
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#00C853',
            }}></span>
            <span style={{
              color: tokens.color.structural.white,
              fontSize: '13px',
              fontFamily: tokens.type.family.ui,
            }}>
              Running
            </span>
          </div>
        </div>

        {/* Time */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span style={{
            fontSize: '10px',
            color: tokens.color.structural.titanium[300],
            textTransform: 'uppercase',
          }}>
            Time
          </span>
          {solverStatus && (
            <span style={{
              color: tokens.color.structural.white,
              fontSize: '13px',
              fontFamily: tokens.type.family.data,
            }}>
              {solverStatus.elapsed} / {solverStatus.total}
            </span>
          )}
        </div>

        {/* Iterations */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span style={{
            fontSize: '10px',
            color: tokens.color.structural.titanium[300],
            textTransform: 'uppercase',
          }}>
            Iterations
          </span>
          {solverStatus && (
            <span style={{
              color: tokens.color.structural.white,
              fontSize: '13px',
              fontFamily: tokens.type.family.data,
            }}>
              {solverStatus.iterations} / {solverStatus.totalIterations}
            </span>
          )}
        </div>

        {/* Icon buttons */}
        <div style={{ display: 'flex', gap: tokens.spacing[2] }}>
          <button style={{
            width: '24px',
            height: '24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'transparent',
            border: 'none',
            color: tokens.color.structural.titanium[300],
            fontSize: '14px',
            cursor: 'pointer',
          }}>
            ⬚
          </button>
          <button style={{
            width: '24px',
            height: '24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'transparent',
            border: 'none',
            color: tokens.color.structural.titanium[300],
            fontSize: '14px',
            cursor: 'pointer',
          }}>
            🔔
          </button>
          <button style={{
            width: '24px',
            height: '24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'transparent',
            border: 'none',
            color: tokens.color.structural.titanium[300],
            fontSize: '14px',
            cursor: 'pointer',
          }}>
            ⚙️
          </button>
          <button style={{
            width: '24px',
            height: '24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'transparent',
            border: 'none',
            color: tokens.color.structural.titanium[300],
            fontSize: '14px',
            cursor: 'pointer',
          }}>
            ⊞
          </button>
        </div>

        {/* Avatar */}
        <div style={{
          width: '28px',
          height: '28px',
          borderRadius: '50%',
          backgroundColor: tokens.color.structural.titanium[700],
          border: '1px solid ' + tokens.color.structural.titanium[500],
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '12px',
          color: tokens.color.structural.white,
        }}>
          👤
        </div>
      </div>
    </header>
  );
};

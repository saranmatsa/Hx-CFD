import React from 'react';
import { tokens } from '../../tokens';
import { AICopilot } from '../ai/AICopilot';

// Mock residual data
const residualData = [
  { iteration: 0, U: 1.0e-0, p: 1.0e-0, k: 1.0e-0, omega: 1.0e-0 },
  { iteration: 100, U: 1.2e-1, p: 8.5e-2, k: 9.2e-2, omega: 8.8e-2 },
  { iteration: 200, U: 5.4e-2, p: 4.1e-2, k: 4.8e-2, omega: 4.5e-2 },
  { iteration: 300, U: 2.1e-2, p: 1.8e-2, k: 2.3e-2, omega: 2.1e-2 },
  { iteration: 400, U: 8.5e-3, p: 7.2e-3, k: 9.1e-3, omega: 8.4e-3 },
  { iteration: 500, U: 3.2e-3, p: 2.8e-3, k: 3.5e-3, omega: 3.2e-3 },
  { iteration: 600, U: 1.2e-3, p: 1.1e-3, k: 1.4e-3, omega: 1.3e-3 },
  { iteration: 700, U: 4.8e-4, p: 4.2e-4, k: 5.3e-4, omega: 4.9e-4 },
  { iteration: 800, U: 1.9e-4, p: 1.7e-4, k: 2.1e-4, omega: 1.9e-4 },
  { iteration: 900, U: 7.5e-5, p: 6.8e-5, k: 8.4e-5, omega: 7.8e-5 },
];

// Mock monitor points data
const monitorPointsData = [
  { name: 'Inlet Mass Flow', type: 'Mass Flow', value: 2.453, units: 'kg/s' },
  { name: 'Outlet Mass Flow', type: 'Mass Flow', value: 2.451, units: 'kg/s' },
  { name: 'Pressure Drop', type: 'Pressure', value: 1253.6, units: 'Pa' },
  { name: 'Efficiency', type: 'Custom', value: 89.37, units: '%' },
  { name: 'Turbine Torque', type: 'Torque', value: 12.43, units: 'N·m' },
];

interface ResidualsChartProps {
  data: typeof residualData;
}

const ResidualsChart: React.FC<ResidualsChartProps> = ({ data }) => {
  const maxIteration = Math.max(...data.map(d => d.iteration));
  const maxValue = Math.max(...data.map(d => Math.max(d.U, d.p, d.k, d.omega)));

  return (
    <div style={{ width: '100%', height: '100%', padding: tokens.spacing[3] }}>
      <div style={{ marginBottom: tokens.spacing[2] }}>
        <h4 style={{
          fontSize: '11px',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: tokens.color.structural.titanium[300],
          marginBottom: tokens.spacing[2],
        }}>
          SOLVER RESIDUALS
        </h4>
      </div>

      {/* Simple SVG chart */}
      <svg width="100%" height="120" viewBox="0 0 400 120" style={{ backgroundColor: tokens.color.structural.titanium[900] }}>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => (
          <line
            key={i}
            x1="40"
            y1={10 + ratio * 100}
            x2="390"
            y2={10 + ratio * 100}
            stroke={tokens.color.structural.titanium[500]}
            strokeWidth="0.5"
          />
        ))}

        {/* Y-axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => (
          <text
            key={i}
            x="35"
            y={14 + ratio * 100}
            fill={tokens.color.structural.titanium[300]}
            fontSize="9"
            textAnchor="end"
            fontFamily={tokens.type.family.data}
          >
            {(maxValue * (1 - ratio)).toExponential(1)}
          </text>
        ))}

        {/* Residual lines */}
        {['U', 'p', 'k', 'omega'].map((field, fieldIndex) => {
          const colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0'];
          const points = data.map((d) => {
            const x = 40 + (d.iteration / maxIteration) * 350;
            const y = 110 - (d[field as keyof typeof d] as number / maxValue) * 100;
            return `${x},${y}`;
          }).join(' ');

          return (
            <polyline
              key={field}
              points={points}
              fill="none"
              stroke={colors[fieldIndex]}
              strokeWidth="1.5"
            />
          );
        })}

        {/* Legend */}
        {['U', 'p', 'k', 'ω'].map((label, i) => {
          const colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0'];
          return (
            <g key={label}>
              <rect x={50 + i * 80} y="5" width="10" height="10" fill={colors[i]} />
              <text
                x={65 + i * 80}
                y="13"
                fill={tokens.color.structural.white}
                fontSize="10"
                fontFamily={tokens.type.family.ui}
              >
                {label}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Current values */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: tokens.spacing[2],
        marginTop: tokens.spacing[2],
        paddingTop: tokens.spacing[2],
        borderTop: '1px solid ' + tokens.color.structural.titanium[500]
      }}>
        {['U', 'p', 'k', 'omega'].map((field, i) => {
          const colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0'];
          const currentValue = data[data.length - 1][field as keyof typeof data[0]] as number;
          return (
            <div key={field} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '10px', color: colors[i], marginBottom: '2px' }}>{field}</div>
              <div style={{
                fontSize: '13px',
                fontFamily: tokens.type.family.data,
                color: tokens.color.structural.white
              }}>
                {currentValue.toExponential(2)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

interface MonitorPointsTableProps {
  data: typeof monitorPointsData;
}

const MonitorPointsTable: React.FC<MonitorPointsTableProps> = ({ data }) => {
  return (
    <div style={{ width: '100%', height: '100%', padding: tokens.spacing[3] }}>
      <h4 style={{
        fontSize: '11px',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.1em',
        color: tokens.color.structural.titanium[300],
        marginBottom: tokens.spacing[2],
      }}>
        MONITOR POINTS
      </h4>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid ' + tokens.color.structural.titanium[500] }}>
            <th style={{
              textAlign: 'left',
              padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
              fontSize: '11px',
              fontWeight: 600,
              color: tokens.color.structural.titanium[300],
              fontFamily: tokens.type.family.ui
            }}>
              Name
            </th>
            <th style={{
              textAlign: 'left',
              padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
              fontSize: '11px',
              fontWeight: 600,
              color: tokens.color.structural.titanium[300],
              fontFamily: tokens.type.family.ui
            }}>
              Type
            </th>
            <th style={{
              textAlign: 'right',
              padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
              fontSize: '11px',
              fontWeight: 600,
              color: tokens.color.structural.titanium[300],
              fontFamily: tokens.type.family.ui
            }}>
              Value
            </th>
            <th style={{
              textAlign: 'left',
              padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
              fontSize: '11px',
              fontWeight: 600,
              color: tokens.color.structural.titanium[300],
              fontFamily: tokens.type.family.ui
            }}>
              Units
            </th>
            <th style={{
              textAlign: 'center',
              padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
              fontSize: '11px',
              fontWeight: 600,
              color: tokens.color.structural.titanium[300],
              fontFamily: tokens.type.family.ui
            }}>
              Trend
            </th>
          </tr>
        </thead>
        <tbody>
          {data.map((point, index) => (
            <tr key={index} style={{ borderBottom: '1px solid ' + tokens.color.structural.titanium[500] }}>
              <td style={{
                padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
                fontSize: '12px',
                color: tokens.color.structural.white,
                fontFamily: tokens.type.family.ui
              }}>
                {point.name}
              </td>
              <td style={{
                padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
                fontSize: '12px',
                color: tokens.color.structural.white,
                fontFamily: tokens.type.family.ui
              }}>
                {point.type}
              </td>
              <td style={{
                padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
                textAlign: 'right',
                fontSize: '12px',
                color: tokens.color.structural.white,
                fontFamily: tokens.type.family.data
              }}>
                {point.value}
              </td>
              <td style={{
                padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
                fontSize: '12px',
                color: tokens.color.structural.white,
                fontFamily: tokens.type.family.ui
              }}>
                {point.units}
              </td>
              <td style={{
                padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
                textAlign: 'center',
                fontSize: '12px',
                color: tokens.color.structural.white,
              }}>
                📈
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

interface BottomDockProps {
  height?: string;
}

const SliceViewPanel: React.FC = () => {
  return (
    <div style={{ width: '100%', height: '100%', padding: tokens.spacing[3] }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: tokens.spacing[2] }}>
        <div>
          <h4 style={{
            fontSize: '11px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: tokens.color.structural.titanium[300],
            marginBottom: '2px',
          }}>
            Static Pressure
          </h4>
          <span style={{ fontSize: '10px', color: tokens.color.structural.titanium[300] }}>Pa</span>
        </div>
      </div>

      {/* Circular contour visualization placeholder */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: tokens.spacing[3],
        height: 'calc(100% - 60px)',
      }}>
        {/* Legend */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '150px' }}>
          {['2500', '1250', '0', '-1250', '-2500'].map((value) => (
            <span key={value} style={{
              fontSize: '10px',
              color: tokens.color.structural.titanium[300],
              fontFamily: tokens.type.family.data,
              textAlign: 'right',
            }}>
              {value}
            </span>
          ))}
        </div>

        {/* Circular plot placeholder */}
        <div style={{
          width: '150px',
          height: '150px',
          borderRadius: '50%',
          backgroundColor: '#0024A8',
          border: '2px solid #0C0D0F',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <span style={{ fontSize: '12px', color: tokens.color.structural.titanium[300] }}>
            Slice View
          </span>
        </div>
      </div>

      {/* Controls */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: tokens.spacing[2],
        paddingTop: tokens.spacing[2],
        borderTop: '1px solid ' + tokens.color.structural.titanium[500],
      }}>
        <span style={{ fontSize: '11px', color: tokens.color.structural.titanium[300] }}>Plane</span>
        <div style={{
          padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
          backgroundColor: tokens.color.structural.titanium[700],
          border: '1px solid ' + tokens.color.structural.titanium[500],
          borderRadius: tokens.radius.sm,
          fontSize: '11px',
          color: tokens.color.structural.white,
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
        }}>
          Z = 0.128 m ▼
        </div>
        <div style={{ flex: 1, height: '4px', backgroundColor: tokens.color.structural.titanium[700], borderRadius: '2px' }}>
          <div style={{ width: '50%', height: '100%', backgroundColor: tokens.color.structural.titanium[300], borderRadius: '2px' }}></div>
        </div>
        <span style={{ fontSize: '11px', fontFamily: tokens.type.family.data, color: tokens.color.structural.white }}>1.00</span>
      </div>
    </div>
  );
};

export const BottomDock: React.FC<BottomDockProps> = ({ height = '263px' }) => {
  return (
    <div
      style={{
        height,
        backgroundColor: '#0C0D11',
        borderTop: '1px solid #0C0D0F',
        display: 'flex',
      }}
    >
      {/* Residuals Panel - x=131–470, width=339px */}
      <div style={{
        width: '339px',
        borderRight: '1px solid #0C0D0F',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{
          height: '36px',
          padding: '0 ' + tokens.spacing[3],
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #0C0D0F',
        }}>
          <span style={{
            fontSize: '11px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: tokens.color.structural.titanium[300],
          }}>
            RESIDUALS
          </span>
          <div style={{ display: 'flex', gap: tokens.spacing[1] }}>
            <button style={{
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              color: tokens.color.structural.titanium[300],
              fontSize: '12px',
              cursor: 'pointer',
            }}>📌</button>
            <button style={{
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              color: tokens.color.structural.titanium[300],
              fontSize: '12px',
              cursor: 'pointer',
            }}>⛶</button>
            <button style={{
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              color: tokens.color.structural.titanium[300],
              fontSize: '12px',
              cursor: 'pointer',
            }}>✕</button>
          </div>
        </div>
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <ResidualsChart data={residualData} />
        </div>
      </div>

      {/* Monitor Points Panel - x=470–890, width=420px */}
      <div style={{
        width: '420px',
        borderRight: '1px solid #0C0D0F',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{
          height: '36px',
          padding: '0 ' + tokens.spacing[3],
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #0C0D0F',
        }}>
          <span style={{
            fontSize: '11px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: tokens.color.structural.titanium[300],
          }}>
            MONITOR POINTS
          </span>
          <div style={{ display: 'flex', gap: tokens.spacing[1] }}>
            <button style={{
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              color: tokens.color.structural.titanium[300],
              fontSize: '12px',
              cursor: 'pointer',
            }}>📌</button>
            <button style={{
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              color: tokens.color.structural.titanium[300],
              fontSize: '12px',
              cursor: 'pointer',
            }}>⛶</button>
            <button style={{
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              color: tokens.color.structural.titanium[300],
              fontSize: '12px',
              cursor: 'pointer',
            }}>✕</button>
          </div>
        </div>
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <MonitorPointsTable data={monitorPointsData} />
        </div>
      </div>

      {/* Slice View Panel - x=890–1120, width=230px */}
      <div style={{
        width: '230px',
        borderRight: '1px solid #0C0D0F',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{
          height: '36px',
          padding: '0 ' + tokens.spacing[3],
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #0C0D0F',
        }}>
          <span style={{
            fontSize: '11px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: tokens.color.structural.titanium[300],
          }}>
            SLICE VIEW
          </span>
          <div style={{ display: 'flex', gap: tokens.spacing[1] }}>
            <button style={{
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              color: tokens.color.structural.titanium[300],
              fontSize: '12px',
              cursor: 'pointer',
            }}>📌</button>
            <button style={{
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              color: tokens.color.structural.titanium[300],
              fontSize: '12px',
              cursor: 'pointer',
            }}>⛶</button>
            <button style={{
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              color: tokens.color.structural.titanium[300],
              fontSize: '12px',
              cursor: 'pointer',
            }}>✕</button>
          </div>
        </div>
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <SliceViewPanel />
        </div>
      </div>

      {/* AI Copilot Panel - x=1120–1536, width=416px */}
      <div style={{
        width: '416px',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{
          height: '36px',
          padding: '0 ' + tokens.spacing[3],
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #0C0D0F',
        }}>
          <span style={{
            fontSize: '11px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: tokens.color.structural.titanium[300],
          }}>
            AI COPILOT
          </span>
          <div style={{ display: 'flex', gap: tokens.spacing[1] }}>
            <button style={{
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              color: tokens.color.structural.titanium[300],
              fontSize: '12px',
              cursor: 'pointer',
            }}>📌</button>
            <button style={{
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              color: tokens.color.structural.titanium[300],
              fontSize: '12px',
              cursor: 'pointer',
            }}>⛶</button>
            <button style={{
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              color: tokens.color.structural.titanium[300],
              fontSize: '12px',
              cursor: 'pointer',
            }}>✕</button>
          </div>
        </div>
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <AICopilot />
        </div>
      </div>
    </div>
  );
};

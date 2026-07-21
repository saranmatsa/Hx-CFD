import React, { useState } from 'react';
import { tokens } from '../../tokens';

type TabType = 'selection' | 'materials' | 'bcs' | 'loads' | 'mesh';

interface TabConfig {
  id: TabType;
  label: string;
}

const tabs: TabConfig[] = [
  { id: 'selection', label: 'Selection' },
  { id: 'materials', label: 'Materials' },
  { id: 'bcs', label: 'BCs' },
  { id: 'loads', label: 'Loads' },
  { id: 'mesh', label: 'Mesh' },
];

interface SectionProps {
  title: string;
  children: React.ReactNode;
}

const Section: React.FC<SectionProps> = ({ title, children }) => {
  return (
    <div style={{ marginBottom: tokens.spacing[4] }}>
      <h4
        style={{
          fontSize: '10px',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: tokens.color.structural.titanium[300],
          marginBottom: tokens.spacing[2],
        }}
      >
        {title}
      </h4>
      {children}
    </div>
  );
};

interface PropertyRowProps {
  label: string;
  value: string | number;
  unit?: string;
  isMonospace?: boolean;
  isDropdown?: boolean;
  isInput?: boolean;
  disabled?: boolean;
}

const PropertyRow: React.FC<PropertyRowProps> = ({ label, value, unit, isMonospace, isDropdown, isInput, disabled }) => {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: tokens.spacing[1] + ' 0',
      }}
    >
      <span style={{
        fontSize: '12px',
        color: tokens.color.structural.titanium[300],
        fontFamily: tokens.type.family.ui
      }}>
        {label}
      </span>
      {isDropdown ? (
        <div style={{
          padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
          backgroundColor: disabled ? tokens.color.structural.titanium[900] : tokens.color.structural.titanium[700],
          border: '1px solid ' + tokens.color.structural.titanium[500],
          borderRadius: tokens.radius.sm,
          fontSize: '12px',
          color: disabled ? tokens.color.structural.titanium[300] : tokens.color.structural.white,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          minWidth: '120px',
        }}>
          <span>{value}</span>
          <span style={{ fontSize: '10px' }}>▼</span>
        </div>
      ) : isInput ? (
        <div style={{
          padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
          backgroundColor: disabled ? tokens.color.structural.titanium[900] : tokens.color.structural.titanium[700],
          border: '1px solid ' + tokens.color.structural.titanium[500],
          borderRadius: tokens.radius.sm,
          fontSize: '12px',
          color: disabled ? tokens.color.structural.titanium[300] : tokens.color.structural.white,
          minWidth: '120px',
        }}>
          {value}
        </div>
      ) : (
        <span style={{
          fontSize: '12px',
          color: disabled ? tokens.color.structural.titanium[300] : tokens.color.structural.white,
          fontFamily: isMonospace ? tokens.type.family.data : tokens.type.family.ui
        }}>
          {typeof value === 'number' && !isMonospace ? value : value}
          {unit && <span style={{ marginLeft: '4px', color: tokens.color.structural.titanium[300] }}>{unit}</span>}
        </span>
      )}
    </div>
  );
};

interface ToggleSwitchProps {
  on: boolean;
  onChange?: (value: boolean) => void;
}

const ToggleSwitch: React.FC<ToggleSwitchProps> = ({ on, onChange }) => {
  return (
    <div
      onClick={() => onChange?.(!on)}
      style={{
        width: '32px',
        height: '16px',
        borderRadius: '8px',
        backgroundColor: on ? '#2196F3' : tokens.color.structural.titanium[700],
        position: 'relative',
        cursor: 'pointer',
        transition: 'background-color 0.2s',
      }}
    >
      <div style={{
        width: '12px',
        height: '12px',
        borderRadius: '50%',
        backgroundColor: tokens.color.structural.white,
        position: 'absolute',
        top: '2px',
        left: on ? '18px' : '2px',
        transition: 'left 0.2s',
      }}></div>
    </div>
  );
};

interface DetailsPanelProps {
  width?: string;
}

export const DetailsPanel: React.FC<DetailsPanelProps> = ({ width = '340px' }) => {
  const [activeTab, setActiveTab] = useState<TabType>('selection');
  const [monitoringEnabled, setMonitoringEnabled] = useState(true);
  const [roughWallEnabled, setRoughWallEnabled] = useState(false);

  return (
    <div
      style={{
        width,
        height: '100%',
        backgroundColor: '#0D0E10',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Panel Header */}
      <div
        style={{
          height: '36px',
          padding: '0 ' + tokens.spacing[3],
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #0C0D0F',
        }}
      >
        <span
          style={{
            fontSize: '11px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: tokens.color.structural.titanium[300],
          }}
        >
          DETAILS
        </span>
        <button
          style={{
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
          }}
        >
          ✕
        </button>
      </div>

      {/* Tabs */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid #0C0D0F',
        }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              flex: 1,
              padding: tokens.spacing[2] + ' ' + tokens.spacing[3],
              backgroundColor: activeTab === tab.id ? '#141418' : 'transparent',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid ' + tokens.color.structural.white : 'none',
              color: activeTab === tab.id ? tokens.color.structural.white : tokens.color.structural.titanium[300],
              fontSize: '12px',
              fontWeight: 500,
              cursor: 'pointer',
              fontFamily: tokens.type.family.ui,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div
        style={{
          flex: 1,
          overflow: 'auto',
          padding: tokens.spacing[3],
        }}
      >
        {activeTab === 'selection' && (
          <>
            <Section title="FACE (ID: 45871)">
              <PropertyRow label="Type" value="WALL" />
              <PropertyRow label="Area" value="0.013245" unit="m²" isMonospace />
              <PropertyRow label="Center" value="(0.128, -0.045, 0.213)" unit="m" isMonospace />
              <PropertyRow label="Normal" value="(0.000, 1.000, 0.000)" isMonospace />
              <PropertyRow label="Zone" value="Rotor_Blade_Surface" />
            </Section>

            <Section title="BOUNDARY CONDITION">
              <PropertyRow label="Type" value="Wall" isDropdown />
              <PropertyRow label="Wall Type" value="No Slip" isDropdown />
              <PropertyRow label="Roughness" value="1.5e-06 m" isInput />
            </Section>

            <Section title="WALL TREATMENT">
              <PropertyRow label="Y+" value="1.28" isMonospace />
              <PropertyRow label="Model" value="Automatic" isDropdown />
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: tokens.spacing[1] + ' 0',
              }}>
                <span style={{ fontSize: '12px', color: tokens.color.structural.titanium[300] }}>Rough Wall</span>
                <ToggleSwitch on={roughWallEnabled} onChange={setRoughWallEnabled} />
              </div>
            </Section>

            <Section title="HEAT TRANSFER">
              <PropertyRow label="Thermal Condition" value="Adiabatic" isDropdown />
              <PropertyRow label="Heat Flux" value="0 W/m²" isInput disabled />
            </Section>

            <Section title="MONITORING">
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: tokens.spacing[1] + ' 0',
              }}>
                <span style={{ fontSize: '12px', color: tokens.color.structural.titanium[300] }}>Enable Monitoring</span>
                <ToggleSwitch on={monitoringEnabled} onChange={setMonitoringEnabled} />
              </div>
              <button
                style={{
                  width: '100%',
                  marginTop: tokens.spacing[2],
                  padding: tokens.spacing[2] + ' ' + tokens.spacing[3],
                  backgroundColor: tokens.color.structural.titanium[700],
                  border: '1px solid ' + tokens.color.structural.titanium[500],
                  borderRadius: tokens.radius.sm,
                  color: tokens.color.structural.white,
                  fontSize: '12px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: tokens.spacing[1],
                }}
              >
                <span>📊</span>
                <span>Create Report for Selection</span>
              </button>
            </Section>
          </>
        )}
      </div>
    </div>
  );
};

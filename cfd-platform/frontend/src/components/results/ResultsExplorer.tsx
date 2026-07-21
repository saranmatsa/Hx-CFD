import React, { useState } from 'react';
import { tokens } from '../../tokens';

interface FieldNode {
  id: string;
  label: string;
  type: 'folder' | 'file';
  children?: FieldNode[];
  visible: boolean;
  selected: boolean;
  color?: string;
}

const fieldsData: FieldNode[] = [
  {
    id: 'velocity',
    label: 'Velocity',
    type: 'folder',
    visible: true,
    selected: false,
    color: '#4CAF50',
    children: [
      { id: 'velocity-mag', label: 'Velocity Magnitude', type: 'file', visible: true, selected: true, color: '#4CAF50' },
      { id: 'velocity-x', label: 'Velocity X', type: 'file', visible: true, selected: false, color: '#4CAF50' },
      { id: 'velocity-y', label: 'Velocity Y', type: 'file', visible: true, selected: false, color: '#4CAF50' },
      { id: 'velocity-z', label: 'Velocity Z', type: 'file', visible: true, selected: false, color: '#4CAF50' },
    ],
  },
  {
    id: 'pressure',
    label: 'Pressure',
    type: 'folder',
    visible: true,
    selected: false,
    color: '#2196F3',
    children: [
      { id: 'static-pressure', label: 'Static Pressure', type: 'file', visible: true, selected: false, color: '#2196F3' },
      { id: 'total-pressure', label: 'Total Pressure', type: 'file', visible: true, selected: false, color: '#2196F3' },
    ],
  },
  {
    id: 'temperature',
    label: 'Temperature',
    type: 'folder',
    visible: true,
    selected: false,
    color: '#FF9800',
    children: [
      { id: 'temperature', label: 'Temperature', type: 'file', visible: true, selected: false, color: '#FF9800' },
    ],
  },
  {
    id: 'turbulence',
    label: 'Turbulence',
    type: 'folder',
    visible: true,
    selected: false,
    color: '#9C27B0',
    children: [
      { id: 'tke', label: 'Turbulent Kinetic Energy (k)', type: 'file', visible: true, selected: false, color: '#9C27B0' },
      { id: 'omega', label: 'Turbulent Dissipation (ε)', type: 'file', visible: true, selected: false, color: '#9C27B0' },
    ],
  },
  {
    id: 'wall-shear',
    label: 'Wall Shear Stress',
    type: 'folder',
    visible: false,
    selected: false,
    children: [],
  },
  {
    id: 'mach',
    label: 'Mach Number',
    type: 'folder',
    visible: false,
    selected: false,
    children: [],
  },
  {
    id: 'density',
    label: 'Density',
    type: 'folder',
    visible: false,
    selected: false,
    children: [],
  },
];

interface ClipItem {
  id: string;
  label: string;
  hasToggle: boolean;
  toggleOn: boolean;
  hasSettings: boolean;
}

const clipsData: ClipItem[] = [
  { id: 'x-clip', label: 'X Clip', hasToggle: false, toggleOn: false, hasSettings: true },
  { id: 'y-clip', label: 'Y Clip', hasToggle: false, toggleOn: false, hasSettings: true },
  { id: 'z-clip', label: 'Z Clip', hasToggle: false, toggleOn: false, hasSettings: true },
  { id: 'custom-1', label: 'Custom Clip 1', hasToggle: true, toggleOn: true, hasSettings: false },
];

interface SceneItem {
  id: string;
  label: string;
  selected: boolean;
}

const scenesData: SceneItem[] = [
  { id: 'scene-1', label: 'Scene 1', selected: true },
  { id: 'scene-2', label: 'Scene 2', selected: false },
  { id: 'scene-3', label: 'Scene 3', selected: false },
];

interface FieldRowProps {
  node: FieldNode;
  level: number;
  onToggle: (id: string) => void;
}

const FieldRow: React.FC<FieldRowProps> = ({ node, level, onToggle }) => {
  const [expanded, setExpanded] = useState(node.type === 'folder' && node.id !== 'velocity' ? false : true);

  const handleClick = () => {
    if (node.type === 'folder') {
      setExpanded(!expanded);
      onToggle(node.id);
    }
  };

  return (
    <div>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
          paddingLeft: (tokens.spacing[2] + level * 12) + 'px',
          cursor: node.type === 'folder' ? 'pointer' : 'default',
          backgroundColor: node.selected ? '#141418' : 'transparent',
          borderLeft: node.selected ? '2px solid ' + tokens.color.structural.white : 'none',
          transition: 'background-color ' + tokens.motion.duration.instant + ' ' + tokens.motion.easing.standard,
        }}
        onClick={handleClick}
        onMouseEnter={(e) => {
          if (!node.selected) {
            e.currentTarget.style.backgroundColor = tokens.color.structural.titanium[700];
          }
        }}
        onMouseLeave={(e) => {
          if (!node.selected) {
            e.currentTarget.style.backgroundColor = 'transparent';
          }
        }}
      >
        <span style={{ marginRight: tokens.spacing[1], fontSize: '10px', color: tokens.color.structural.titanium[300] }}>
          {node.type === 'folder' ? (expanded ? '▼' : '▶') : ''}
        </span>
        {node.type === 'file' && node.color && (
          <span style={{
            marginRight: tokens.spacing[1],
            width: '8px',
            height: '8px',
            borderRadius: '2px',
            backgroundColor: node.color
          }}></span>
        )}
        <span style={{
          flex: 1,
          fontSize: '12px',
          color: tokens.color.structural.white,
          fontFamily: tokens.type.family.ui
        }}>
          {node.label}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
          }}
          style={{
            width: '16px',
            height: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'transparent',
            border: 'none',
            color: node.visible ? tokens.color.structural.white : tokens.color.structural.titanium[300],
            fontSize: '10px',
            cursor: 'pointer',
          }}
        >
          👁️
        </button>
      </div>
      {node.type === 'folder' && expanded && node.children && (
        <div>
          {node.children.map((child) => (
            <FieldRow
              key={child.id}
              node={child}
              level={level + 1}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
};

interface ResultsExplorerProps {
  onNodeSelect?: (nodeId: string) => void;
}

export const ResultsExplorer: React.FC<ResultsExplorerProps> = ({ onNodeSelect }) => {
  const [fields, setFields] = useState(fieldsData);
  const [clips, setClips] = useState(clipsData);
  const [scenes, setScenes] = useState(scenesData);

  const toggleField = (id: string) => {
    const updateVisibility = (nodes: FieldNode[]): FieldNode[] => nodes.map((node) => ({
      ...node,
      visible: node.id === id ? !node.visible : node.visible,
      children: node.children ? updateVisibility(node.children) : undefined,
    }));
    setFields((current) => updateVisibility(current));
    onNodeSelect?.(id);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#0C0D0F' }}>
      {/* Header */}
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
          RESULTS EXPLORER
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
          }}>🔄</button>
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

      {/* Case selector */}
      <div style={{ padding: tokens.spacing[2] + ' ' + tokens.spacing[3] }}>
        <div style={{ marginBottom: tokens.spacing[1] }}>
          <span style={{ fontSize: '10px', color: tokens.color.structural.titanium[300] }}>Case</span>
        </div>
        <div style={{
          padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
          backgroundColor: tokens.color.structural.titanium[700],
          border: '1px solid ' + tokens.color.structural.titanium[500],
          borderRadius: tokens.radius.sm,
          fontSize: '12px',
          color: tokens.color.structural.white,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <span>Pressure Drop Analysis</span>
          <span style={{ fontSize: '10px' }}>▼</span>
        </div>
      </div>

      {/* Search */}
      <div style={{ padding: '0 ' + tokens.spacing[3], marginBottom: tokens.spacing[2] }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
          backgroundColor: tokens.color.structural.titanium[700],
          border: '1px solid ' + tokens.color.structural.titanium[500],
          borderRadius: tokens.radius.sm,
        }}>
          <span style={{ marginRight: tokens.spacing[1], fontSize: '12px', color: tokens.color.structural.titanium[300] }}>🔍</span>
          <input
            type="text"
            placeholder="Search variables"
            style={{
              flex: 1,
              backgroundColor: 'transparent',
              border: 'none',
              color: tokens.color.structural.white,
              fontSize: '12px',
              fontFamily: tokens.type.family.ui,
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* FIELDS Section */}
      <div style={{ padding: '0 ' + tokens.spacing[3] }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: tokens.spacing[1],
        }}>
          <span style={{
            fontSize: '10px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: tokens.color.structural.titanium[300],
          }}>
            FIELDS
          </span>
          <button style={{
            width: '16px',
            height: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'transparent',
            border: 'none',
            color: tokens.color.structural.titanium[300],
            fontSize: '12px',
            cursor: 'pointer',
          }}>+</button>
        </div>
        <div style={{ maxHeight: '200px', overflow: 'auto' }}>
          {fields.map((node) => (
            <FieldRow
              key={node.id}
              node={node}
              level={0}
              onToggle={toggleField}
            />
          ))}
        </div>
      </div>

      {/* CLIPS Section */}
      <div style={{ padding: tokens.spacing[2] + ' ' + tokens.spacing[3] }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: tokens.spacing[1],
        }}>
          <span style={{
            fontSize: '10px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: tokens.color.structural.titanium[300],
          }}>
            CLIPS
          </span>
          <button style={{
            width: '16px',
            height: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'transparent',
            border: 'none',
            color: tokens.color.structural.titanium[300],
            fontSize: '12px',
            cursor: 'pointer',
          }}>+</button>
        </div>
        {clips.map((clip) => (
          <div
            key={clip.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
              marginBottom: tokens.spacing[1],
            }}
          >
            <span style={{ fontSize: '12px', color: tokens.color.structural.white }}>{clip.label}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[1] }}>
              {clip.hasSettings && (
                <button style={{
                  width: '16px',
                  height: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: 'transparent',
                  border: 'none',
                  color: tokens.color.structural.titanium[300],
                  fontSize: '10px',
                  cursor: 'pointer',
                }}>⚙️</button>
              )}
              {clip.hasToggle && (
                <button
                  type="button"
                  onClick={() => setClips((current) => current.map((item) => (
                    item.id === clip.id ? { ...item, toggleOn: !item.toggleOn } : item
                  )))}
                  style={{
                  width: '24px',
                  height: '14px',
                  borderRadius: '7px',
                  backgroundColor: clip.toggleOn ? '#2196F3' : tokens.color.structural.titanium[700],
                  position: 'relative',
                  cursor: 'pointer',
                  border: 'none',
                  padding: 0,
                }}>
                  <div style={{
                    width: '10px',
                    height: '10px',
                    borderRadius: '50%',
                    backgroundColor: tokens.color.structural.white,
                    position: 'absolute',
                    top: '2px',
                    left: clip.toggleOn ? '12px' : '2px',
                    transition: 'left 0.2s',
                  }}></div>
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* SCENES Section */}
      <div style={{ padding: tokens.spacing[2] + ' ' + tokens.spacing[3] }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: tokens.spacing[1],
        }}>
          <span style={{
            fontSize: '10px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: tokens.color.structural.titanium[300],
          }}>
            SCENES
          </span>
          <button style={{
            width: '16px',
            height: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'transparent',
            border: 'none',
            color: tokens.color.structural.titanium[300],
            fontSize: '12px',
            cursor: 'pointer',
          }}>+</button>
        </div>
        {scenes.map((scene) => (
          <button
            type="button"
            onClick={() => setScenes((current) => current.map((item) => ({
              ...item,
              selected: item.id === scene.id,
            })))}
            key={scene.id}
            style={{
              padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
              marginBottom: tokens.spacing[1],
              backgroundColor: scene.selected ? '#141418' : 'transparent',
              borderRadius: tokens.radius.sm,
              cursor: 'pointer',
              border: 'none',
              width: '100%',
              textAlign: 'left',
            }}
          >
            <span style={{ fontSize: '12px', color: tokens.color.structural.white }}>{scene.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

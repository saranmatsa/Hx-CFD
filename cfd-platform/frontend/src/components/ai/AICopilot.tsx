import React, { useState } from 'react';
import { tokens } from '../../tokens';

type CopilotMode = 'chat' | 'analysis' | 'optimization' | 'knowledge';

interface ModeConfig {
  id: CopilotMode;
  label: string;
  icon: string;
}

const modes: ModeConfig[] = [
  { id: 'chat', label: 'Chat', icon: '💬' },
  { id: 'analysis', label: 'Analysis', icon: '📊' },
  { id: 'optimization', label: 'Optimization', icon: '⚡' },
  { id: 'knowledge', label: 'Knowledge', icon: '📚' },
];

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const mockMessages: Message[] = [
  {
    id: '1',
    role: 'assistant',
    content: 'I\'ve analyzed your turbine simulation results. The velocity distribution shows good flow attachment across the blade surfaces, but I recommend refining the mesh in the tip clearance region to better capture the secondary flows.',
    timestamp: new Date(),
  },
  {
    id: '2',
    role: 'user',
    content: 'What about the pressure drop across the turbine?',
    timestamp: new Date(),
  },
  {
    id: '3',
    role: 'assistant',
    content: 'The pressure drop is within expected ranges for this geometry. The current value of 475 Pa indicates efficient energy extraction. However, you could potentially improve this by adjusting the blade pitch angle by 2-3 degrees.',
    timestamp: new Date(),
  },
];

interface QuickAction {
  id: string;
  label: string;
}

const quickActions: QuickAction[] = [
  { id: '1', label: 'Show regions' },
  { id: '2', label: 'Explain in detail' },
  { id: '3', label: 'Suggest improvements' },
  { id: '4', label: 'Compare with baseline' },
];

interface AICopilotProps {
  width?: string;
  height?: string;
}

export const AICopilot: React.FC<AICopilotProps> = ({ width = '350px', height = '100%' }) => {
  const [activeMode, setActiveMode] = useState<CopilotMode>('chat');
  const [messages, setMessages] = useState<Message[]>(mockMessages);
  const [inputValue, setInputValue] = useState('');

  const handleSendMessage = () => {
    if (inputValue.trim()) {
      const newMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: inputValue,
        timestamp: new Date(),
      };
      setMessages([...messages, newMessage]);
      setInputValue('');

      // Simulate AI response
      setTimeout(() => {
        const aiResponse: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'I\'m analyzing your request. Based on the current simulation state, I recommend focusing on the boundary layer resolution near the leading edge.',
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, aiResponse]);
      }, 1000);
    }
  };

  return (
    <div
      style={{
        width,
        height,
        backgroundColor: tokens.color.structural.titanium[900],
        border: '1px solid ' + tokens.color.structural.titanium[500],
        borderRadius: tokens.radius.md,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        boxShadow: tokens.elevation[1],
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
          borderBottom: '1px solid ' + tokens.color.structural.titanium[500],
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
          AI COPILOT
        </span>
        <div style={{ display: 'flex', gap: tokens.spacing[1] }}>
          <button
            style={{
              width: '24px',
              height: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              borderRadius: tokens.radius.sm,
              color: tokens.color.structural.titanium[300],
              fontSize: '12px',
              cursor: 'pointer',
              transition: 'all ' + tokens.motion.duration.instant + ' ' + tokens.motion.easing.standard,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = tokens.color.structural.titanium[700];
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            📌
          </button>
          <button
            style={{
              width: '24px',
              height: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              borderRadius: tokens.radius.sm,
              color: tokens.color.structural.titanium[300],
              fontSize: '12px',
              cursor: 'pointer',
              transition: 'all ' + tokens.motion.duration.instant + ' ' + tokens.motion.easing.standard,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = tokens.color.structural.titanium[700];
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            ⛶
          </button>
        </div>
      </div>

      {/* Mode Tabs */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid ' + tokens.color.structural.titanium[500],
        }}
      >
        {modes.map((mode) => (
          <button
            key={mode.id}
            onClick={() => setActiveMode(mode.id)}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: tokens.spacing[1],
              padding: tokens.spacing[2] + ' ' + tokens.spacing[3],
              backgroundColor: activeMode === mode.id ? tokens.color.structural.titanium[700] : 'transparent',
              border: 'none',
              borderBottom: activeMode === mode.id ? '2px solid ' + tokens.color.structural.white : 'none',
              color: activeMode === mode.id ? tokens.color.structural.white : tokens.color.structural.titanium[300],
              fontSize: '11px',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all ' + tokens.motion.duration.instant + ' ' + tokens.motion.easing.standard,
              fontFamily: tokens.type.family.ui,
            }}
            onMouseEnter={(e) => {
              if (activeMode !== mode.id) {
                e.currentTarget.style.backgroundColor = tokens.color.structural.titanium[700];
              }
            }}
            onMouseLeave={(e) => {
              if (activeMode !== mode.id) {
                e.currentTarget.style.backgroundColor = 'transparent';
              }
            }}
          >
            <span>{mode.icon}</span>
            <span>{mode.label}</span>
          </button>
        ))}
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflow: 'auto',
          padding: tokens.spacing[3],
          display: 'flex',
          flexDirection: 'column',
          gap: tokens.spacing[3],
        }}
      >
        {messages.map((message) => (
          <div
            key={message.id}
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: tokens.spacing[1],
              ...(message.role === 'user' ? {
                alignItems: 'flex-end',
              } : {
                alignItems: 'flex-start',
              }),
            }}
          >
            <div
              style={{
                maxWidth: '85%',
                padding: tokens.spacing[2],
                borderRadius: tokens.radius.sm,
                backgroundColor: message.role === 'user'
                  ? tokens.color.structural.titanium[700]
                  : tokens.color.structural.titanium[500],
                color: tokens.color.structural.white,
                fontSize: '13px',
                lineHeight: 1.5,
                fontFamily: tokens.type.family.ui,
              }}
            >
              {message.content}
            </div>
            {message.role === 'assistant' && (
              <div style={{ display: 'flex', gap: tokens.spacing[1], flexWrap: 'wrap' }}>
                {quickActions.map((action) => (
                  <button
                    key={action.id}
                    style={{
                      padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
                      backgroundColor: 'transparent',
                      border: '1px solid ' + tokens.color.structural.titanium[500],
                      borderRadius: tokens.radius.sm,
                      color: tokens.color.structural.titanium[300],
                      fontSize: '11px',
                      cursor: 'pointer',
                      transition: 'all ' + tokens.motion.duration.instant + ' ' + tokens.motion.easing.standard,
                      fontFamily: tokens.type.family.ui,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = tokens.color.structural.titanium[700];
                      e.currentTarget.style.color = tokens.color.structural.white;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                      e.currentTarget.style.color = tokens.color.structural.titanium[300];
                    }}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Input */}
      <div
        style={{
          padding: tokens.spacing[3],
          borderTop: '1px solid ' + tokens.color.structural.titanium[500],
        }}
      >
        <div style={{ display: 'flex', gap: tokens.spacing[2] }}>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleSendMessage();
              }
            }}
            placeholder="Ask about your simulation..."
            style={{
              flex: 1,
              padding: tokens.spacing[2] + ' ' + tokens.spacing[3],
              backgroundColor: tokens.color.structural.titanium[700],
              border: '1px solid ' + tokens.color.structural.titanium[500],
              borderRadius: tokens.radius.sm,
              color: tokens.color.structural.white,
              fontSize: '13px',
              fontFamily: tokens.type.family.ui,
              outline: 'none',
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = tokens.color.structural.titanium[300];
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = tokens.color.structural.titanium[500];
            }}
          />
          <button
            onClick={handleSendMessage}
            style={{
              padding: tokens.spacing[2] + ' ' + tokens.spacing[3],
              backgroundColor: tokens.color.structural.titanium[700],
              border: '1px solid ' + tokens.color.structural.titanium[500],
              borderRadius: tokens.radius.sm,
              color: tokens.color.structural.white,
              fontSize: '13px',
              cursor: 'pointer',
              transition: 'all ' + tokens.motion.duration.instant + ' ' + tokens.motion.easing.standard,
              fontFamily: tokens.type.family.ui,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = tokens.color.structural.titanium[500];
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = tokens.color.structural.titanium[700];
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

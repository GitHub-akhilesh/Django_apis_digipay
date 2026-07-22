import React, { useState } from 'react';
import { ChatProvider } from '../context/ChatContext';
import { useChat, useMessages } from '../hooks/useChat';

export interface DigiPayChatWidgetProps {
  cscId?: string;
  baseUrl?: string;
  username?: string;
  position?: 'bottom-right' | 'bottom-left';
  mode?: 'floating' | 'inline' | 'sidebar';
}

const InnerWidget: React.FC<{ mode: 'floating' | 'inline' | 'sidebar' }> = ({ mode }) => {
  const [isOpen, setIsOpen] = useState(mode !== 'floating');
  const [input, setInput] = useState('');
  const messages = useMessages();
  const { sendMessage, seedTestData, isTyping, isEscalated } = useChat();

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim()) return;
    const text = input;
    setInput('');
    await sendMessage(text);
  };

  if (mode === 'floating' && !isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          width: 60,
          height: 60,
          borderRadius: '50%',
          background: '#2563eb',
          color: '#fff',
          border: 'none',
          cursor: 'pointer',
          boxShadow: '0 8px 24px rgba(37,99,235,0.4)',
          fontSize: 24,
          zIndex: 99999
        }}
      >
        💬
      </button>
    );
  }

  return (
    <div
      style={{
        width: mode === 'inline' ? '100%' : 380,
        height: mode === 'sidebar' ? '100vh' : 560,
        background: '#0f172a',
        color: '#f8fafc',
        borderRadius: mode === 'inline' ? 12 : 20,
        display: 'flex',
        flexDirection: 'column',
        boxShadow: mode === 'floating' ? '0 20px 50px rgba(0,0,0,0.5)' : 'none',
        border: '1px solid rgba(255,255,255,0.1)',
        position: mode === 'floating' ? 'fixed' : 'relative',
        bottom: mode === 'floating' ? 96 : undefined,
        right: mode === 'floating' ? 24 : undefined,
        zIndex: 99998
      }}
    >
      <div style={{ padding: '16px 20px', background: '#1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h4 style={{ margin: 0, fontSize: 16 }}>DigiPay AI Assistant</h4>
        {mode === 'floating' && (
          <button onClick={() => setIsOpen(false)} style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: 20, cursor: 'pointer' }}>
            &times;
          </button>
        )}
      </div>

      <div style={{ flex: 1, padding: 16, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              background: m.role === 'user' ? '#2563eb' : '#1e293b',
              color: '#fff',
              padding: '10px 14px',
              borderRadius: 12,
              maxWidth: '85%',
              fontSize: 14
            }}
          >
            {m.content}
            {m.escalate && <div style={{ fontSize: 11, color: '#fdba74', marginTop: 4 }}>⚠️ Escalated to Support</div>}
          </div>
        ))}
        {isTyping && <div style={{ fontSize: 12, color: '#94a3b8' }}>Assistant is typing...</div>}
        {isEscalated && <div style={{ fontSize: 12, color: '#fb923c' }}>Human agent notified.</div>}
      </div>

      <form onSubmit={handleSend} style={{ padding: 12, background: '#0f172a', display: 'flex', gap: 8, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          style={{ flex: 1, background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: 8, padding: '8px 12px', fontSize: 14 }}
        />
        <button type="submit" style={{ background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer' }}>
          Send
        </button>
      </form>
    </div>
  );
};

export const DigiPayChatWidget: React.FC<DigiPayChatWidgetProps> = ({
  cscId = '500100100014',
  baseUrl = 'http://127.0.0.1:8000',
  username = 'merchant_admin',
  mode = 'floating'
}) => {
  return (
    <ChatProvider cscId={cscId} baseUrl={baseUrl} username={username}>
      <InnerWidget mode={mode} />
    </ChatProvider>
  );
};

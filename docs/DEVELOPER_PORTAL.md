# DigiPay Developer Portal & DX Documentation

Welcome to the official developer portal documentation for **DigiPay AI Chat Agent & SDK Ecosystem**.

---

## ⚡ Quick Start

### 1. Web Component (Plain HTML / Vue / Angular / Svelte)

Drop the script tags into your page and declare `<digipay-chat>`:

```html
<script src="digipay-chat-sdk.js"></script>
<script src="digipay-chat-widget.js"></script>

<!-- Floating Mode (Default) -->
<digipay-chat csc-id="500100100014" mode="floating"></digipay-chat>

<!-- Inline Mode -->
<digipay-chat csc-id="500100100014" mode="inline"></digipay-chat>

<!-- Sidebar Mode -->
<digipay-chat csc-id="500100100014" mode="sidebar"></digipay-chat>
```

---

### 2. React / Next.js Integration (`@digipay/chat-react`)

Install `@digipay/chat-core` and `@digipay/chat-react`:

```tsx
import React from 'react';
import { DigiPayChatWidget } from '@digipay/chat-react';

export default function Dashboard() {
  return (
    <div>
      <h1>Merchant Portal</h1>

      {/* Drop-in Widget Component */}
      <DigiPayChatWidget 
        cscId="500100100014" 
        baseUrl="http://127.0.0.1:8000" 
        mode="floating"
      />
    </div>
  );
}
```

#### Custom React Hooks Integration
```tsx
import { ChatProvider, useChat, useMessages } from '@digipay/chat-react';

function CustomChatScreen() {
  const messages = useMessages();
  const { sendMessage, isTyping } = useChat();

  return (
    <div>
      {messages.map((m, i) => (
        <p key={i}><strong>{m.role}:</strong> {m.content}</p>
      ))}
      {isTyping && <span>Agent typing...</span>}
      <button onClick={() => sendMessage("Check my wallet balance")}>Check Balance</button>
    </div>
  );
}

export default function App() {
  return (
    <ChatProvider cscId="500100100014">
      <CustomChatScreen />
    </ChatProvider>
  );
}
```

---

## 📦 Package Ecosystem Architecture

| Package | Language | Target Audience / Usage |
| :--- | :--- | :--- |
| **`@digipay/chat-core`** | TypeScript | Framework-agnostic core SDK (Auth, Transport, Storage, Plugins, Event Bus) |
| **`@digipay/chat-react`** | React / TSX | Context provider (`ChatProvider`), Hooks (`useChat`), and React UI widgets |
| **`@digipay/chat-widget`** | HTML5 / JS | Universal custom element (`<digipay-chat mode="...">`) |

---

## ⚙️ Custom Theme Engine Configuration

```typescript
const client = new ChatClient({
  baseUrl: 'http://127.0.0.1:8000',
  cscId: '500100100014',
  theme: {
    mode: 'dark',
    primaryColor: '#2563eb',
    backgroundColor: '#0f172a',
    borderRadius: 16,
    fontFamily: 'Inter, sans-serif'
  }
});
```

---

## 🔌 Plugin System & Event Bus

```typescript
import { ChatClient, loggerMiddleware, markdownPlugin, analyticsPlugin } from '@digipay/chat-core';

const client = new ChatClient({
  baseUrl: 'http://127.0.0.1:8000',
  plugins: [
    markdownPlugin(),
    analyticsPlugin((event, data) => console.log('Analytics Event:', event, data))
  ]
});

// Intercept HTTP requests with Middleware Pipeline
client.use(loggerMiddleware());

// Subscribe to typed events
client.on('message', (msg) => console.log('Message:', msg));
client.on('escalate', (msg) => console.log('Human Escalation Requested:', msg));
```

# DigiPay Chat SDK — React + Vite Starter Example

Quickly integrate the `@digipay/chat-react` SDK component into a React + Vite application.

## Quickstart

```tsx
import React from 'react';
import { DigiPayChatWidget } from '@digipay/chat-react';

export default function MerchantDashboard() {
  return (
    <div style={{ padding: 40, fontFamily: 'sans-serif' }}>
      <h1>DigiPay Merchant Portal</h1>
      <p>Welcome back! Use the AI assistant below for balance and transaction support.</p>

      {/* Embed DigiPay Chat AI Assistant */}
      <DigiPayChatWidget 
        cscId="500100100014" 
        mode="floating" 
        theme="dark" 
      />
    </div>
  );
}
```

## Running Locally

```bash
npm install
npm run dev
```

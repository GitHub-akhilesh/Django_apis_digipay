# DigiPay Chat SDK — React + Vite Starter Example

> **For a working integration, see [`../react/README.md`](../react/README.md).**
> The `@digipay/chat-react` package below is not published, so `npm install`
> will fail. The shipped integration copies `sdk/digipay-chat-sdk.js` and
> `sdk/digipay-chat-widget.js` into `public/js` and proxies the backend — that
> README covers it, including the CORS and mixed-content reasons for the proxy.
> This file is kept as the intended package API for when it is published.

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

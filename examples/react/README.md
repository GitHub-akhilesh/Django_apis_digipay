# DigiPay Chat — React integration

Two ways in. Both use the same two files; there is no npm package to install.

## 1. Copy the SDK into your app

```bash
cp sdk/digipay-chat-sdk.js sdk/digipay-chat-widget.js \
   your-react-app/public/js/
```

Serving them from your own `public/js` means the version in the browser is the
one in your repo. The backend also serves them at `http://<host>/sdk/…`
(`app/main.py` mounts `/sdk`) if you would rather load them from there — but a
page served over https cannot load them over http, so prefer local copies.

## 2. Proxy the chat backend — do not call it cross-origin

Add this to `vite.config.js`. It must come **before** any `/api/v1` rule:
both the legacy API and the chat platform expose `/api/v1/chat`, so without a
distinct prefix the chat call lands on the wrong service.

```js
server: {
  proxy: {
    '/ai-platform': {
      target: process.env.VITE_AI_PLATFORM_URL || 'http://10.1.76.194:8001',
      changeOrigin: true,
      secure: false,
      rewrite: (p) => p.replace(/^\/ai-platform/, ''),
    },
    // …your existing rules
  },
}
```

```dotenv
# .env
VITE_AI_PLATFORM_URL=http://10.1.76.194:8001
```

Going through the proxy is not cosmetic. The SDK sends `credentials: 'include'`,
and a browser **rejects** a credentialed response whose
`Access-Control-Allow-Origin` is `*` — which is what the platform is configured
with. A relative path also keeps working once your app is served over https,
where a direct `http://…:8001` call would be blocked as mixed content.

Restart the dev server after this. Vite does not reliably hot-reload proxy or
`.env` changes, and the symptom is a chat reply saying it reached the app but
not the assistant.

## 3a. Component (recommended)

```jsx
import DigiPayChat from './DigiPayChat';

export default function App() {
  return (
    <>
      <AppRoutes />
      <DigiPayChat
        apiMode="ai-platform"
        apiUrl="/ai-platform"
        cscId="523816200013"
        userName="Akhilesh"
        mode="floating"
        theme="dark"
      />
    </>
  );
}
```

Use this over the custom element in a React app: `initDigiPayChat()` appends a
fresh widget on every call, so React 18 StrictMode (which double-invokes effects
in development) and Vite hot reload would otherwise leave you with two launchers
stacked up. The component clears its host on cleanup.

## 3b. Custom element (fine for a static page)

```html
<!-- index.html -->
<script src="/js/digipay-chat-sdk.js"></script>
<script src="/js/digipay-chat-widget.js"></script>
```

```jsx
<digipay-chat
  csc-id="523816200013"
  api-mode="ai-platform"
  api-url="/ai-platform"
  token-storage-key="authToken"
  mode="floating"
  theme="dark"
></digipay-chat>
```

## Authentication

The widget reads the DigiPay JWT from `localStorage["authToken"]` (override with
`tokenStorageKey`, or pass `token` directly) and sends it as
`Authorization: Bearer …`, plus cookies, so a DigiPay `access_token` session
cookie reaches the gateway.

The platform derives the CSC ID **from the token**, not from the `cscId` prop —
that prop is a display/legacy-mode hint only. Two consequences:

* A reply of *"Your DigiPay session has expired"* is correct behaviour for a
  token the gateway does not recognise, not an outage. Gateway-backed answers
  need a real DigiPay session; legacy-backed ones ("what is my legacy wallet
  balance") work with any token the platform can verify.
* For local testing you can mint a token the platform accepts, via the existing
  `/api/v1` proxy:

```js
fetch('/api/v1/auth/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'test', cscId: '523816200013' }),
})
  .then((r) => r.json())
  .then((d) => localStorage.setItem('authToken', d.access_token));
```

Then reload and ask *"what is my legacy wallet balance"*.

## Props

| Prop | Default | Notes |
|---|---|---|
| `apiUrl` | `/ai-platform` | keep it relative so the call is same-origin |
| `apiMode` | `ai-platform` | `ai-platform` → `:8001`; `legacy` → `:8000` |
| `cscId` | — | display hint; real identity comes from the JWT |
| `userName` | — | greeting stays "Namaste!" when omitted |
| `rewards` | — | `{ streakDays, coins, level, xpPercent, note }`; the strip is hidden entirely without it |
| `mode` | `floating` | `floating` \| `sidebar` \| `inline` |
| `tokenStorageKey` | `authToken` | localStorage key holding the JWT |
| `token` | — | pass the JWT directly instead |
| `voiceLang` | `en-IN` | one of 13 Indian languages; remembered per browser |

`rewards` renders only what you pass. There is no endpoint for streaks or coins,
and showing invented figures beside real balances would make the real ones
untrustworthy — so with no data the strip stays hidden rather than defaulting.

## Voice

Uses the browser's Web Speech API, so no audio leaves the device. Speech
**recognition** requires a secure context: `https://` or `http://localhost`, not
a plain `http://` LAN address. Where it is unavailable the mic button is hidden
rather than left dead.

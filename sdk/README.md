# DigiPay AI Agent Chat SDK & Web Component Widget

The DigiPay Chat SDK provides high-performance, resilient integration for embedding AI Agent support into merchant web portals and enterprise applications.

---

## Architecture Flow

```
+-------------------+        +----------------------+        +------------------------+
|   DigiPay SDK     |  --->  |  Web Component Widget|  --->  |   Merchant Dashboard   |
| (digipay-chat-sdk)|        | (digipay-chat-widget)|        |  (index.html / Demo)  |
+-------------------+        +----------------------+        +------------------------+
```

1. **SDK (`sdk/digipay-chat-sdk.js`)**:
   - Manages connection lifecycle, token authentication (`/api/v1/auth/token`), SSE streaming, session caching, and fallback polling.
2. **Widget (`sdk/digipay-chat-widget.js`)**:
   - Custom HTML5 Web Component (`<digipay-chat>`) rendering floating chat UI, dark/light themes, real-time message history, and quick action prompts.
3. **Demo Integrations (`sdk/examples/` / `index.js`)**:
   - Production demonstration incorporating embedded custom element:
     ```html
     <script src="/js/digipay-chat-sdk.js"></script>
     <script src="/js/digipay-chat-widget.js"></script>

     <digipay-chat
       csc-id="500100100014"
       api-url="http://localhost:8000"
       mode="floating"
       theme="dark"
     ></digipay-chat>
     ```

---

## Features
- 🚀 Zero-dependency vanilla Web Component architecture (<15KB minified SDK, <30KB Widget).
- 🔒 Secure JWT authentication and PII masking.
- 🎨 Modern Glassmorphism dark/light theme presets.
- ⚡ Resilient auto-retry with exponential backoff.

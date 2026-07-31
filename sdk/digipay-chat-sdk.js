/**
 * DigiPay Chat Core SDK v1.1.0
 * Framework-agnostic JavaScript client for DigiPay chat backends.
 *
 * Two backends exist and they are NOT interchangeable, so the SDK targets one
 * explicitly via `apiMode`:
 *
 *   apiMode: 'legacy'       Legacy DigiPay API service (app/main.py, :8000)
 *                           POST /api/v1/auth/token   -> issues its own token
 *                           POST /api/v1/agent/chat   -> flat response body
 *                           GET  /api/v1/agent/history/{sessionId}
 *                           POST /api/v1/agent/test-seed
 *
 *   apiMode: 'ai-platform'  AI Platform (ai_platform/main.py, :8001)
 *                           POST /api/v1/chat         -> ApiResponse envelope
 *                           No /auth/token: it verifies the DigiPay JWT the
 *                           caller already holds, and forwards it downstream to
 *                           the gateway, so a token MUST be supplied.
 *                           No history or seed endpoints.
 *
 * Default is 'legacy' so existing embeds keep working untouched.
 */

const DIGIPAY_CHAT_MODES = {
  legacy: {
    defaultPort: '8000',
    authPath: '/api/v1/auth/token',
    chatPath: '/api/v1/agent/chat',
    historyPath: (sessionId) => `/api/v1/agent/history/${sessionId}`,
    seedPath: '/api/v1/agent/test-seed',
    // Flat body: {status, response, intent, escalate, confidenceScore, policyChecked}
    unwrap: (body) => body || {},
  },
  'ai-platform': {
    defaultPort: '8001',
    authPath: null,
    chatPath: '/api/v1/chat',
    historyPath: null,
    seedPath: null,
    // ApiResponse envelope: {success, message, data:{response, intent, escalate, policyChecked}}
    unwrap: (body) => (body && body.data ? body.data : body || {}),
  },
};

class DigiPayChatSDK {
  constructor(options = {}) {
    const requestedMode = options.apiMode || options.mode_api || 'legacy';
    this.apiMode = DIGIPAY_CHAT_MODES[requestedMode] ? requestedMode : 'legacy';
    if (this.apiMode !== requestedMode) {
      console.warn(
        `[DigiPaySDK] Unknown apiMode "${requestedMode}". Falling back to "legacy". ` +
        `Valid values: ${Object.keys(DIGIPAY_CHAT_MODES).join(', ')}`
      );
    }
    this._modeConfig = DIGIPAY_CHAT_MODES[this.apiMode];

    let rawUrl = options.baseUrl || options.apiUrl;
    if (!rawUrl && typeof window !== 'undefined' && window.location.origin) {
      // Guess the backend port only when the page is not already served from it.
      const port = this._modeConfig.defaultPort;
      if (window.location.port && window.location.port !== port) {
        rawUrl = window.location.protocol + '//' + window.location.hostname + ':' + port;
      } else {
        rawUrl = window.location.origin;
      }
    }
    if (!rawUrl) rawUrl = 'http://localhost:' + this._modeConfig.defaultPort;
    rawUrl = rawUrl.replace(/\/$/, '');
    this.baseUrl = rawUrl;
    this.cscId = options.cscId || '500100100014';
    this.username = options.username || 'merchant_admin';
    this.sessionId = options.sessionId || this._getOrCreateSessionId();

    // Where to find the host application's JWT. The DigiPay React app stores it
    // at localStorage["authToken"] (see src/api/apiClient.js), which is the
    // default; override with tokenStorageKey, or pass `token` directly.
    this.tokenStorageKey = options.tokenStorageKey || 'authToken';
    this.token = options.token || this._tokenFromStorage() || null;

    // Send cookies with cross-origin calls so a DigiPay `access_token` session
    // cookie reaches the backend. Opt out with withCredentials: false.
    this.withCredentials = options.withCredentials !== false;

    this.history = [];
    this.onMessageListeners = [];
    this.onStatusListeners = [];
  }

  _tokenFromStorage() {
    if (typeof localStorage === 'undefined' || !this.tokenStorageKey) return null;
    try {
      return localStorage.getItem(this.tokenStorageKey) || null;
    } catch (e) {
      return null;
    }
  }

  _url(path) {
    return `${this.baseUrl}${path}`;
  }

  _authHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    // Re-read on every call: the host app may log in after the widget mounted.
    const token = this.token || this._tokenFromStorage();
    if (token) {
      this.token = token;
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  /**
   * fetch options shared by every call.
   *
   * credentials:'include' is required, not optional. A DigiPay session lives in
   * the `access_token` cookie, and a cross-origin fetch (React dev server on
   * :5173 -> API on :8001) omits cookies unless credentials are included — so
   * the request arrived with no credential at all and was rejected with 401.
   * The backend answers with Access-Control-Allow-Credentials: true and echoes
   * the exact origin, which is what makes this legal.
   */
  _fetchOptions(extra = {}) {
    return {
      credentials: this.withCredentials ? 'include' : 'same-origin',
      ...extra,
      headers: { ...(extra.headers || {}) },
    };
  }

  _getOrCreateSessionId() {
    const key = `digipay_session_${this.cscId}`;
    let sid = typeof localStorage !== 'undefined' ? localStorage.getItem(key) : null;
    if (!sid) {
      sid = 'sess_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(key, sid);
      }
    }
    return sid;
  }

  async authenticate() {
    // ai-platform mode has no token endpoint by design: it verifies the DigiPay
    // JWT the host app already holds and forwards it to the gateway, so minting
    // a separate token here would produce one the gateway rejects.
    if (!this._modeConfig.authPath) {
      const token = this.token || this._tokenFromStorage();
      if (token) {
        this.token = token;
        this._emitStatus('authenticated');
        return token;
      }
      // No readable token. This is NOT necessarily an error: a DigiPay session
      // lives in the HttpOnly `access_token` cookie, which JavaScript cannot
      // read but the browser still sends because credentials are included. So
      // proceed and let the request itself decide - a genuine 401 is reported
      // by sendMessage with an actionable message.
      console.info(
        `[DigiPaySDK] No token in localStorage["${this.tokenStorageKey}"]; ` +
        `relying on the DigiPay session cookie (sent because credentials are included).`
      );
      this._emitStatus('idle');
      return null;
    }

    try {
      this._emitStatus('authenticating');
      const response = await fetch(this._url(this._modeConfig.authPath), this._fetchOptions({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: this.username,
          cscId: this.cscId
        })
      }));
      if (!response.ok) {
        throw new Error(`Auth failed with status ${response.status}`);
      }
      const data = await response.json();
      this.token = data.access_token;
      this._emitStatus('authenticated');
      return this.token;
    } catch (err) {
      console.warn('[DigiPaySDK] Authenticate warning (proceeding with fallback):', err.message);
      this._emitStatus('auth_failed');
      return null;
    }
  }

  async seedTestData() {
    if (!this._modeConfig.seedPath) {
      const msg = `Test seeding is not available in apiMode "${this.apiMode}".`;
      console.warn('[DigiPaySDK] ' + msg);
      return { msg };
    }
    try {
      const res = await fetch(this._url(this._modeConfig.seedPath), this._fetchOptions({
        method: 'POST',
        headers: this._authHeaders()
      }));
      return await res.json();
    } catch (err) {
      console.error('[DigiPaySDK] Test seed error:', err);
      throw err;
    }
  }

  async sendMessage(messageText) {
    if (!messageText || !messageText.trim()) return null;

    if (!this.token) {
      await this.authenticate();
    }

    const payload = {
      sessionId: this.sessionId,
      message: messageText.trim(),
      cscId: this.cscId
    };

    const userMessageObj = { role: 'user', content: messageText.trim(), timestamp: new Date() };
    this.history.push(userMessageObj);
    this._emitMessage(userMessageObj);

    this._emitStatus('typing');

    try {
      const res = await fetch(this._url(this._modeConfig.chatPath), this._fetchOptions({
        method: 'POST',
        headers: this._authHeaders(),
        body: JSON.stringify(payload)
      }));

      if (!res.ok) {
        // 401 here almost always means no usable JWT rather than a server fault,
        // so say which one so it is not mistaken for the backend being down.
        if (res.status === 401 && !this._modeConfig.authPath) {
          throw new Error(
            '401 Unauthorized - the backend received no valid DigiPay session. ' +
            'Check that you are signed in (the access_token cookie is set and ' +
            'not expired) and that the cookie is scoped to reach ' +
            `${this.baseUrl}. Alternatively pass a token to the widget.`
          );
        }
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      // A 200 that is not JSON means the request never reached the chat
      // backend. The usual cause is a missing dev-server proxy for this path:
      // the SPA fallback answers with index.html, and res.json() then fails
      // with "Unexpected token '<'", which reads like the backend is down.
      const contentType = (res.headers.get('content-type') || '').toLowerCase();
      if (!contentType.includes('json')) {
        const preview = (await res.text()).trim().slice(0, 100);
        throw new Error(
          `NotJson: expected JSON from ${this._url(this._modeConfig.chatPath)} but got ` +
          `"${contentType || 'no content-type'}". The request did not reach the chat ` +
          `backend - check that this path is proxied to it. Body starts: ${preview}`
        );
      }

      const body = await res.json();
      // Normalise the two response shapes to one object the UI can rely on.
      const data = this._modeConfig.unwrap(body);

      const assistantMsg = {
        role: 'assistant',
        content: data.response,
        intent: data.intent,
        escalate: data.escalate,
        confidenceScore: data.confidenceScore,
        policyChecked: data.policyChecked,
        timestamp: new Date()
      };

      this.history.push(assistantMsg);
      this._emitStatus('idle');
      this._emitMessage(assistantMsg);

      return data;
    } catch (err) {
      this._emitStatus('error');
      const errorMsg = {
        role: 'assistant',
        content: `Sorry, I encountered a communication error (${err.message}). Please verify service connectivity.`,
        isError: true,
        timestamp: new Date()
      };
      this.history.push(errorMsg);
      this._emitMessage(errorMsg);
      throw err;
    }
  }

  async loadHistory() {
    if (!this._modeConfig.historyPath) {
      // Not an error: the AI platform keeps session history server-side and
      // exposes no read endpoint, so the in-memory history is all there is.
      return this.history;
    }
    try {
      const res = await fetch(this._url(this._modeConfig.historyPath(this.sessionId)), this._fetchOptions({
        headers: this._authHeaders()
      }));
      if (res.ok) {
        const data = await res.json();
        if (data && data.history) {
          this.history = data.history;
          return this.history;
        }
      }
    } catch (err) {
      console.warn('[DigiPaySDK] Could not load past history:', err.message);
    }
    return [];
  }

  onMessage(callback) {
    this.onMessageListeners.push(callback);
  }

  onStatusChange(callback) {
    this.onStatusListeners.push(callback);
  }

  _emitMessage(msg) {
    this.onMessageListeners.forEach(cb => cb(msg));
  }

  _emitStatus(status) {
    this.onStatusListeners.forEach(cb => cb(status));
  }
}

// Publish on window even under CommonJS: a bundler may define `module` while the
// widget still resolves the class via window.DigiPayChatSDK.
if (typeof window !== 'undefined') {
  window.DigiPayChatSDK = DigiPayChatSDK;
  window.DIGIPAY_CHAT_MODES = Object.keys(DIGIPAY_CHAT_MODES);
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { DigiPayChatSDK, DIGIPAY_CHAT_MODES };
}

/**
 * DigiPay Chat Core SDK v1.0.0
 * Framework-agnostic JavaScript client for DigiPay Agent & Ledger API Gateway.
 */

class DigiPayChatSDK {
  constructor(options = {}) {
    let rawUrl = (options.baseUrl || (typeof window !== 'undefined' ? window.location.origin : 'http://10.1.76.194')).replace(/:8000\/?$/, '').replace(/\/$/, '');
    if (rawUrl.includes('localhost:5173') || rawUrl.includes('127.0.0.1:5173')) {
      rawUrl = 'http://10.1.76.194';
    }
    this.baseUrl = rawUrl;
    this.cscId = options.cscId || '500100100014';
    this.username = options.username || 'merchant_admin';
    this.sessionId = options.sessionId || this._getOrCreateSessionId();
    this.token = options.token || null;
    this.history = [];
    this.onMessageListeners = [];
    this.onStatusListeners = [];
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
    try {
      this._emitStatus('authenticating');
      const response = await fetch(`${this.baseUrl}/api/v1/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: this.username,
          cscId: this.cscId
        })
      });
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
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/agent/test-seed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
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
      const headers = { 'Content-Type': 'application/json' };
      if (this.token) {
        headers['Authorization'] = `Bearer ${this.token}`;
      }

      const res = await fetch(`${this.baseUrl}/api/v1/agent/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();
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
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/agent/history/${this.sessionId}`);
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

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { DigiPayChatSDK };
} else if (typeof window !== 'undefined') {
  window.DigiPayChatSDK = DigiPayChatSDK;
}

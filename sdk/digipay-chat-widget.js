/**
 * DigiPay Chat UI Widget Component v2.0.0
 * Zero-dependency drop-in chat widget for Web, React, Vue, Angular, and HTML apps.
 * Supports Layout Modes: mode="floating" | mode="sidebar" | mode="inline"
 */

(function () {
  const styles = `
    .digipay-chat-launcher {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      box-shadow: 0 8px 24px rgba(37, 99, 235, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      z-index: 99999;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      border: none;
      outline: none;
    }
    .digipay-chat-launcher:hover {
      transform: scale(1.08);
      box-shadow: 0 12px 32px rgba(37, 99, 235, 0.5);
    }
    .digipay-chat-launcher svg {
      width: 28px;
      height: 28px;
      fill: #ffffff;
    }
    .digipay-chat-window {
      background: #0f172a;
      color: #f8fafc;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.1);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      z-index: 99998;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      transition: all 0.3s ease;
    }
    .digipay-chat-window.floating {
      position: fixed;
      bottom: 96px;
      right: 24px;
      width: 380px;
      max-width: calc(100vw - 32px);
      height: 580px;
      max-height: calc(100vh - 120px);
      border-radius: 20px;
      opacity: 0;
      pointer-events: none;
      transform: translateY(20px) scale(0.95);
    }
    .digipay-chat-window.floating.open {
      opacity: 1;
      pointer-events: auto;
      transform: translateY(0) scale(1);
    }
    .digipay-chat-window.sidebar {
      position: fixed;
      top: 0;
      right: 0;
      width: 400px;
      max-width: 100vw;
      height: 100vh;
      border-radius: 0;
      box-shadow: -10px 0 40px rgba(0,0,0,0.5);
    }
    .digipay-chat-window.inline {
      position: relative;
      width: 100%;
      height: 520px;
      border-radius: 16px;
    }
    .digipay-chat-header {
      padding: 16px 20px;
      background: linear-gradient(135deg, #1e293b, #0f172a);
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .digipay-chat-header-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .digipay-avatar {
      width: 38px;
      height: 38px;
      border-radius: 50%;
      background: #2563eb;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      color: #fff;
    }
    .digipay-title {
      font-weight: 600;
      font-size: 15px;
      margin: 0;
    }
    .digipay-subtitle {
      font-size: 12px;
      color: #94a3b8;
      margin: 2px 0 0 0;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .digipay-online-dot {
      width: 8px;
      height: 8px;
      background: #22c55e;
      border-radius: 50%;
    }
    .digipay-close-btn {
      background: transparent;
      border: none;
      color: #94a3b8;
      cursor: pointer;
      font-size: 20px;
      padding: 4px;
    }
    .digipay-close-btn:hover { color: #fff; }
    .digipay-chat-body {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .digipay-msg-bubble {
      max-width: 82%;
      padding: 12px 16px;
      border-radius: 16px;
      font-size: 14px;
      line-height: 1.5;
      word-break: break-word;
    }
    .digipay-msg-bubble.user {
      align-self: flex-end;
      background: #2563eb;
      color: #ffffff;
      border-bottom-right-radius: 4px;
    }
    .digipay-msg-bubble.assistant {
      align-self: flex-start;
      background: #1e293b;
      color: #e2e8f0;
      border-bottom-left-radius: 4px;
      border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .digipay-escalate-badge {
      display: inline-block;
      margin-top: 8px;
      padding: 4px 8px;
      background: #7c2d12;
      color: #fdba74;
      font-size: 11px;
      border-radius: 6px;
      font-weight: 600;
    }
    .digipay-quick-chips {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding: 8px 16px;
      background: #090d16;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
    .digipay-chip {
      background: #1e293b;
      color: #38bdf8;
      border: 1px solid rgba(56, 189, 248, 0.2);
      border-radius: 20px;
      padding: 6px 12px;
      font-size: 12px;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }
    .digipay-chip:hover {
      background: #2563eb;
      color: #fff;
    }
    .digipay-chat-footer {
      padding: 12px 16px;
      background: #0f172a;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .digipay-chat-input {
      flex: 1;
      background: #1e293b;
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      padding: 10px 14px;
      color: #fff;
      font-size: 14px;
      outline: none;
    }
    .digipay-chat-input:focus {
      border-color: #2563eb;
    }
    .digipay-send-btn {
      background: #2563eb;
      color: #fff;
      border: none;
      border-radius: 12px;
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    }
    .digipay-send-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  `;

  class DigiPayChatElement extends HTMLElement {
    connectedCallback() {
      const cscId = this.getAttribute('csc-id') || this.getAttribute('csc_id') || '500100100014';
      const baseUrl = this.getAttribute('api-url') || this.getAttribute('api_url') || this.getAttribute('base-url') || 'http://localhost:8000';
      const mode = this.getAttribute('mode') || 'floating';
      initDigiPayChat({ cscId, baseUrl, mode, targetElement: this });
    }
  }

  if (!customElements.get('digipay-chat')) {
    customElements.define('digipay-chat', DigiPayChatElement);
  }

  window.initDigiPayChat = function (config = {}) {
    const mode = config.mode || 'floating';

    if (!document.getElementById('digipay-chat-styles')) {
      const styleEl = document.createElement('style');
      styleEl.id = 'digipay-chat-styles';
      styleEl.innerHTML = styles;
      document.head.appendChild(styleEl);
    }

    const container = config.targetElement || document.body;

    const root = document.createElement('div');
    root.className = 'digipay-chat-wrapper';
    root.innerHTML = `
      ${mode === 'floating' ? `
        <button class="digipay-chat-launcher">
          <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/></svg>
        </button>
      ` : ''}

      <div class="digipay-chat-window ${mode}">
        <div class="digipay-chat-header">
          <div class="digipay-chat-header-info">
            <div class="digipay-avatar">DP</div>
            <div>
              <h4 class="digipay-title">DigiPay Support AI</h4>
              <div class="digipay-subtitle">
                <span class="digipay-online-dot"></span> Online • Ledger & Transactions
              </div>
            </div>
          </div>
          ${mode !== 'inline' ? `<button class="digipay-close-btn">&times;</button>` : ''}
        </div>

        <div class="digipay-body digipay-chat-body">
          <div class="digipay-msg-bubble assistant">
            Namaste! I am your DigiPay AI Assistant (${mode} mode active). Ask me about wallet balances, transaction logs, settlements, or KYC status.
          </div>
        </div>

        <div class="digipay-quick-chips">
          <div class="digipay-chip" data-msg="Check my wallet balance">💰 Wallet Balance</div>
          <div class="digipay-chip" data-msg="Check my last settlement">🏦 Last Settlement</div>
          <div class="digipay-chip" data-msg="Seed test data for my account">🌱 Seed Test Data</div>
        </div>

        <div class="digipay-chat-footer">
          <input class="digipay-chat-input" placeholder="Type a message..." />
          <button class="digipay-send-btn">➔</button>
        </div>
      </div>
    `;
    container.appendChild(root);

    let targetBaseUrl = config.baseUrl || config.apiUrl || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000');
    targetBaseUrl = targetBaseUrl.replace(/\/$/, '');
    if (targetBaseUrl.includes(':5173')) {
      targetBaseUrl = targetBaseUrl.replace(':5173', ':8000');
    }

    const sdk = new window.DigiPayChatSDK({
      baseUrl: targetBaseUrl,
      cscId: config.cscId || '500100100014'
    });

    const launcher = root.querySelector('.digipay-chat-launcher');
    const win = root.querySelector('.digipay-chat-window');
    const closeBtn = root.querySelector('.digipay-close-btn');
    const body = root.querySelector('.digipay-body');
    const input = root.querySelector('.digipay-chat-input');
    const sendBtn = root.querySelector('.digipay-send-btn');

    if (launcher) launcher.onclick = () => win.classList.toggle('open');
    if (closeBtn) closeBtn.onclick = () => win.classList.remove('open');

    function appendMessage(role, content, extra = {}) {
      const bubble = document.createElement('div');
      bubble.className = `digipay-msg-bubble ${role}`;
      bubble.textContent = content;

      if (extra.escalate) {
        const badge = document.createElement('div');
        badge.className = 'digipay-escalate-badge';
        badge.textContent = '⚠️ Escalated to Support Executive';
        bubble.appendChild(badge);
      }

      body.appendChild(bubble);
      body.scrollTop = body.scrollHeight;
    }

    async function handleSend(text) {
      if (!text || !text.trim()) return;
      appendMessage('user', text);
      input.value = '';
      sendBtn.disabled = true;

      try {
        if (text.includes('Seed Test Data') || text.includes('seed')) {
          const seedRes = await sdk.seedTestData();
          appendMessage('assistant', seedRes.msg || 'Test database seeded successfully!');
        } else {
          const res = await sdk.sendMessage(text);
          appendMessage('assistant', res.response, { escalate: res.escalate });
        }
      } catch (err) {
        appendMessage('assistant', `Communication error: ${err.message}`);
      } finally {
        sendBtn.disabled = false;
      }
    }

    sendBtn.onclick = () => handleSend(input.value);
    input.onkeypress = (e) => {
      if (e.key === 'Enter') handleSend(input.value);
    };

    root.querySelectorAll('.digipay-chip').forEach(chip => {
      chip.onclick = () => handleSend(chip.getAttribute('data-msg'));
    });

    sdk.authenticate();
  };
})();

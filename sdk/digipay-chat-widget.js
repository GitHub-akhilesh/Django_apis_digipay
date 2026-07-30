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

    /* ---- Rendered Markdown inside assistant bubbles ---- */
    .digipay-md-heading {
      font-weight: 700;
      font-size: 13px;
      letter-spacing: .02em;
      margin: 2px 0 6px;
      opacity: .95;
    }
    .digipay-md-line { margin: 2px 0; }
    .digipay-md-gap { height: 6px; }
    .digipay-md-rule {
      border: 0;
      border-top: 1px solid rgba(255,255,255,.15);
      margin: 8px 0 6px;
    }
    .digipay-list { margin: 4px 0 4px 2px; padding-left: 16px; }
    .digipay-list li { margin: 3px 0; line-height: 1.45; }
    .digipay-msg-bubble strong { font-weight: 700; }
    .digipay-msg-bubble em { opacity: .75; font-style: normal; font-size: 11.5px; }
    .digipay-msg-bubble code {
      background: rgba(255,255,255,.12);
      padding: 1px 5px;
      border-radius: 4px;
      font-size: 11.5px;
    }

    /* Tables scroll inside the bubble so a wide report never widens the widget. */
    .digipay-table-wrap {
      overflow-x: auto;
      margin: 6px 0;
      border-radius: 8px;
      border: 1px solid rgba(255,255,255,.12);
    }
    .digipay-table { border-collapse: collapse; width: 100%; font-size: 11.5px; }
    .digipay-table th, .digipay-table td {
      padding: 6px 9px;
      text-align: left;
      white-space: nowrap;
      border-bottom: 1px solid rgba(255,255,255,.08);
    }
    .digipay-table th {
      background: rgba(255,255,255,.07);
      font-weight: 600;
      position: sticky;
      top: 0;
    }
    .digipay-table tr:last-child td { border-bottom: 0; }

    /* ---- Motion ----
       Every animation honours prefers-reduced-motion at the bottom of this
       block: motion is decoration, and for some users it causes nausea. */

    /* Messages rise and fade in, so a new reply is noticed without a jolt. */
    .digipay-msg-bubble {
      animation: digipay-msg-in 0.28s cubic-bezier(0.22, 1, 0.36, 1) both;
    }
    @keyframes digipay-msg-in {
      from { opacity: 0; transform: translateY(8px) scale(0.985); }
      to   { opacity: 1; transform: translateY(0) scale(1); }
    }

    /* The panel scales up from the launcher corner rather than appearing. */
    .digipay-chat-window {
      transform-origin: bottom right;
      transition: opacity .22s ease, transform .26s cubic-bezier(0.22, 1, 0.36, 1);
    }
    .digipay-chat-window:not(.open) {
      opacity: 0;
      transform: translateY(10px) scale(0.97);
      pointer-events: none;
    }
    .digipay-chat-window.open { opacity: 1; transform: translateY(0) scale(1); }

    /* Launcher: lifts on hover, presses in on click, and pulses once on load so
       a first-time user notices it exists. */
    .digipay-chat-launcher {
      transition: transform .18s ease, box-shadow .18s ease;
      animation: digipay-attention 2.4s ease-out 1.2s 2;
    }
    .digipay-chat-launcher:hover { transform: scale(1.08) translateY(-2px); }
    .digipay-chat-launcher:active { transform: scale(0.94); }
    @keyframes digipay-attention {
      0%, 100% { box-shadow: 0 8px 24px rgba(37, 99, 235, 0.4); }
      50%      { box-shadow: 0 8px 34px rgba(37, 99, 235, 0.95); }
    }

    .digipay-chip {
      transition: transform .15s ease, background .2s ease, color .2s ease;
    }
    .digipay-chip:hover { transform: translateY(-2px); }
    .digipay-chip:active { transform: translateY(0) scale(0.97); }

    .digipay-send-btn { transition: transform .15s ease, filter .2s ease; }
    .digipay-send-btn:hover:not(:disabled) { transform: scale(1.08); filter: brightness(1.1); }
    .digipay-send-btn:active:not(:disabled) { transform: scale(0.93); }

    /* Newly arrived amounts flash briefly so the figure draws the eye. */
    .digipay-msg-bubble strong { transition: color .3s ease; }
    .digipay-highlight { animation: digipay-flash 1.1s ease-out 1; }
    @keyframes digipay-flash {
      0%   { background: rgba(56, 189, 248, 0.28); }
      100% { background: transparent; }
    }

    /* Table rows stagger in, which makes a long passbook feel responsive. */
    .digipay-table tbody tr {
      animation: digipay-row-in .26s ease both;
    }
    .digipay-table tbody tr:nth-child(1) { animation-delay: .02s; }
    .digipay-table tbody tr:nth-child(2) { animation-delay: .05s; }
    .digipay-table tbody tr:nth-child(3) { animation-delay: .08s; }
    .digipay-table tbody tr:nth-child(4) { animation-delay: .11s; }
    .digipay-table tbody tr:nth-child(5) { animation-delay: .14s; }
    .digipay-table tbody tr:nth-child(n+6) { animation-delay: .17s; }
    @keyframes digipay-row-in {
      from { opacity: 0; transform: translateX(-6px); }
      to   { opacity: 1; transform: translateX(0); }
    }

    @media (prefers-reduced-motion: reduce) {
      .digipay-msg-bubble,
      .digipay-chat-launcher,
      .digipay-table tbody tr,
      .digipay-highlight,
      .digipay-typing span {
        animation: none !important;
      }
      .digipay-chat-window,
      .digipay-chip,
      .digipay-send-btn { transition: none !important; }
    }

    /* ---- Voice controls ---- */
    .digipay-lang-select {
      background: #1e293b;
      color: #94a3b8;
      border: 1px solid rgba(148, 163, 184, 0.25);
      border-radius: 8px;
      padding: 8px 6px;
      font-size: 11px;
      max-width: 78px;
      flex: 0 0 auto;
      cursor: pointer;
    }
    .digipay-lang-select:focus { outline: none; border-color: #38bdf8; color: #fff; }

    .digipay-mic-btn, .digipay-speak-btn {
      background: #1e293b;
      color: #94a3b8;
      border: 1px solid rgba(148, 163, 184, 0.25);
      border-radius: 50%;
      width: 40px;
      height: 40px;
      flex: 0 0 auto;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.2s;
    }
    .digipay-mic-btn:hover, .digipay-speak-btn:hover { color: #fff; background: #334155; }
    .digipay-mic-btn svg, .digipay-speak-btn svg { width: 18px; height: 18px; fill: currentColor; }

    /* Recording: red and pulsing, so it is never ambiguous that the mic is live. */
    .digipay-mic-btn.recording {
      background: #dc2626;
      color: #fff;
      border-color: #dc2626;
      animation: digipay-pulse 1.4s infinite;
    }
    @keyframes digipay-pulse {
      0%   { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.55); }
      70%  { box-shadow: 0 0 0 10px rgba(220, 38, 38, 0); }
      100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
    }
    .digipay-speak-btn.on { color: #38bdf8; border-color: rgba(56, 189, 248, 0.45); }
    .digipay-voice-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 16px 0;
    }
    .digipay-voice-hint {
      font-size: 11px;
      color: #64748b;
      min-height: 15px;
      flex: 1 1 auto;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    /* ---- Typing indicator ---- */
    .digipay-typing { display: flex; gap: 4px; align-items: center; padding: 2px 0; }
    .digipay-typing span {
      width: 6px; height: 6px; border-radius: 50%;
      background: currentColor; opacity: .45;
      animation: digipay-bounce 1.2s infinite ease-in-out;
    }
    .digipay-typing span:nth-child(2) { animation-delay: .15s; }
    .digipay-typing span:nth-child(3) { animation-delay: .3s; }
    @keyframes digipay-bounce {
      0%, 60%, 100% { transform: translateY(0); opacity: .35; }
      30% { transform: translateY(-4px); opacity: .9; }
    }

    /* Quick-action chips wrap onto multiple rows instead of forcing a horizontal
       scrollbar, which hid most of the actions behind a drag. */
    .digipay-quick-chips {
      flex-wrap: wrap;
      overflow-x: visible;
      max-height: 92px;
      overflow-y: auto;
    }
    .digipay-chip { flex: 0 0 auto; }
    .digipay-chip.legacy {
      color: #fbbf24;
      border-color: rgba(251, 191, 36, 0.25);
    }
    .digipay-chip.legacy:hover { background: #b45309; color: #fff; }
    .digipay-chip.help {
      color: #a3e635;
      border-color: rgba(163, 230, 53, 0.25);
    }
    .digipay-chip.help:hover { background: #4d7c0f; color: #fff; }
  `;

  class DigiPayChatElement extends HTMLElement {
    connectedCallback() {
      const cscId = this.getAttribute('csc-id') || this.getAttribute('csc_id') || '500100100014';
      const mode = this.getAttribute('mode') || 'floating';

      // Which backend to talk to. 'legacy' (default) keeps existing embeds
      // working; 'ai-platform' targets the AI platform, which serves
      // /api/v1/chat instead of /api/v1/agent/chat and requires the host app's
      // DigiPay JWT. See digipay-chat-sdk.js for the full contract.
      const apiMode = this.getAttribute('api-mode') || this.getAttribute('api_mode') || 'legacy';

      // Language for speech input and spoken replies. en-IN gives noticeably
      // better recognition of Indian English and of terms like AePS and VLE.
      const voiceLang = this.getAttribute('voice-lang') || this.getAttribute('voice_lang') || 'en-IN';

      // Default port follows the mode so api-url can be omitted entirely.
      const defaultBase = apiMode === 'ai-platform'
        ? 'http://localhost:8001'
        : 'http://localhost:8000';
      const baseUrl = this.getAttribute('api-url')
        || this.getAttribute('api_url')
        || this.getAttribute('base-url')
        || defaultBase;

      // Token passed explicitly, or read from where the host app keeps it.
      const token = this.getAttribute('token') || null;
      const tokenStorageKey = this.getAttribute('token-storage-key')
        || this.getAttribute('token_storage_key')
        || 'authToken';

      initDigiPayChat({
        cscId, baseUrl, mode, apiMode, token, tokenStorageKey, voiceLang, targetElement: this
      });
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
            Namaste! I'm your DigiPay assistant. Ask me about your balance, passbook, transactions, settlements or devices — or tap a suggestion below.
          </div>
        </div>

        <div class="digipay-quick-chips">
          <div class="digipay-chip" data-msg="Check my wallet balance">💰 Balance</div>
          <div class="digipay-chip" data-msg="Show my passbook for this month">📒 Passbook</div>
          <div class="digipay-chip" data-msg="Show my transaction history">🧾 Transactions</div>
          <div class="digipay-chip" data-msg="Summarise my transactions this month">📊 Summary</div>
          <div class="digipay-chip" data-msg="Is my registered device active">📱 My devices</div>
          <div class="digipay-chip" data-msg="Any notifications for me">🔔 Alerts</div>
          <div class="digipay-chip legacy" data-msg="What is my old digipay balance">🗄️ Old balance</div>
          <div class="digipay-chip legacy" data-msg="Show my legacy passbook">🗂️ Old passbook</div>
          <div class="digipay-chip help" data-msg="What is the AePS transaction limit">❓ AePS limit</div>
          <div class="digipay-chip help" data-msg="What can you do">✨ What can you do</div>
        </div>

        <!-- Language sits on its own row: five controls in the footer squeezed the
             text input to almost nothing on a 380px panel. -->
        <div class="digipay-voice-bar">
          <select class="digipay-lang-select" title="Voice language" aria-label="Voice language"></select>
          <span class="digipay-voice-hint"></span>
        </div>

        <div class="digipay-chat-footer">
          <button class="digipay-mic-btn" title="Speak your question" aria-label="Speak your question">
            <svg viewBox="0 0 24 24"><path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2z"/></svg>
          </button>
          <input class="digipay-chat-input" placeholder="Type or speak a message..." />
          <button class="digipay-speak-btn" title="Read replies aloud" aria-label="Read replies aloud">
            <svg viewBox="0 0 24 24"><path d="M3 10v4h4l5 5V5L7 10H3zm13.5 2a4.5 4.5 0 0 0-2.5-4.03v8.06A4.5 4.5 0 0 0 16.5 12zM14 3.23v2.06a6.98 6.98 0 0 1 0 13.42v2.06a9 9 0 0 0 0-17.54z"/></svg>
          </button>
          <button class="digipay-send-btn">➔</button>
        </div>
      </div>
    `;
    container.appendChild(root);

    const apiMode = config.apiMode === 'ai-platform' ? 'ai-platform' : 'legacy';
    const defaultPort = apiMode === 'ai-platform' ? '8001' : '8000';

    let targetBaseUrl = config.baseUrl || config.apiUrl;
    if (!targetBaseUrl && typeof window !== 'undefined' && window.location.origin) {
      if (window.location.port && window.location.port !== defaultPort) {
        targetBaseUrl = window.location.protocol + '//' + window.location.hostname + ':' + defaultPort;
      } else {
        targetBaseUrl = window.location.origin;
      }
    }
    if (!targetBaseUrl) targetBaseUrl = 'http://localhost:' + defaultPort;
    targetBaseUrl = targetBaseUrl.replace(/\/$/, '');

    if (typeof window.DigiPayChatSDK !== 'function') {
      // The UI is already in the DOM at this point, so fail loudly rather than
      // leaving a chat window whose send button silently does nothing.
      const msg = 'digipay-chat-sdk.js did not load before digipay-chat-widget.js. '
        + 'Include the SDK script first.';
      console.error('[DigiPayWidget] ' + msg);
      const bodyEl = root.querySelector('.digipay-body');
      if (bodyEl) {
        const err = document.createElement('div');
        err.className = 'digipay-msg-bubble assistant';
        err.textContent = 'Chat unavailable: ' + msg;
        bodyEl.appendChild(err);
      }
      return;
    }

    const sdk = new window.DigiPayChatSDK({
      baseUrl: targetBaseUrl,
      cscId: config.cscId || '500100100014',
      apiMode,
      token: config.token || null,
      tokenStorageKey: config.tokenStorageKey || 'authToken'
    });

    const launcher = root.querySelector('.digipay-chat-launcher');
    const win = root.querySelector('.digipay-chat-window');
    const closeBtn = root.querySelector('.digipay-close-btn');
    const body = root.querySelector('.digipay-body');
    const input = root.querySelector('.digipay-chat-input');
    const sendBtn = root.querySelector('.digipay-send-btn');
    const micBtn = root.querySelector('.digipay-mic-btn');
    const speakBtn = root.querySelector('.digipay-speak-btn');
    const voiceHint = root.querySelector('.digipay-voice-hint');
    const langSelect = root.querySelector('.digipay-lang-select');

    if (launcher) launcher.onclick = () => win.classList.toggle('open');
    if (closeBtn) closeBtn.onclick = () => {
      win.classList.remove('open');
      stopSpeaking();
      stopListening();
    };

    const setHint = (text) => { if (voiceHint) voiceHint.textContent = text || ''; };

    // ------------------------------------------------------------------
    // Voice assistance.
    //
    // Uses the browser's built-in Web Speech APIs, so the widget stays
    // zero-dependency and no audio ever leaves the device to a third party:
    //   SpeechRecognition   speech -> text (Chrome/Edge; Safari needs the prefix)
    //   speechSynthesis     text -> speech (all current browsers)
    //
    // Both are optional. Where unsupported the buttons are hidden rather than
    // left visible and dead. Recognition needs a secure context: it works on
    // https and on http://localhost, but not on a plain http:// LAN address.
    // ------------------------------------------------------------------
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const synth = window.speechSynthesis || null;

    // Languages a CSC VLE is likely to use. Recognition and synthesis both take
    // BCP-47 tags, so one list drives both. The chosen language is remembered per
    // browser: a VLE who speaks Marathi should not have to reselect it every visit.
    const VOICE_LANGUAGES = [
      { code: 'en-IN', label: 'English' },
      { code: 'hi-IN', label: 'हिन्दी' },
      { code: 'bn-IN', label: 'বাংলা' },
      { code: 'mr-IN', label: 'मराठी' },
      { code: 'ta-IN', label: 'தமிழ்' },
      { code: 'te-IN', label: 'తెలుగు' },
      { code: 'gu-IN', label: 'ગુજરાતી' },
      { code: 'kn-IN', label: 'ಕನ್ನಡ' },
      { code: 'ml-IN', label: 'മലയാളം' },
      { code: 'pa-IN', label: 'ਪੰਜਾਬੀ' },
      { code: 'or-IN', label: 'ଓଡ଼ିଆ' },
      { code: 'as-IN', label: 'অসমীয়া' },
      { code: 'ur-IN', label: 'اردو' },
    ];
    const VOICE_LANG_KEY = 'digipay_voice_lang';

    let voiceLang = config.voiceLang || 'en-IN';
    try {
      const saved = localStorage.getItem(VOICE_LANG_KEY);
      if (saved && VOICE_LANGUAGES.some((l) => l.code === saved)) voiceLang = saved;
    } catch (e) { /* storage unavailable; fall back to the default */ }

    let recognition = null;
    let listening = false;
    let speakReplies = false;

    if (!SpeechRecognition && micBtn) {
      micBtn.style.display = 'none';
      console.info('[DigiPayWidget] Speech recognition unavailable; mic hidden.');
    }
    if (!synth && speakBtn) {
      speakBtn.style.display = 'none';
    }

    function stopSpeaking() {
      try { if (synth && synth.speaking) synth.cancel(); } catch (e) { /* no-op */ }
    }

    /** Speak a reply, with Markdown and citations stripped so it reads naturally. */
    function speak(text) {
      if (!speakReplies || !synth || !text) return;
      const plain = String(text)
        .replace(/```[\s\S]*?```/g, '')
        .replace(/\|[^\n]*\|/g, '')                 // table rows read as noise
        .replace(/^\s*[-*]\s+/gm, '')
        .replace(/[*_`#>]/g, '')
        .replace(/\bRs\b/g, 'rupees')
        .replace(/₹\s?([\d,]+(?:\.\d+)?)/g, '$1 rupees')
        .replace(/\s{2,}/g, ' ')
        .trim();
      if (!plain) return;
      stopSpeaking();
      const utter = new SpeechSynthesisUtterance(plain.slice(0, 600));
      utter.lang = voiceLang;
      utter.rate = 1.02;
      synth.speak(utter);
    }

    function stopListening() {
      listening = false;
      if (micBtn) micBtn.classList.remove('recording');
      try { if (recognition) recognition.stop(); } catch (e) { /* no-op */ }
    }

    function startListening() {
      if (!SpeechRecognition) return;

      recognition = new SpeechRecognition();
      recognition.lang = voiceLang;
      recognition.interimResults = true;
      recognition.continuous = false;
      recognition.maxAlternatives = 1;

      let finalText = '';

      recognition.onstart = () => {
        listening = true;
        micBtn.classList.add('recording');
        setHint('Listening… speak now');
        stopSpeaking();   // never listen and talk at once
      };

      recognition.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const chunk = event.results[i][0].transcript;
          if (event.results[i].isFinal) finalText += chunk;
          else interim += chunk;
        }
        // Show words as they are recognised so the user can see it working.
        input.value = (finalText + interim).trim();
        setHint(interim ? 'Listening… ' + interim : 'Listening…');
      };

      recognition.onerror = (event) => {
        stopListening();
        const messages = {
          'not-allowed': 'Microphone access was blocked. Allow it in your browser settings to speak.',
          'service-not-allowed': 'Microphone access was blocked. Allow it in your browser settings to speak.',
          'no-speech': "I didn't catch that. Tap the mic and try again.",
          'audio-capture': 'No microphone was found. Please connect one and try again.',
          'network': 'Speech recognition needs a network connection.',
        };
        setHint(messages[event.error] || 'Speech input is unavailable right now.');
        console.warn('[DigiPayWidget] speech recognition error:', event.error);
      };

      recognition.onend = () => {
        stopListening();
        const text = (finalText || input.value || '').trim();
        if (text) {
          setHint('');
          handleSend(text);            // send automatically, like a voice assistant
        } else {
          setHint("I didn't catch that. Tap the mic and try again.");
        }
      };

      try {
        recognition.start();
      } catch (e) {
        stopListening();
        setHint('Could not start the microphone.');
      }
    }

    // Populate the language picker and remember the choice.
    if (langSelect) {
      if (!SpeechRecognition && !synth) {
        langSelect.style.display = 'none';
      } else {
        langSelect.innerHTML = VOICE_LANGUAGES
          .map((l) => `<option value="${l.code}"${l.code === voiceLang ? ' selected' : ''}>${l.label}</option>`)
          .join('');
        langSelect.onchange = () => {
          voiceLang = langSelect.value;
          try { localStorage.setItem(VOICE_LANG_KEY, voiceLang); } catch (e) { /* no-op */ }
          const chosen = VOICE_LANGUAGES.find((l) => l.code === voiceLang);
          setHint(`Voice set to ${chosen ? chosen.label : voiceLang}.`);
          stopListening();
          stopSpeaking();
        };
      }
    }

    if (micBtn) {
      micBtn.onclick = () => (listening ? stopListening() : startListening());
    }

    if (speakBtn) {
      speakBtn.onclick = () => {
        speakReplies = !speakReplies;
        speakBtn.classList.toggle('on', speakReplies);
        speakBtn.title = speakReplies ? 'Stop reading replies aloud' : 'Read replies aloud';
        if (speakReplies) {
          setHint('Replies will be read aloud.');
        } else {
          stopSpeaking();
          setHint('');
        }
      };
    }

    /**
     * Minimal, safe Markdown -> HTML for assistant replies.
     *
     * The backend formats answers as Markdown (bold labels, bullet lists, tables
     * with amounts). Rendering that with textContent showed raw syntax to the
     * user - "**CSC ID:** 500100100014" - which reads as a broken response.
     *
     * Deliberately hand-rolled and tiny: the widget is zero-dependency, and a
     * full Markdown library would be far larger than the whole SDK. Input is
     * HTML-escaped FIRST, so no backend string can inject markup.
     */
    function renderMarkdown(text) {
      const escapeHtml = (s) => String(s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

      // Bold must run before single-asterisk italics, or **x** would be eaten
      // as *(*x*)* and leave stray asterisks on screen.
      const inline = (s) => escapeHtml(s)
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/(^|[^*])\*(?!\*)([^*]+?)\*(?!\*)/g, '$1<em>$2</em>')
        .replace(/(^|[\s(])_(?!_)([^_]+?)_(?=[\s.,;:)!?]|$)/g, '$1<em>$2</em>')
        .replace(/`([^`]+?)`/g, '<code>$1</code>');

      const lines = String(text || '').split('\n');
      const html = [];
      let listOpen = false;
      let tableRows = [];

      const flushList = () => { if (listOpen) { html.push('</ul>'); listOpen = false; } };
      const flushTable = () => {
        if (!tableRows.length) return;
        const cells = (row) => row.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
        const header = cells(tableRows[0]);
        const bodyRows = tableRows.slice(1).filter((r) => !/^\|?[\s:-]+\|/.test(r));
        html.push('<div class="digipay-table-wrap"><table class="digipay-table"><thead><tr>'
          + header.map((c) => `<th>${inline(c)}</th>`).join('')
          + '</tr></thead><tbody>'
          + bodyRows.map((r) => '<tr>' + cells(r).map((c) => `<td>${inline(c)}</td>`).join('') + '</tr>').join('')
          + '</tbody></table></div>');
        tableRows = [];
      };

      for (const raw of lines) {
        const line = raw.trimEnd();

        if (/^\s*\|.*\|\s*$/.test(line)) { flushList(); tableRows.push(line.trim()); continue; }
        flushTable();

        if (/^\s*[-*]\s+/.test(line)) {
          if (!listOpen) { html.push('<ul class="digipay-list">'); listOpen = true; }
          html.push(`<li>${inline(line.replace(/^\s*[-*]\s+/, ''))}</li>`);
          continue;
        }
        flushList();

        if (/^\s*#{1,4}\s+/.test(line)) {
          html.push(`<div class="digipay-md-heading">${inline(line.replace(/^\s*#{1,4}\s+/, ''))}</div>`);
          continue;
        }
        if (/^\s*---+\s*$/.test(line)) { html.push('<hr class="digipay-md-rule">'); continue; }
        if (!line.trim()) { html.push('<div class="digipay-md-gap"></div>'); continue; }

        html.push(`<div class="digipay-md-line">${inline(line)}</div>`);
      }
      flushList();
      flushTable();
      return html.join('');
    }

    function appendMessage(role, content, extra = {}) {
      const bubble = document.createElement('div');
      bubble.className = `digipay-msg-bubble ${role}`;
      // User text stays literal; assistant replies are Markdown from the backend.
      if (role === 'assistant') {
        bubble.innerHTML = renderMarkdown(content);
      } else {
        bubble.textContent = content;
      }

      if (extra.escalate) {
        const badge = document.createElement('div');
        badge.className = 'digipay-escalate-badge';
        // Phrased for the person reading it, not for an operations dashboard.
        badge.textContent = 'A support colleague has been notified';
        bubble.appendChild(badge);
      }

      body.appendChild(bubble);

      // Flash any money figures so the number the user asked for stands out.
      if (role === 'assistant') {
        bubble.querySelectorAll('strong').forEach((el) => {
          if (/[₹]|\d[\d,]*\.\d{2}/.test(el.textContent)) {
            el.classList.add('digipay-highlight');
          }
        });
      }

      // Smooth scroll rather than a jump, so the reading position is not lost.
      body.scrollTo({ top: body.scrollHeight, behavior: 'smooth' });
      return bubble;
    }

    /** Animated dots while waiting, so the widget never looks frozen. */
    function showTyping() {
      const bubble = document.createElement('div');
      bubble.className = 'digipay-msg-bubble assistant digipay-typing-bubble';
      bubble.innerHTML = '<div class="digipay-typing"><span></span><span></span><span></span></div>';
      body.appendChild(bubble);
      body.scrollTop = body.scrollHeight;
      return bubble;
    }

    async function handleSend(text) {
      if (!text || !text.trim()) return;
      appendMessage('user', text);
      input.value = '';
      sendBtn.disabled = true;
      const typing = showTyping();

      try {
        if (text.includes('Seed Test Data') || text.includes('seed')) {
          const seedRes = await sdk.seedTestData();
          typing.remove();
          appendMessage('assistant', seedRes.msg || 'Test data has been set up.');
        } else {
          const res = await sdk.sendMessage(text);
          typing.remove();
          appendMessage('assistant', res.response, { escalate: res.escalate });
          speak(res.response);
        }
      } catch (err) {
        typing.remove();
        // Say what the person can do, not what the transport did. The technical
        // detail still goes to the console for whoever is debugging.
        console.error('[DigiPayWidget] send failed:', err);
        const detail = String(err && err.message || '');
        let friendly = "Sorry, I couldn't reach DigiPay just now. Please try again in a moment.";
        if (/401|Unauthorized|session/i.test(detail)) {
          friendly = 'Your DigiPay session seems to have ended. Please sign in again, then ask me once more.';
        } else if (/Failed to fetch|NetworkError|CORS/i.test(detail)) {
          friendly = "I can't connect to DigiPay from here. Please check your connection and try again.";
        }
        appendMessage('assistant', friendly);
        speak(friendly);
      } finally {
        sendBtn.disabled = false;
        input.focus();
      }
    }

    sendBtn.onclick = () => handleSend(input.value);
    // keypress is deprecated and misses IME/composed input; keydown is reliable.
    input.onkeydown = (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend(input.value);
      }
    };

    root.querySelectorAll('.digipay-chip').forEach(chip => {
      chip.onclick = () => handleSend(chip.getAttribute('data-msg'));
    });

    sdk.authenticate();
  };
})();

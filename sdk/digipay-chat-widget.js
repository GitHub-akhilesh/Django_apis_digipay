/**
 * DigiPay Chat UI Widget Component v2.0.0
 * Zero-dependency drop-in chat widget for Web, React, Vue, Angular, and HTML apps.
 * Supports Layout Modes: mode="floating" | mode="sidebar" | mode="inline"
 */

(function () {
  const styles = `
    /* ==================================================================
       DigiPay Chat Widget - design tokens
       One dark theme, tuned for a 390px floating panel.
       ================================================================== */
    .digipay-chat-wrapper {
      --dp-bg:        #060B18;
      --dp-card:      #111827;
      --dp-glass:     rgba(255, 255, 255, 0.07);
      --dp-glass-hi:  rgba(255, 255, 255, 0.12);
      --dp-stroke:    rgba(255, 255, 255, 0.10);
      --dp-primary:   #2563EB;
      --dp-secondary: #06B6D4;
      --dp-accent:    #7C3AED;
      --dp-success:   #22C55E;
      --dp-warning:   #F59E0B;
      --dp-danger:    #EF4444;
      --dp-text:      #E8EDF7;
      --dp-muted:     #94A3B8;
      --dp-r-lg:      28px;
      --dp-r-md:      20px;
      --dp-r-sm:      14px;
      --dp-shadow:    0 24px 60px rgba(0,0,0,.55), 0 2px 8px rgba(0,0,0,.4);
      --dp-ease:      cubic-bezier(.22,1,.36,1);
      font-family: 'Inter', 'SF Pro Display', 'Manrope', -apple-system,
                   BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Respect the OS setting. "Everything animates" must not mean motion
       sickness for someone who has asked the system for less of it. */
    @media (prefers-reduced-motion: reduce) {
      .digipay-chat-wrapper *,
      .digipay-chat-wrapper *::before,
      .digipay-chat-wrapper *::after {
        animation-duration: .001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: .001ms !important;
      }
    }

    /* ================================ LAUNCHER ======================== */
    .digipay-chat-launcher {
      position: fixed;
      bottom: 24px; right: 24px;
      width: 64px; height: 64px;
      border-radius: 50%;
      border: none; outline: none; cursor: pointer;
      z-index: 99999;
      background: linear-gradient(135deg, var(--dp-primary), var(--dp-accent) 55%, var(--dp-secondary));
      background-size: 200% 200%;
      box-shadow: 0 10px 30px rgba(37,99,235,.45), 0 0 0 1px rgba(255,255,255,.12) inset;
      display: flex; align-items: center; justify-content: center;
      animation: dp-gradient 8s ease infinite;
      transition: transform .35s var(--dp-ease), box-shadow .35s var(--dp-ease);
    }
    .digipay-chat-launcher::after {
      content: ''; position: absolute; inset: -6px;
      border-radius: 50%; border: 2px solid rgba(37,99,235,.5);
      animation: dp-ring 2.4s ease-out infinite;
    }
    .digipay-chat-launcher:hover { transform: scale(1.08) translateY(-2px); }
    .digipay-chat-launcher:active { transform: scale(.96); }
    .digipay-chat-launcher svg { width: 28px; height: 28px; fill: #fff; }
    @keyframes dp-ring {
      0%   { transform: scale(.9);  opacity: .8; }
      100% { transform: scale(1.5); opacity: 0; }
    }
    @keyframes dp-gradient {
      0%,100% { background-position: 0% 50%; }
      50%     { background-position: 100% 50%; }
    }

    /* ================================ WINDOW ========================== */
    .digipay-chat-window {
      position: relative;
      background: var(--dp-bg);
      color: var(--dp-text);
      display: none;
      flex-direction: column;
      overflow: hidden;
      box-shadow: var(--dp-shadow);
      isolation: isolate;
    }
    .digipay-chat-window.open { display: flex; animation: dp-panel-in .45s var(--dp-ease); }
    @keyframes dp-panel-in {
      from { opacity: 0; transform: translateY(24px) scale(.97); }
      to   { opacity: 1; transform: none; }
    }
    .digipay-chat-window.floating {
      position: fixed;
      bottom: 100px; right: 24px;
      width: 390px; height: 88vh; max-height: 780px;
      border-radius: var(--dp-r-lg);
      border: 1px solid var(--dp-stroke);
      z-index: 99999;
    }
    .digipay-chat-window.sidebar {
      position: fixed; top: 0; right: 0;
      width: 420px; height: 100vh; z-index: 99999;
      border-left: 1px solid var(--dp-stroke);
    }
    .digipay-chat-window.inline {
      display: flex; width: 100%; height: 640px;
      border-radius: var(--dp-r-lg);
      border: 1px solid var(--dp-stroke);
    }
    @media (max-width: 480px) {
      .digipay-chat-window.floating {
        width: 100vw; height: 100vh; max-height: none;
        bottom: 0; right: 0; border-radius: 0;
      }
      .digipay-chat-launcher { bottom: 18px; right: 18px; }
    }

    /* Aurora background + drifting particles, behind everything. */
    .digipay-aurora {
      position: absolute; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
    }
    .digipay-aurora::before, .digipay-aurora::after {
      content: ''; position: absolute; width: 320px; height: 320px; border-radius: 50%;
      filter: blur(70px); opacity: .40;
    }
    .digipay-aurora::before {
      background: radial-gradient(circle, var(--dp-primary), transparent 70%);
      top: -110px; left: -90px; animation: dp-drift-a 18s ease-in-out infinite;
    }
    .digipay-aurora::after {
      background: radial-gradient(circle, var(--dp-accent), transparent 70%);
      bottom: -130px; right: -90px; animation: dp-drift-b 22s ease-in-out infinite;
    }
    @keyframes dp-drift-a {
      0%,100% { transform: translate(0,0) scale(1); }
      50%     { transform: translate(50px,60px) scale(1.15); }
    }
    @keyframes dp-drift-b {
      0%,100% { transform: translate(0,0) scale(1.1); }
      50%     { transform: translate(-45px,-50px) scale(1); }
    }
    .digipay-particle {
      position: absolute; border-radius: 50%;
      background: rgba(147, 197, 253, .55);
      animation: dp-float linear infinite;
    }
    @keyframes dp-float {
      0%   { transform: translateY(100%) scale(.6); opacity: 0; }
      15%  { opacity: .7; }
      85%  { opacity: .5; }
      100% { transform: translateY(-120%) scale(1); opacity: 0; }
    }

    /* Every real layer sits above the aurora. */
    .digipay-chat-header, .digipay-body, .digipay-quick-chips,
    .digipay-rewards, .digipay-voice-bar, .digipay-chat-footer,
    .digipay-shortcuts, .digipay-nav { position: relative; z-index: 1; }

    /* ================================ HEADER ========================== */
    .digipay-chat-header {
      display: flex; align-items: center; gap: 12px;
      padding: 14px 16px;
      background: linear-gradient(180deg, rgba(17,24,39,.92), rgba(17,24,39,.55));
      backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--dp-stroke);
    }
    .digipay-chat-header-info { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
    .digipay-avatar {
      position: relative; flex: 0 0 auto;
      width: 42px; height: 42px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: 14px; letter-spacing: .5px; color: #fff;
      background: linear-gradient(135deg, var(--dp-primary), var(--dp-accent));
      box-shadow: 0 6px 18px rgba(37,99,235,.45), 0 0 0 1px rgba(255,255,255,.16) inset;
    }
    .digipay-avatar::after {
      content: 'AI'; position: absolute; bottom: -3px; right: -6px;
      font-size: 8px; font-weight: 800; letter-spacing: .4px;
      padding: 2px 5px; border-radius: 8px; color: #052e16;
      background: linear-gradient(135deg, #4ADE80, var(--dp-success));
      box-shadow: 0 2px 8px rgba(34,197,94,.5);
    }
    .digipay-title {
      margin: 0; font-size: 15px; font-weight: 700; letter-spacing: -.2px;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .digipay-subtitle {
      display: flex; align-items: center; gap: 6px;
      font-size: 11px; color: var(--dp-muted); margin-top: 2px;
    }
    .digipay-online-dot {
      width: 7px; height: 7px; border-radius: 50%;
      background: var(--dp-success); box-shadow: 0 0 0 0 rgba(34,197,94,.7);
      animation: dp-pulse 2s infinite;
    }
    @keyframes dp-pulse {
      0%   { box-shadow: 0 0 0 0 rgba(34,197,94,.7); }
      70%  { box-shadow: 0 0 0 7px rgba(34,197,94,0); }
      100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); }
    }
    .digipay-streak {
      display: none; align-items: center; gap: 5px;
      padding: 6px 10px; border-radius: 999px;
      font-size: 11px; font-weight: 700; color: #FED7AA;
      background: linear-gradient(135deg, rgba(245,158,11,.22), rgba(239,68,68,.18));
      border: 1px solid rgba(245,158,11,.35);
      white-space: nowrap;
    }
    .digipay-streak.on { display: flex; }
    .digipay-streak .dp-flame { animation: dp-bob 1.8s ease-in-out infinite; }
    @keyframes dp-bob { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-2px); } }
    .digipay-close-btn {
      flex: 0 0 auto; width: 32px; height: 32px; border-radius: 50%;
      background: var(--dp-glass); border: 1px solid var(--dp-stroke);
      color: var(--dp-muted); font-size: 20px; line-height: 1; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: all .25s var(--dp-ease);
    }
    .digipay-close-btn:hover { background: var(--dp-danger); color: #fff; transform: rotate(90deg); }

    /* ================================ BODY ============================ */
    .digipay-body {
      flex: 1; overflow-y: auto; overflow-x: hidden;
      padding: 16px 14px 8px;
      display: flex; flex-direction: column; gap: 12px;
      scrollbar-width: thin; scrollbar-color: rgba(255,255,255,.18) transparent;
    }
    .digipay-body::-webkit-scrollbar { width: 6px; }
    .digipay-body::-webkit-scrollbar-thumb { background: rgba(255,255,255,.16); border-radius: 999px; }

    /* ============================ ROBOT AVATAR ======================== */
    .digipay-hero { display: flex; justify-content: center; padding: 6px 0 2px; }
    .digipay-bot { position: relative; width: 132px; height: 118px; animation: dp-breathe 4s ease-in-out infinite; }
    @keyframes dp-breathe {
      0%,100% { transform: translateY(0) scale(1); }
      50%     { transform: translateY(-7px) scale(1.02); }
    }
    .digipay-bot-glow {
      position: absolute; left: 50%; bottom: 2px; transform: translateX(-50%);
      width: 96px; height: 20px; border-radius: 50%;
      background: radial-gradient(ellipse, rgba(6,182,212,.55), transparent 70%);
      filter: blur(6px); animation: dp-glow-pulse 4s ease-in-out infinite;
    }
    @keyframes dp-glow-pulse {
      0%,100% { opacity: .55; transform: translateX(-50%) scale(1); }
      50%     { opacity: .85; transform: translateX(-50%) scale(1.12); }
    }
    .digipay-bot svg { position: relative; width: 132px; height: 112px; overflow: visible; }
    .digipay-bot .dp-eye {
      transform-origin: center;
      animation: dp-blink 5s infinite;
    }
    @keyframes dp-blink {
      0%,92%,100% { transform: scaleY(1); }
      95%         { transform: scaleY(.08); }
    }
    .digipay-bot .dp-antenna-tip { animation: dp-tip 2.2s ease-in-out infinite; }
    @keyframes dp-tip { 0%,100% { opacity: .55; r: 4; } 50% { opacity: 1; r: 5; } }
    .digipay-bot .dp-hand { transform-origin: 26px 66px; }
    .digipay-bot.wave .dp-hand { animation: dp-wave 1.5s ease-in-out 2; }
    @keyframes dp-wave {
      0%,100% { transform: rotate(0deg); }
      25%     { transform: rotate(-22deg); }
      75%     { transform: rotate(14deg); }
    }
    /* moods */
    .digipay-bot.thinking { animation: dp-tilt 2.2s ease-in-out infinite; }
    @keyframes dp-tilt {
      0%,100% { transform: rotate(-3deg) translateY(0); }
      50%     { transform: rotate(3deg) translateY(-5px); }
    }
    .digipay-bot.talking .dp-mouth { animation: dp-talk .32s ease-in-out infinite; }
    @keyframes dp-talk { 0%,100% { transform: scaleY(.5); } 50% { transform: scaleY(1.5); } }
    .digipay-bot .dp-mouth { transform-origin: center; transition: all .3s var(--dp-ease); }
    .digipay-bot.listening .dp-visor { filter: drop-shadow(0 0 10px var(--dp-secondary)); }
    .digipay-bot.celebrate { animation: dp-hop .55s ease-in-out 3; }
    @keyframes dp-hop {
      0%,100% { transform: translateY(0) scale(1); }
      40%     { transform: translateY(-16px) scale(1.06); }
    }

    /* ============================= WELCOME CARD ======================= */
    .digipay-welcome {
      position: relative;
      background: linear-gradient(160deg, rgba(37,99,235,.16), rgba(124,58,237,.12)) !important;
      border: 1px solid transparent !important;
      background-clip: padding-box;
    }
    .digipay-welcome::before {
      content: ''; position: absolute; inset: -1px; border-radius: inherit; padding: 1px;
      background: linear-gradient(120deg, var(--dp-primary), var(--dp-secondary), var(--dp-accent), var(--dp-primary));
      background-size: 300% 300%;
      -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
      -webkit-mask-composite: xor; mask-composite: exclude;
      animation: dp-gradient 6s linear infinite;
      pointer-events: none;
    }
    .digipay-welcome strong { color: #93C5FD; }

    /* ============================== BUBBLES =========================== */
    .digipay-msg-bubble {
      max-width: 86%;
      padding: 12px 14px;
      border-radius: var(--dp-r-md);
      font-size: 13.5px; line-height: 1.62;
      word-wrap: break-word; white-space: pre-wrap;
      animation: dp-msg-in .38s var(--dp-ease);
      backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    }
    @keyframes dp-msg-in {
      from { opacity: 0; transform: translateY(12px) scale(.97); }
      to   { opacity: 1; transform: none; }
    }
    .digipay-msg-bubble.assistant {
      align-self: flex-start;
      background: var(--dp-glass);
      border: 1px solid var(--dp-stroke);
      border-bottom-left-radius: 6px;
      color: var(--dp-text);
    }
    .digipay-msg-bubble.user {
      align-self: flex-end;
      background: linear-gradient(135deg, var(--dp-primary), #1D4ED8);
      border: 1px solid rgba(255,255,255,.14);
      border-bottom-right-radius: 6px;
      color: #fff;
      box-shadow: 0 8px 22px rgba(37,99,235,.32);
    }
    .digipay-msg-time {
      display: block; margin-top: 6px;
      font-size: 10px; color: var(--dp-muted); opacity: .8;
    }
    .digipay-msg-bubble.user .digipay-msg-time { color: rgba(255,255,255,.75); text-align: right; }
    .digipay-highlight {
      color: #6EE7B7;
      text-shadow: 0 0 14px rgba(110,231,183,.45);
      animation: dp-flash 1.1s ease-out;
    }
    @keyframes dp-flash {
      0%  { background: rgba(34,197,94,.28); }
      100%{ background: transparent; }
    }
    .digipay-escalate-badge {
      margin-top: 8px; padding: 6px 10px; border-radius: 10px;
      font-size: 11px; color: #FCD34D;
      background: rgba(245,158,11,.14); border: 1px solid rgba(245,158,11,.3);
    }

    /* markdown */
    .digipay-md-heading { font-weight: 700; color: #BFDBFE; margin: 2px 0 4px; font-size: 13.5px; }
    .digipay-md-line { display: block; }
    .digipay-md-gap { height: 6px; }
    .digipay-md-rule { border: none; border-top: 1px solid var(--dp-stroke); margin: 8px 0; }
    .digipay-list { margin: 4px 0 4px 16px; padding: 0; }
    .digipay-list li { margin: 3px 0; }
    .digipay-table-wrap { overflow-x: auto; margin: 8px 0; border-radius: 12px; border: 1px solid var(--dp-stroke); }
    .digipay-table { width: 100%; border-collapse: collapse; font-size: 12px; }
    .digipay-table th, .digipay-table td { padding: 7px 10px; text-align: left; white-space: nowrap; }
    .digipay-table th { background: rgba(255,255,255,.07); color: #BFDBFE; font-weight: 700; }
    .digipay-table tr + tr td { border-top: 1px solid rgba(255,255,255,.07); }

    /* typing */
    .digipay-typing { display: flex; gap: 5px; align-items: center; padding: 2px 0; }
    .digipay-typing span {
      width: 7px; height: 7px; border-radius: 50%;
      background: linear-gradient(135deg, var(--dp-secondary), var(--dp-primary));
      animation: dp-typing 1.3s infinite ease-in-out;
    }
    .digipay-typing span:nth-child(2) { animation-delay: .18s; }
    .digipay-typing span:nth-child(3) { animation-delay: .36s; }
    @keyframes dp-typing {
      0%,60%,100% { transform: translateY(0);    opacity: .45; }
      30%         { transform: translateY(-7px); opacity: 1; }
    }

    /* shimmer skeleton, used instead of a spinner for data-shaped replies */
    .digipay-skeleton { display: flex; flex-direction: column; gap: 7px; }
    .digipay-skeleton i {
      display: block; height: 9px; border-radius: 6px;
      background: linear-gradient(90deg, rgba(255,255,255,.06) 25%, rgba(255,255,255,.16) 37%, rgba(255,255,255,.06) 63%);
      background-size: 400% 100%;
      animation: dp-shimmer 1.4s ease infinite;
    }
    .digipay-skeleton i:nth-child(2) { width: 78%; }
    .digipay-skeleton i:nth-child(3) { width: 55%; }
    @keyframes dp-shimmer { 0% { background-position: 100% 50%; } 100% { background-position: 0 50%; } }

    /* ========================== ACTION CARDS ========================== */
    .digipay-quick-chips {
      display: flex; gap: 9px;
      padding: 10px 14px 12px;
      overflow-x: auto; overflow-y: hidden;
      scrollbar-width: none;
      -webkit-overflow-scrolling: touch;
    }
    .digipay-quick-chips::-webkit-scrollbar { display: none; }
    .digipay-chip {
      position: relative; flex: 0 0 auto;
      width: 88px; padding: 11px 8px 10px;
      border-radius: var(--dp-r-sm);
      background: linear-gradient(160deg, rgba(255,255,255,.10), rgba(255,255,255,.04));
      border: 1px solid var(--dp-stroke);
      cursor: pointer; overflow: hidden;
      display: flex; flex-direction: column; align-items: center; gap: 5px;
      text-align: center;
      transition: transform .3s var(--dp-ease), box-shadow .3s var(--dp-ease), border-color .3s;
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    }
    .digipay-chip:hover {
      transform: translateY(-5px) scale(1.03);
      border-color: rgba(96,165,250,.5);
      box-shadow: 0 14px 28px rgba(0,0,0,.45), 0 0 22px rgba(37,99,235,.28);
    }
    .digipay-chip:active { transform: translateY(-1px) scale(.98); }
    .digipay-chip .dp-ic {
      width: 34px; height: 34px; border-radius: 11px;
      display: flex; align-items: center; justify-content: center;
      font-size: 17px;
      background: linear-gradient(135deg, rgba(37,99,235,.35), rgba(124,58,237,.28));
      box-shadow: 0 6px 14px rgba(0,0,0,.35), 0 0 0 1px rgba(255,255,255,.10) inset;
    }
    .digipay-chip .dp-lb { font-size: 11px; font-weight: 700; color: var(--dp-text); line-height: 1.2; }
    .digipay-chip .dp-sb { font-size: 9px; color: var(--dp-muted); line-height: 1.2; }
    .digipay-chip.legacy .dp-ic { background: linear-gradient(135deg, rgba(245,158,11,.35), rgba(180,83,9,.3)); }
    .digipay-chip.legacy .dp-lb { color: #FCD34D; }
    .digipay-chip.help .dp-ic { background: linear-gradient(135deg, rgba(6,182,212,.35), rgba(14,116,144,.3)); }
    /* ripple */
    .digipay-ripple {
      position: absolute; border-radius: 50%; transform: scale(0);
      background: rgba(255,255,255,.35); pointer-events: none;
      animation: dp-ripple .6s ease-out forwards;
    }
    @keyframes dp-ripple { to { transform: scale(3.2); opacity: 0; } }

    /* ============================= REWARDS ============================ */
    .digipay-rewards {
      display: none; align-items: center; gap: 10px;
      margin: 0 14px 10px; padding: 10px 12px;
      border-radius: var(--dp-r-sm);
      background: linear-gradient(135deg, rgba(37,99,235,.16), rgba(124,58,237,.14));
      border: 1px solid var(--dp-stroke);
      backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    }
    .digipay-rewards.on { display: flex; }
    .digipay-rewards .dp-rw-main { flex: 1; min-width: 0; }
    .digipay-rewards .dp-rw-title { font-size: 11.5px; font-weight: 700; color: var(--dp-text); }
    .digipay-rewards .dp-rw-sub { font-size: 10px; color: var(--dp-muted); margin-top: 1px; }
    .digipay-xp { height: 5px; border-radius: 999px; background: rgba(255,255,255,.10); margin-top: 7px; overflow: hidden; }
    .digipay-xp i {
      display: block; height: 100%; width: 0; border-radius: 999px;
      background: linear-gradient(90deg, var(--dp-secondary), var(--dp-primary), var(--dp-accent));
      transition: width 1.2s var(--dp-ease);
    }
    .digipay-coins {
      display: flex; align-items: center; gap: 6px; flex: 0 0 auto;
      padding: 6px 10px; border-radius: 999px;
      background: rgba(245,158,11,.14); border: 1px solid rgba(245,158,11,.3);
    }
    .digipay-coin {
      width: 18px; height: 18px; border-radius: 50%;
      background: linear-gradient(135deg, #FDE68A, var(--dp-warning));
      box-shadow: 0 0 10px rgba(245,158,11,.55);
      animation: dp-spin 3.5s linear infinite;
    }
    @keyframes dp-spin { 0% { transform: rotateY(0); } 100% { transform: rotateY(360deg); } }
    .digipay-coins b { font-size: 11.5px; color: #FCD34D; }

    /* ============================ VOICE BAR =========================== */
    .digipay-voice-bar {
      display: flex; align-items: center; gap: 8px;
      padding: 0 14px 8px;
    }
    .digipay-lang-select {
      padding: 6px 10px; border-radius: 999px;
      background: var(--dp-glass); color: var(--dp-text);
      border: 1px solid var(--dp-stroke);
      font-size: 11px; cursor: pointer; outline: none;
    }
    .digipay-lang-select option { background: var(--dp-card); color: var(--dp-text); }
    .digipay-voice-hint { font-size: 10.5px; color: var(--dp-muted); flex: 1; }

    /* ============================== FOOTER ============================ */
    .digipay-chat-footer {
      display: flex; align-items: center; gap: 8px;
      padding: 10px 14px;
      background: rgba(17,24,39,.6);
      backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
      border-top: 1px solid var(--dp-stroke);
    }
    .digipay-chat-input {
      flex: 1; min-width: 0;
      padding: 12px 15px; border-radius: 999px;
      background: var(--dp-glass); color: var(--dp-text);
      border: 1px solid var(--dp-stroke);
      font-size: 13px; outline: none;
      transition: border-color .25s, box-shadow .25s;
      font-family: inherit;
    }
    .digipay-chat-input::placeholder { color: #64748B; }
    .digipay-chat-input:focus {
      border-color: rgba(96,165,250,.6);
      box-shadow: 0 0 0 3px rgba(37,99,235,.16);
    }
    .digipay-mic-btn, .digipay-speak-btn, .digipay-send-btn {
      flex: 0 0 auto;
      width: 40px; height: 40px; border-radius: 50%;
      border: 1px solid var(--dp-stroke);
      background: var(--dp-glass); color: var(--dp-text);
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      transition: transform .25s var(--dp-ease), background .25s, box-shadow .25s;
    }
    .digipay-mic-btn svg, .digipay-speak-btn svg { width: 18px; height: 18px; fill: currentColor; }
    .digipay-mic-btn:hover, .digipay-speak-btn:hover { background: var(--dp-glass-hi); transform: translateY(-2px); }
    .digipay-mic-btn.listening {
      background: linear-gradient(135deg, var(--dp-danger), #B91C1C);
      color: #fff; border-color: transparent;
    }
    .digipay-mic-btn.listening::after {
      content: ''; position: absolute; inset: -5px; border-radius: 50%;
      border: 2px solid rgba(239,68,68,.6); animation: dp-ring 1.5s ease-out infinite;
    }
    .digipay-speak-btn.on {
      background: linear-gradient(135deg, var(--dp-secondary), #0E7490);
      color: #fff; border-color: transparent;
    }
    .digipay-send-btn {
      background: linear-gradient(135deg, var(--dp-primary), var(--dp-accent));
      background-size: 200% 200%;
      border-color: transparent; color: #fff; font-size: 17px;
      animation: dp-gradient 6s ease infinite;
      box-shadow: 0 6px 18px rgba(37,99,235,.4);
    }
    .digipay-send-btn:hover:not(:disabled) { transform: translateY(-2px) scale(1.06); }
    .digipay-send-btn:disabled { opacity: .5; cursor: not-allowed; }

    /* live waveform while listening */
    .digipay-wave { display: none; align-items: center; gap: 2px; height: 20px; }
    .digipay-wave.on { display: flex; }
    .digipay-wave i {
      width: 3px; border-radius: 2px; height: 5px;
      background: linear-gradient(180deg, var(--dp-secondary), var(--dp-primary));
      animation: dp-wave-b .9s ease-in-out infinite;
    }
    .digipay-wave i:nth-child(2) { animation-delay: .12s; }
    .digipay-wave i:nth-child(3) { animation-delay: .24s; }
    .digipay-wave i:nth-child(4) { animation-delay: .36s; }
    .digipay-wave i:nth-child(5) { animation-delay: .48s; }
    @keyframes dp-wave-b { 0%,100% { height: 5px; } 50% { height: 18px; } }

    /* ============================ SHORTCUTS =========================== */
    .digipay-shortcuts {
      display: flex; gap: 7px; padding: 0 14px 10px;
      overflow-x: auto; scrollbar-width: none;
    }
    .digipay-shortcuts::-webkit-scrollbar { display: none; }
    .digipay-sc {
      flex: 0 0 auto; display: flex; align-items: center; gap: 5px;
      padding: 7px 12px; border-radius: 999px;
      background: var(--dp-glass); border: 1px solid var(--dp-stroke);
      font-size: 11px; color: var(--dp-muted); cursor: pointer;
      transition: all .25s var(--dp-ease);
    }
    .digipay-sc:hover {
      color: #fff; border-color: rgba(96,165,250,.5);
      background: var(--dp-glass-hi); transform: translateY(-2px);
    }

    /* ========================== BOTTOM NAV ============================ */
    .digipay-nav {
      display: flex; align-items: flex-end; justify-content: space-around;
      padding: 8px 10px 10px;
      background: rgba(10,15,28,.86);
      backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
      border-top: 1px solid var(--dp-stroke);
    }
    .digipay-nav-item {
      flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px;
      padding: 5px 2px; border: none; background: none; cursor: pointer;
      color: var(--dp-muted); font-size: 9.5px; font-weight: 600;
      transition: color .25s var(--dp-ease), transform .25s var(--dp-ease);
    }
    .digipay-nav-item span.dp-nic { font-size: 16px; line-height: 1; }
    .digipay-nav-item:hover { color: var(--dp-text); transform: translateY(-2px); }
    .digipay-nav-item.active { color: #93C5FD; }
    .digipay-nav-item.center {
      flex: 0 0 auto; width: 54px; height: 54px; margin-top: -22px;
      border-radius: 50%; justify-content: center; color: #fff;
      background: linear-gradient(135deg, var(--dp-primary), var(--dp-accent));
      background-size: 200% 200%;
      box-shadow: 0 10px 26px rgba(37,99,235,.5), 0 0 0 4px rgba(6,11,24,.9);
      animation: dp-gradient 6s ease infinite;
    }
    .digipay-nav-item.center span.dp-nic { font-size: 21px; }
    .digipay-nav-item.center:hover { transform: translateY(-4px) scale(1.05); }

    /* ============================= CONFETTI =========================== */
    .digipay-confetti {
      position: absolute; top: 0; left: 0; width: 100%; height: 100%;
      pointer-events: none; z-index: 5; overflow: hidden;
    }
    .digipay-confetti i {
      position: absolute; width: 7px; height: 11px; border-radius: 2px;
      animation: dp-fall linear forwards;
    }
    @keyframes dp-fall {
      0%   { transform: translateY(-20px) rotate(0deg);    opacity: 1; }
      100% { transform: translateY(420px) rotate(620deg);  opacity: 0; }
    }
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

    // Greeting. Personalised only when the host app supplies a name -- an
    // invented one would be worse than none.
    const who = (config.userName || '').toString().trim();
    const welcomeHtml =
      `\u{1F64F} <strong>Namaste${who ? ' ' + who : ''}!</strong><br/>`
      + `I'm your <strong>DigiPay</strong> AI assistant. Ask me about your `
      + `balance, passbook, transactions, settlements or devices \u2014 `
      + `or tap a card below.`;

    const root = document.createElement('div');
    root.className = 'digipay-chat-wrapper';
    root.innerHTML = `
      ${mode === 'floating' ? `
        <button class="digipay-chat-launcher" aria-label="Open DigiPay assistant">
          <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/></svg>
        </button>
      ` : ''}

      <div class="digipay-chat-window ${mode}">
        <div class="digipay-aurora"></div>
        <div class="digipay-confetti"></div>

        <div class="digipay-chat-header">
          <div class="digipay-chat-header-info">
            <div class="digipay-avatar">DP</div>
            <div style="min-width:0">
              <h4 class="digipay-title">DigiPay Support AI</h4>
              <div class="digipay-subtitle">
                <span class="digipay-online-dot"></span> Online • Ledger &amp; Transactions
              </div>
            </div>
          </div>
          <div class="digipay-streak"><span class="dp-flame">🔥</span> <span class="dp-streak-n"></span></div>
          ${mode !== 'inline' ? `<button class="digipay-close-btn" aria-label="Close">&times;</button>` : ''}
        </div>

        <div class="digipay-body digipay-chat-body">
          <div class="digipay-hero">
            <div class="digipay-bot" aria-hidden="true">
              <div class="digipay-bot-glow"></div>
              <svg viewBox="0 0 132 112">
                <defs>
                  <linearGradient id="dpHead" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#DBEAFE"/><stop offset="100%" stop-color="#93B4E8"/>
                  </linearGradient>
                  <linearGradient id="dpVisor" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#0B1220"/><stop offset="100%" stop-color="#1E3A8A"/>
                  </linearGradient>
                  <linearGradient id="dpBody" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#BFD3F2"/><stop offset="100%" stop-color="#7E9FD4"/>
                  </linearGradient>
                </defs>
                <!-- antenna -->
                <line x1="66" y1="16" x2="66" y2="6" stroke="#93B4E8" stroke-width="3" stroke-linecap="round"/>
                <circle class="dp-antenna-tip" cx="66" cy="5" r="4" fill="#06B6D4"/>
                <!-- body -->
                <rect x="44" y="74" width="44" height="26" rx="13" fill="url(#dpBody)"/>
                <!-- arms -->
                <rect class="dp-hand" x="22" y="60" width="16" height="9" rx="4.5" fill="#9DB8E4"/>
                <rect x="94" y="76" width="16" height="9" rx="4.5" fill="#9DB8E4"/>
                <!-- head -->
                <rect x="30" y="16" width="72" height="58" rx="22" fill="url(#dpHead)"/>
                <!-- headphones -->
                <rect x="20" y="34" width="13" height="24" rx="6.5" fill="#5B7FC7"/>
                <rect x="99" y="34" width="13" height="24" rx="6.5" fill="#5B7FC7"/>
                <!-- visor -->
                <rect class="dp-visor" x="40" y="27" width="52" height="36" rx="17" fill="url(#dpVisor)"/>
                <circle class="dp-eye" cx="55" cy="44" r="6" fill="#22D3EE"/>
                <circle class="dp-eye" cx="77" cy="44" r="6" fill="#22D3EE"/>
                <rect class="dp-mouth" x="60" y="54" width="12" height="3" rx="1.5" fill="#22D3EE" opacity=".85"/>
                <!-- chest badge -->
                <circle cx="66" cy="87" r="7" fill="#0B1220" opacity=".55"/>
                <text x="66" y="90.5" text-anchor="middle" font-size="7" font-weight="700" fill="#93C5FD">DP</text>
              </svg>
            </div>
          </div>

          <div class="digipay-msg-bubble assistant digipay-welcome">${welcomeHtml}</div>
        </div>

        <div class="digipay-quick-chips">
          <div class="digipay-chip" data-msg="Check my wallet balance">
            <span class="dp-ic">💰</span><span class="dp-lb">Balance</span><span class="dp-sb">Wallet &amp; ledger</span>
          </div>
          <div class="digipay-chip" data-msg="Show my passbook for this month">
            <span class="dp-ic">📒</span><span class="dp-lb">Passbook</span><span class="dp-sb">This month</span>
          </div>
          <div class="digipay-chip" data-msg="Show my transaction history">
            <span class="dp-ic">🧾</span><span class="dp-lb">Transactions</span><span class="dp-sb">Recent activity</span>
          </div>
          <div class="digipay-chip" data-msg="What is my settlement status">
            <span class="dp-ic">🏦</span><span class="dp-lb">Settlement</span><span class="dp-sb">Payout status</span>
          </div>
          <div class="digipay-chip" data-msg="Summarise my transactions this month">
            <span class="dp-ic">📊</span><span class="dp-lb">Summary</span><span class="dp-sb">Monthly report</span>
          </div>
          <div class="digipay-chip" data-msg="Is my registered device active">
            <span class="dp-ic">📱</span><span class="dp-lb">Devices</span><span class="dp-sb">RD status</span>
          </div>
          <div class="digipay-chip" data-msg="Any notifications for me">
            <span class="dp-ic">🔔</span><span class="dp-lb">Alerts</span><span class="dp-sb">Notifications</span>
          </div>
          <div class="digipay-chip legacy" data-msg="What is my old digipay balance">
            <span class="dp-ic">🗄️</span><span class="dp-lb">Old balance</span><span class="dp-sb">Legacy system</span>
          </div>
          <div class="digipay-chip legacy" data-msg="Show my legacy passbook">
            <span class="dp-ic">🗂️</span><span class="dp-lb">Old passbook</span><span class="dp-sb">Legacy system</span>
          </div>
          <div class="digipay-chip help" data-msg="What is the AePS transaction limit">
            <span class="dp-ic">⚡</span><span class="dp-lb">AePS limit</span><span class="dp-sb">Check limits</span>
          </div>
          <div class="digipay-chip help" data-msg="What can you do">
            <span class="dp-ic">✨</span><span class="dp-lb">Capabilities</span><span class="dp-sb">What I can do</span>
          </div>
        </div>

        <!-- Rewards. Hidden unless the host app supplies real figures via
             config.rewards - see initDigiPayChat. Nothing here is invented. -->
        <div class="digipay-rewards">
          <div class="dp-rw-main">
            <div class="dp-rw-title dp-rw-heading"></div>
            <div class="dp-rw-sub dp-rw-note"></div>
            <div class="digipay-xp"><i></i></div>
          </div>
          <div class="digipay-coins"><span class="digipay-coin"></span><b class="dp-coin-n"></b></div>
        </div>

        <!-- Language sits on its own row: five controls in the footer squeezed the
             text input to almost nothing on a 380px panel. -->
        <div class="digipay-voice-bar">
          <select class="digipay-lang-select" title="Voice language" aria-label="Voice language"></select>
          <span class="digipay-voice-hint"></span>
          <span class="digipay-wave"><i></i><i></i><i></i><i></i><i></i></span>
        </div>

        <div class="digipay-chat-footer">
          <button class="digipay-mic-btn" title="Speak your question" aria-label="Speak your question" style="position:relative">
            <svg viewBox="0 0 24 24"><path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2z"/></svg>
          </button>
          <input class="digipay-chat-input" placeholder="Ask anything about DigiPay..." />
          <button class="digipay-speak-btn" title="Read replies aloud" aria-label="Read replies aloud">
            <svg viewBox="0 0 24 24"><path d="M3 10v4h4l5 5V5L7 10H3zm13.5 2a4.5 4.5 0 0 0-2.5-4.03v8.06A4.5 4.5 0 0 0 16.5 12zM14 3.23v2.06a6.98 6.98 0 0 1 0 13.42v2.06a9 9 0 0 0 0-17.54z"/></svg>
          </button>
          <button class="digipay-send-btn" aria-label="Send">➔</button>
        </div>

        <div class="digipay-shortcuts">
          <div class="digipay-sc" data-msg="What can you do">❓ FAQs</div>
          <div class="digipay-sc" data-msg="I want to raise a support ticket">🎫 Raise ticket</div>
          <div class="digipay-sc" data-msg="I want to talk to a human agent">🙋 Talk to agent</div>
          <div class="digipay-sc" data-msg="What is the AePS transaction limit">⚡ AePS limit</div>
        </div>

        <div class="digipay-nav">
          <button class="digipay-nav-item active" data-nav="home"><span class="dp-nic">🏠</span>Home</button>
          <button class="digipay-nav-item" data-nav="txn" data-msg="Show my transaction history"><span class="dp-nic">🧾</span>Transactions</button>
          <button class="digipay-nav-item center" data-nav="ai" aria-label="Ask the assistant"><span class="dp-nic">🎙️</span></button>
          <button class="digipay-nav-item" data-nav="rewards" data-msg="Summarise my transactions this month"><span class="dp-nic">🏆</span>Rewards</button>
          <button class="digipay-nav-item" data-nav="profile" data-msg="Show my profile and registered bank account"><span class="dp-nic">👤</span>Profile</button>
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

    // ==================================================================
    // Presentation layer: moods, particles, rewards, confetti, nav.
    //
    // Everything below is wired through MutationObserver and event handlers
    // rather than by editing appendMessage/handleSend/the voice code, so the
    // chat logic above stays exactly as it was and this can be deleted
    // wholesale without breaking the widget.
    // ==================================================================
    const reduceMotion = window.matchMedia
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const bot        = root.querySelector('.digipay-bot');
    const aurora     = root.querySelector('.digipay-aurora');
    const confettiEl = root.querySelector('.digipay-confetti');
    const waveEl     = root.querySelector('.digipay-wave');

    /** Robot expression. Falls back to 'happy' after transient moods. */
    let moodTimer = null;
    function setMood(mood, revertAfter) {
      if (!bot) return;
      bot.classList.remove('thinking', 'talking', 'listening', 'celebrate', 'wave');
      if (mood) bot.classList.add(mood);
      clearTimeout(moodTimer);
      if (revertAfter) {
        moodTimer = setTimeout(() => bot.classList.remove(mood), revertAfter);
      }
    }

    // Drifting particles. Purely decorative, so skipped entirely when the
    // user has asked for reduced motion.
    if (aurora && !reduceMotion) {
      for (let i = 0; i < 14; i++) {
        const p = document.createElement('span');
        p.className = 'digipay-particle';
        const size = 2 + Math.random() * 3;
        p.style.width = p.style.height = size + 'px';
        p.style.left = Math.random() * 100 + '%';
        p.style.bottom = '-10px';
        p.style.animationDuration = (10 + Math.random() * 14) + 's';
        p.style.animationDelay = (Math.random() * 12) + 's';
        aurora.appendChild(p);
      }
    }

    function confetti() {
      if (!confettiEl || reduceMotion) return;
      const colors = ['#2563EB', '#06B6D4', '#7C3AED', '#22C55E', '#F59E0B'];
      for (let i = 0; i < 26; i++) {
        const c = document.createElement('i');
        c.style.left = Math.random() * 100 + '%';
        c.style.background = colors[i % colors.length];
        c.style.animationDuration = (1.4 + Math.random() * 1.1) + 's';
        c.style.animationDelay = (Math.random() * .35) + 's';
        confettiEl.appendChild(c);
        setTimeout(() => c.remove(), 3000);
      }
    }

    // Watch the transcript instead of patching appendMessage(). Adds the
    // timestamp, drives the robot, and celebrates a real figure coming back.
    let lastConfetti = 0;
    if (body && window.MutationObserver) {
      new MutationObserver((records) => {
        records.forEach((rec) => {
          rec.addedNodes.forEach((node) => {
            if (!(node instanceof HTMLElement)) return;
            if (!node.classList.contains('digipay-msg-bubble')) return;

            if (node.classList.contains('digipay-typing-bubble')) {
              setMood('thinking');
              return;
            }
            if (!node.querySelector('.digipay-msg-time')) {
              const t = document.createElement('span');
              t.className = 'digipay-msg-time';
              t.textContent = new Date().toLocaleTimeString([], {
                hour: '2-digit', minute: '2-digit'
              });
              node.appendChild(t);
            }
            if (node.classList.contains('assistant')
                && !node.classList.contains('digipay-welcome')) {
              setMood('talking', 2600);
              // A highlighted figure means a real answer came back rather than
              // an error, which is the moment worth celebrating. Rate-limited
              // so a run of balance questions is not a party.
              const gotFigure = node.querySelector('.digipay-highlight');
              const failed = node.querySelector('.digipay-escalate-badge');
              if (gotFigure && !failed && Date.now() - lastConfetti > 30000) {
                lastConfetti = Date.now();
                setMood('celebrate', 1800);
                confetti();
              }
            }
          });
        });
      }).observe(body, { childList: true });
    }

    // Mirror the mic button's own state rather than duplicating the voice
    // logic, so the waveform can never disagree with what is really recording.
    if (micBtn && waveEl && window.MutationObserver) {
      new MutationObserver(() => {
        const on = micBtn.classList.contains('listening');
        waveEl.classList.toggle('on', on);
        if (on) setMood('listening');
        else if (bot) bot.classList.remove('listening');
      }).observe(micBtn, { attributes: true, attributeFilter: ['class'] });
    }

    // Ripple + magnetic pull on the action cards.
    root.querySelectorAll('.digipay-chip').forEach((chip) => {
      chip.addEventListener('pointerdown', (e) => {
        if (reduceMotion) return;
        const r = chip.getBoundingClientRect();
        const ink = document.createElement('span');
        ink.className = 'digipay-ripple';
        const d = Math.max(r.width, r.height);
        ink.style.width = ink.style.height = d + 'px';
        ink.style.left = (e.clientX - r.left - d / 2) + 'px';
        ink.style.top = (e.clientY - r.top - d / 2) + 'px';
        chip.appendChild(ink);
        setTimeout(() => ink.remove(), 600);
      });
    });

    if (!reduceMotion) {
      root.querySelectorAll('.digipay-chip, .digipay-sc, .digipay-nav-item').forEach((el) => {
        el.addEventListener('pointermove', (e) => {
          const r = el.getBoundingClientRect();
          const dx = (e.clientX - (r.left + r.width / 2)) / r.width;
          const dy = (e.clientY - (r.top + r.height / 2)) / r.height;
          el.style.transform = `translate(${dx * 4}px, ${dy * 3 - 3}px)`;
        });
        el.addEventListener('pointerleave', () => { el.style.transform = ''; });
      });
    }

    // Shortcut pills and the bottom nav both just ask a question, so they are
    // real controls rather than decoration. Home simply returns to the top.
    root.querySelectorAll('.digipay-sc').forEach((el) => {
      el.onclick = () => handleSend(el.getAttribute('data-msg'));
    });
    root.querySelectorAll('.digipay-nav-item').forEach((el) => {
      el.onclick = () => {
        root.querySelectorAll('.digipay-nav-item').forEach((n) => n.classList.remove('active'));
        el.classList.add('active');
        const nav = el.getAttribute('data-nav');
        if (nav === 'home') {
          body.scrollTo({ top: 0, behavior: 'smooth' });
          return;
        }
        if (nav === 'ai') {
          if (micBtn && micBtn.style.display !== 'none') micBtn.click();
          else input.focus();
          return;
        }
        const msg = el.getAttribute('data-msg');
        if (msg) handleSend(msg);
      };
    });

    // Send: brief particle burst, then let handleSend do the real work.
    if (sendBtn && !reduceMotion) {
      sendBtn.addEventListener('click', () => {
        sendBtn.animate(
          [{ transform: 'scale(1)' }, { transform: 'scale(.86)' }, { transform: 'scale(1)' }],
          { duration: 260, easing: 'cubic-bezier(.22,1,.36,1)' }
        );
      });
    }

    // ------------------------------------------------------------------
    // Rewards strip.
    //
    // Rendered ONLY from figures the host application passes in. There is no
    // endpoint for streaks or coins, and showing invented numbers next to real
    // balances would make the whole panel untrustworthy - so with no data the
    // strip stays hidden rather than displaying a plausible-looking default.
    //
    //   initDigiPayChat({ rewards: { streakDays: 7, coins: 230,
    //                                level: 'Level 8 Merchant', xpPercent: 72,
    //                                note: '6 transactions this month' } })
    // ------------------------------------------------------------------
    (function renderRewards() {
      const rw = config.rewards;
      if (!rw || typeof rw !== 'object') return;
      const strip   = root.querySelector('.digipay-rewards');
      const streak  = root.querySelector('.digipay-streak');
      const heading = root.querySelector('.dp-rw-heading');
      const note    = root.querySelector('.dp-rw-note');
      const xp      = root.querySelector('.digipay-xp i');
      const coinN   = root.querySelector('.dp-coin-n');

      if (Number.isFinite(rw.streakDays) && streak) {
        streak.querySelector('.dp-streak-n').textContent =
          `Streak ${rw.streakDays} day${rw.streakDays === 1 ? '' : 's'}`;
        streak.classList.add('on');
      }
      if (!strip) return;
      if (heading) heading.textContent = rw.level || "You're doing great!";
      if (note) note.textContent = rw.note || '';
      if (coinN && Number.isFinite(rw.coins)) {
        coinN.textContent = rw.coins + ' DP';
        // Count up, so the number feels earned rather than printed.
        if (!reduceMotion) {
          const target = rw.coins; const started = performance.now();
          const tick = (now) => {
            const p = Math.min(1, (now - started) / 900);
            coinN.textContent = Math.round(target * (1 - Math.pow(1 - p, 3))) + ' DP';
            if (p < 1) requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
        }
      } else if (coinN) {
        coinN.parentElement.style.display = 'none';
      }
      if (xp && Number.isFinite(rw.xpPercent)) {
        setTimeout(() => { xp.style.width = Math.max(0, Math.min(100, rw.xpPercent)) + '%'; }, 250);
      } else if (xp) {
        xp.parentElement.style.display = 'none';
      }
      strip.classList.add('on');
    })();

    // Wave hello the first time the panel is opened.
    if (launcher) {
      launcher.addEventListener('click', () => {
        if (win.classList.contains('open') && bot && !reduceMotion) {
          bot.classList.add('wave');
          setTimeout(() => bot.classList.remove('wave'), 3200);
        }
      });
    } else if (bot && !reduceMotion) {
      bot.classList.add('wave');
      setTimeout(() => bot.classList.remove('wave'), 3200);
    }

    sdk.authenticate();
  };
})();

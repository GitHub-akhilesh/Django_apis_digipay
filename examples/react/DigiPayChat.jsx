/**
 * DigiPayChat — React wrapper for the DigiPay chat widget.
 *
 * The widget is framework-agnostic DOM code (sdk/digipay-chat-widget.js), so
 * this component only loads the two scripts and drives initDigiPayChat().
 *
 * Why a component instead of the <digipay-chat> custom element:
 *   - it survives React 18 StrictMode, which double-invokes effects in dev.
 *     initDigiPayChat() appends a fresh widget on every call, so without a
 *     cleanup you get two launchers stacked on top of each other.
 *   - the same applies to Vite hot reload.
 *   - props can be objects (rewards), which HTML attributes cannot express.
 *
 * The plain custom element still works and is fine for a static page:
 *   <digipay-chat csc-id="…" api-mode="ai-platform" api-url="/ai-platform">
 */

import { useEffect, useRef } from 'react';

// Served from this app's own public/js so the version in the browser is the one
// in your repo. Point these at http://<host>/sdk/… to use the copies the
// backend serves instead (app/main.py mounts /sdk).
const SDK_SRC = '/js/digipay-chat-sdk.js';
const WIDGET_SRC = '/js/digipay-chat-widget.js';

const loading = new Map();

/** Load a script once per page, even if several instances mount together. */
function loadOnce(src) {
  if (loading.has(src)) return loading.get(src);
  const p = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      if (existing.dataset.loaded === '1') return resolve();
      existing.addEventListener('load', resolve, { once: true });
      existing.addEventListener('error', reject, { once: true });
      return;
    }
    const el = document.createElement('script');
    el.src = src;
    el.async = false; // the widget needs the SDK already defined
    el.addEventListener('load', () => { el.dataset.loaded = '1'; resolve(); }, { once: true });
    el.addEventListener('error', () => reject(new Error(`failed to load ${src}`)), { once: true });
    document.head.appendChild(el);
  });
  loading.set(src, p);
  return p;
}

export default function DigiPayChat({
  // Where the chat backend is. Keep this a SAME-ORIGIN path and proxy it:
  // the SDK sends credentials, and a browser rejects a credentialed request
  // answered with Access-Control-Allow-Origin: *. A relative path also keeps
  // working once this app is served over https, where a direct http:// call to
  // the platform would be blocked as mixed content.
  apiUrl = '/ai-platform',
  apiMode = 'ai-platform',          // 'ai-platform' (:8001) | 'legacy' (:8000)
  cscId,
  userName,                          // greeting stays generic when omitted
  rewards,                           // { streakDays, coins, level, xpPercent, note }
  mode = 'floating',                 // 'floating' | 'sidebar' | 'inline'
  theme = 'dark',
  tokenStorageKey = 'authToken',     // where this app keeps the DigiPay JWT
  token,                             // or pass the JWT directly
  voiceLang = 'en-IN',
  onError,
}) {
  const hostRef = useRef(null);
  // Objects would be a new reference every render and re-init the widget.
  const rewardsKey = rewards ? JSON.stringify(rewards) : '';

  useEffect(() => {
    let cancelled = false;
    const host = hostRef.current;

    (async () => {
      try {
        await loadOnce(SDK_SRC);
        await loadOnce(WIDGET_SRC);
        if (cancelled || !host) return;
        if (typeof window.initDigiPayChat !== 'function') {
          throw new Error('initDigiPayChat missing — widget script did not run');
        }
        host.innerHTML = '';   // StrictMode / hot-reload re-entry
        window.initDigiPayChat({
          targetElement: host,
          mode, apiMode, theme, voiceLang,
          baseUrl: apiUrl,
          cscId, userName, token, tokenStorageKey,
          rewards: rewardsKey ? JSON.parse(rewardsKey) : undefined,
        });
      } catch (err) {
        if (!cancelled) (onError || console.error)(err);
      }
    })();

    return () => {
      cancelled = true;
      // Remove the widget's DOM. The launcher and panel are position: fixed but
      // are children of this host, so clearing it takes them with it.
      if (host) host.innerHTML = '';
    };
  }, [apiUrl, apiMode, cscId, userName, mode, theme, voiceLang,
      token, tokenStorageKey, rewardsKey, onError]);

  return <div ref={hostRef} data-digipay-chat-host="" />;
}

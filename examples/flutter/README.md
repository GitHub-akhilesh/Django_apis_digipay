# DigiPay Chat — Flutter integration

There is no Flutter SDK, and the web widget cannot be reused natively: it is DOM
code (`document.createElement`, CSS, Web Speech API). So there are two honest
routes, and they trade off differently.

| | Native (`digipay_chat_screen.dart`) | WebView (`digipay_chat_webview.dart`) |
|---|---|---|
| UI | Material, yours to restyle | the exact web design |
| Voice input | works, via `speech_to_text` | **does not work** — see below |
| Offline/error handling | full control | whatever the page does |
| Effort to change look | normal Flutter | edit the shared web widget |
| Recommended | **yes, for a shipped app** | demos, or when visual parity matters more than voice |

Both hit the same endpoint, so you can start with the WebView and move later.

## Dependencies

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.0            # native route
  webview_flutter: ^4.8.0 # WebView route only

  # optional, for the native route:
  flutter_markdown: ^0.7.0  # replies are Markdown (bold figures, tables)
  speech_to_text: ^7.0.0    # voice input
  flutter_tts: ^4.0.0       # spoken replies
```

## Native route

```dart
import 'package:flutter/material.dart';
import 'digipay_chat_screen.dart';

Navigator.of(context).push(MaterialPageRoute(
  builder: (_) => DigiPayChatScreen(
    baseUrl: 'http://10.1.76.194:8001',
    token: myDigiPayJwt,          // the same JWT your app already holds
  ),
));
```

Or use the client on its own against your own UI:

```dart
final client = DigiPayChatClient(
  baseUrl: 'http://10.1.76.194:8001',
  token: myDigiPayJwt,
);

final reply = await client.sendMessage(
  sessionId: 'vle-523816200013-support',   // stable for the conversation
  message: 'what is my legacy wallet balance',
);
print(reply.message);   // "**Wallet balance (legacy system)** … ₹191.55 …"
```

### The request contract

```
POST {baseUrl}/api/v1/chat
Authorization: Bearer <DigiPay JWT>
Content-Type: application/json

{ "sessionId": "...", "message": "..." }
```

```json
{
  "success": true,
  "data": { "response": "...", "intent": "LEGACY_WALLET_BALANCE",
            "escalate": false, "policyChecked": true },
  "message": "Chat request processed successfully.",
  "traceId": "…", "requestId": "…", "timestamp": "…", "version": "v1"
}
```

**There is no `cscId` in the request.** `ChatRequest` accepts only `sessionId`
and `message`; the CSC ID comes from the verified token, so sending one is
ignored. Whoever the token belongs to is who the answer is about — which is also
why you must never let one user's token answer for another.

`sessionId` must be **stable for the whole conversation**. The platform keys its
short-term memory on it, so a fresh id per message loses all context.

Replies are **Markdown**. Add `flutter_markdown` and swap the `Text` widget in
`digipay_chat_screen.dart` for `MarkdownBody(data: m.text)` to get bold figures
and tables; the example stays dependency-free.

## WebView route

```dart
import 'digipay_chat_webview.dart';

Navigator.of(context).push(MaterialPageRoute(
  builder: (_) => DigiPayChatWebView(
    assetHost: 'http://10.1.76.194',        // serves /sdk/*.js
    platformUrl: 'http://10.1.76.194:8001',
    token: myDigiPayJwt,
    userName: 'Akhilesh',
  ),
));
```

### Voice input does not work here

`SpeechRecognition` is a Chrome feature backed by a recognition service; it is
**not exposed in Android WebView or iOS WKWebView**. The widget detects this and
hides the mic button rather than leaving a dead control, so the panel still
works — you simply get no dictation. Speech *output* may work where the platform
provides `speechSynthesis`.

If voice matters, take the native route and use `speech_to_text` /`flutter_tts`,
which use the OS engines and need only a microphone permission.

### Plain http needs an opt-in on both platforms

`http://10.1.76.194` is cleartext, which modern Android and iOS block by
default. For a dev/UAT build:

```xml
<!-- android/app/src/main/AndroidManifest.xml -->
<application android:usesCleartextTraffic="true" …>
```

```xml
<!-- ios/Runner/Info.plist — dev only, do not ship -->
<key>NSAppTransportSecurity</key>
<dict><key>NSAllowsArbitraryLoads</key><true/></dict>
```

Put the service behind https before production rather than shipping these.

## Reaching the host

The device, not your laptop, has to resolve `10.1.76.194` — so it needs to be on
the same network or VPN. Two things that catch people out:

* **Android emulator**: `10.0.2.2` is the host machine, not `localhost`.
* **Physical device**: use the LAN address of whatever serves the platform.

The chat platform binds `0.0.0.0:8001`, so it is reachable from the LAN; there
is no proxy in front of it. (The web/React integration proxies the call for CORS
and mixed-content reasons — neither applies to a native HTTP client, so Flutter
can call `:8001` directly.)

## Behaviour worth knowing before you file a bug

* **"Your DigiPay session has expired"** is correct for a token the DigiPay
  gateway does not recognise, not an outage. The gateway authenticates from a
  real session and keeps server-side state. Legacy-backed questions ("what is my
  legacy wallet balance") work with any token the platform can verify; gateway
  ones need a genuine user session.
* **`escalate: true`** means the question went to a human — no further answer is
  coming in that turn. The example surfaces it under the bubble.
* The assistant is **read-only by design**. It cannot move money, and it cannot
  create, update or cancel anything; those endpoints are refused before a socket
  is opened. Do not build a UI that implies otherwise.

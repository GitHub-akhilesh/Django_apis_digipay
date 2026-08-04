/// WebView route: reuse the full web widget inside a Flutter app.
///
/// Use this when you want the exact web UI (aurora background, robot avatar,
/// action cards) without rebuilding it natively. Use digipay_chat_screen.dart
/// instead when you want a native-feeling screen or working voice input.
///
/// Read the caveats below before choosing — one of them is likely to matter.
library digipay_chat_webview;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

class DigiPayChatWebView extends StatefulWidget {
  const DigiPayChatWebView({
    super.key,
    required this.assetHost,
    required this.platformUrl,
    required this.token,
    this.cscId,
    this.userName,
  });

  /// Host serving the SDK files, e.g. http://10.1.76.194 (app/main.py mounts
  /// /sdk). Must be reachable from the device, not just from your laptop.
  final String assetHost;

  /// Chat platform base URL, e.g. http://10.1.76.194:8001
  final String platformUrl;

  /// DigiPay JWT, injected so the page does not have to log in again.
  final String token;

  final String? cscId;
  final String? userName;

  @override
  State<DigiPayChatWebView> createState() => _DigiPayChatWebViewState();
}

class _DigiPayChatWebViewState extends State<DigiPayChatWebView> {
  late final WebViewController _controller;
  String? _error;

  String get _html => '''
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
  <style>html,body{margin:0;height:100%;background:#060B18;}</style>
</head>
<body>
  <script>
    // Seed the token before the widget initialises: it reads the JWT from
    // localStorage["authToken"] at construction time.
    try { localStorage.setItem('authToken', ${_jsString(widget.token)}); } catch (e) {}
  </script>
  <script src="${widget.assetHost}/sdk/digipay-chat-sdk.js"></script>
  <script src="${widget.assetHost}/sdk/digipay-chat-widget.js"></script>
  <script>
    window.addEventListener('load', function () {
      if (typeof window.initDigiPayChat !== 'function') {
        document.body.innerHTML =
          '<p style="color:#f88;font:14px sans-serif;padding:16px">'
          + 'Could not load the DigiPay chat SDK from ${widget.assetHost}/sdk/.</p>';
        return;
      }
      window.initDigiPayChat({
        // inline, not floating: the WebView already IS the panel, so a launcher
        // bubble the user has to tap inside a full-screen view is just friction.
        mode: 'inline',
        apiMode: 'ai-platform',
        baseUrl: ${_jsString(widget.platformUrl)},
        cscId: ${_jsString(widget.cscId ?? '')},
        userName: ${_jsString(widget.userName ?? '')},
        tokenStorageKey: 'authToken'
      });
    });
  </script>
</body>
</html>
''';

  /// Embed a Dart string as a JS string literal.
  ///
  /// jsonEncode does the quoting, escaping and control characters correctly —
  /// hand-rolled replaceAll chains get this wrong. '<' is then escaped as well
  /// so a value containing "</script>" cannot terminate the script block and
  /// inject markup; < is a valid escape inside a JS string.
  static String _jsString(String v) =>
      jsonEncode(v).replaceAll('<', r'\u003C');

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFF060B18))
      ..setNavigationDelegate(NavigationDelegate(
        onWebResourceError: (e) {
          if (mounted) setState(() => _error = e.description);
        },
      ))
      // baseUrl matters: it becomes the page origin, so the widget's relative
      // requests and localStorage are scoped to the asset host rather than
      // about:blank (where localStorage throws on some platforms).
      ..loadHtmlString(_html, baseUrl: Uri.parse(widget.assetHost));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('DigiPay Support AI')),
      body: _error != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text('Could not load the assistant.\n\n$_error',
                    textAlign: TextAlign.center),
              ),
            )
          : WebViewWidget(controller: _controller),
    );
  }
}

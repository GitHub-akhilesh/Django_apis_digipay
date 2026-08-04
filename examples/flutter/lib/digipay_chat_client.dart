/// DigiPay chat client for Flutter.
///
/// The web widget is DOM code and cannot be reused natively, but the backend it
/// talks to is plain HTTP + JWT, so a native client is a thin wrapper.
///
/// Contract, taken from ai_platform/api/routers/chat.py:
///
///   POST {baseUrl}/api/v1/chat
///   Authorization: Bearer <DigiPay JWT>
///   Content-Type: application/json
///   { "sessionId": "...", "message": "..." }
///
///   200 {
///     "success": true,
///     "data": { "response": "...", "intent": "...",
///               "escalate": false, "policyChecked": true },
///     "message": "Chat request processed successfully.",
///     "traceId": "...", "requestId": "...", "timestamp": "...", "version": "v1"
///   }
///
/// Note there is no cscId in the request. ChatRequest accepts only sessionId and
/// message; the CSC ID is derived from the verified token
/// (principal.merchant_id), so sending one would be ignored. Whoever the token
/// belongs to is who the answer is about.
library digipay_chat_client;

import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

/// One assistant turn.
class DigiPayReply {
  const DigiPayReply({
    required this.message,
    this.intent,
    this.escalate = false,
    this.policyChecked = true,
    this.traceId,
  });

  final String message;
  final String? intent;

  /// True when the assistant handed the question to a human. Worth surfacing:
  /// it means no answer is coming in this session.
  final bool escalate;
  final bool policyChecked;

  /// Include this when reporting a problem — it ties to the server-side log.
  final String? traceId;
}

/// Raised for anything the caller may want to react to differently.
class DigiPayChatException implements Exception {
  DigiPayChatException(this.message, {this.statusCode, this.kind});

  final String message;
  final int? statusCode;

  /// unauthorized | notJson | server | network | timeout
  final String? kind;

  bool get isUnauthorized => kind == 'unauthorized';

  @override
  String toString() => 'DigiPayChatException($kind, $statusCode): $message';
}

class DigiPayChatClient {
  DigiPayChatClient({
    required this.baseUrl,
    required this.token,
    this.timeout = const Duration(seconds: 90),
    http.Client? httpClient,
  }) : _http = httpClient ?? http.Client();

  /// e.g. https://digipay.example.gov.in  or  http://10.1.76.194:8001
  final String baseUrl;

  /// The DigiPay JWT. The platform verifies it and forwards it to the gateway,
  /// so downstream calls act as the user rather than a service account.
  final String token;

  final Duration timeout;
  final http.Client _http;

  Uri _uri(String path) =>
      Uri.parse('${baseUrl.replaceAll(RegExp(r'/+$'), '')}$path');

  /// Send one message and await the full reply.
  ///
  /// [sessionId] must be stable for the life of the conversation: the platform
  /// keys its short-term memory on it, so a fresh id each turn loses context.
  Future<DigiPayReply> sendMessage({
    required String sessionId,
    required String message,
  }) async {
    final http.Response res;
    try {
      res = await _http
          .post(
            _uri('/api/v1/chat'),
            headers: {
              'Authorization': 'Bearer $token',
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: jsonEncode({'sessionId': sessionId, 'message': message}),
          )
          .timeout(timeout);
    } on TimeoutException {
      throw DigiPayChatException(
        'The assistant did not reply in time.',
        kind: 'timeout',
      );
    } catch (e) {
      throw DigiPayChatException('Could not reach DigiPay: $e', kind: 'network');
    }

    if (res.statusCode == 401 || res.statusCode == 403) {
      throw DigiPayChatException(
        'Your DigiPay session is not valid. Please sign in again.',
        statusCode: res.statusCode,
        kind: 'unauthorized',
      );
    }

    // A 200 that is not JSON means the request never reached the chat service —
    // usually a proxy or gateway in front answering with an HTML error page.
    // Distinguished from an outage because the fix is different.
    final contentType = (res.headers['content-type'] ?? '').toLowerCase();
    if (!contentType.contains('json')) {
      final preview = res.body.trim();
      throw DigiPayChatException(
        'Expected JSON but got "${contentType.isEmpty ? 'no content-type' : contentType}". '
        'The request did not reach the chat service. '
        'Body starts: ${preview.substring(0, preview.length.clamp(0, 100))}',
        statusCode: res.statusCode,
        kind: 'notJson',
      );
    }

    final Map<String, dynamic> body =
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;

    if (res.statusCode >= 400 || body['success'] == false) {
      throw DigiPayChatException(
        (body['message'] ?? body['detail'] ?? 'The assistant returned an error.')
            .toString(),
        statusCode: res.statusCode,
        kind: 'server',
      );
    }

    final data = (body['data'] as Map<String, dynamic>?) ?? const {};
    return DigiPayReply(
      // 'response' is the field the REST endpoint returns; the others are
      // tolerated so a future rename does not blank the bubble.
      message: (data['response'] ?? data['message'] ?? '').toString(),
      intent: data['intent'] as String?,
      escalate: data['escalate'] == true,
      policyChecked: data['policyChecked'] != false,
      traceId: body['traceId'] as String?,
    );
  }

  void dispose() => _http.close();
}

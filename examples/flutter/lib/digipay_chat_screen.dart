/// A native Flutter chat screen for the DigiPay assistant.
///
/// Deliberately plain Material: the point is a correct, working integration you
/// can restyle, not a reimplementation of the web widget's visuals.
library digipay_chat_screen;

import 'package:flutter/material.dart';

import 'digipay_chat_client.dart';

class DigiPayChatScreen extends StatefulWidget {
  const DigiPayChatScreen({
    super.key,
    required this.baseUrl,
    required this.token,
    this.sessionId,
    this.greeting =
        'Namaste! Ask me about your balance, passbook, transactions, '
        'settlements or devices.',
  });

  final String baseUrl;
  final String token;

  /// Stable for the whole conversation. Generated once if omitted; pass your own
  /// if you want the thread to survive the screen being rebuilt.
  final String? sessionId;
  final String greeting;

  @override
  State<DigiPayChatScreen> createState() => _DigiPayChatScreenState();
}

class _Msg {
  _Msg(this.text, this.fromUser, {this.escalated = false});
  final String text;
  final bool fromUser;
  final bool escalated;
}

class _DigiPayChatScreenState extends State<DigiPayChatScreen> {
  late final DigiPayChatClient _client;
  late final String _sessionId;
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<_Msg> _messages = [];
  bool _sending = false;

  static const _suggestions = <String, String>{
    'Balance': 'what is my wallet balance',
    'Old balance': 'what is my legacy wallet balance',
    'Passbook': 'show my passbook for this month',
    'Transactions': 'show my transaction history',
    'AePS limit': 'what is the AePS transaction limit',
  };

  @override
  void initState() {
    super.initState();
    _client = DigiPayChatClient(baseUrl: widget.baseUrl, token: widget.token);
    // Not cryptographic — it only has to be unique per conversation.
    _sessionId = widget.sessionId ??
        'flutter-${DateTime.now().microsecondsSinceEpoch}';
    _messages.add(_Msg(widget.greeting, false));
  }

  @override
  void dispose() {
    _client.dispose();
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _scrollToEnd() {
    // After the frame, or the extent is still the pre-insert one.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _send(String text) async {
    final message = text.trim();
    if (message.isEmpty || _sending) return;

    setState(() {
      _messages.add(_Msg(message, true));
      _sending = true;
      _input.clear();
    });
    _scrollToEnd();

    try {
      final reply = await _client.sendMessage(
        sessionId: _sessionId,
        message: message,
      );
      if (!mounted) return;
      setState(() => _messages.add(
            _Msg(reply.message, false, escalated: reply.escalate),
          ));
    } on DigiPayChatException catch (e) {
      if (!mounted) return;
      // Say what the person can do, not what the transport did.
      final friendly = switch (e.kind) {
        'unauthorized' =>
          'Your DigiPay session has ended. Please sign in again, then ask me once more.',
        'notJson' =>
          'I reached DigiPay but not the assistant service. Please try again shortly.',
        'timeout' => 'That took too long. Please try again.',
        'network' =>
          "I can't connect to DigiPay right now. Please check your connection.",
        _ => 'Sorry, something went wrong. Please try again in a moment.',
      };
      setState(() => _messages.add(_Msg(friendly, false)));
      debugPrint('[DigiPayChat] $e');
    } finally {
      if (mounted) setState(() => _sending = false);
      _scrollToEnd();
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text('DigiPay Support AI'),
        bottom: _sending
            ? const PreferredSize(
                preferredSize: Size.fromHeight(2),
                child: LinearProgressIndicator(minHeight: 2),
              )
            : null,
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: ListView.builder(
                controller: _scroll,
                padding: const EdgeInsets.all(12),
                itemCount: _messages.length,
                itemBuilder: (_, i) {
                  final m = _messages[i];
                  return Align(
                    alignment:
                        m.fromUser ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      margin: const EdgeInsets.symmetric(vertical: 4),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 10),
                      constraints: BoxConstraints(
                        maxWidth: MediaQuery.of(context).size.width * 0.82,
                      ),
                      decoration: BoxDecoration(
                        color: m.fromUser
                            ? scheme.primary
                            : scheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // The backend replies in Markdown. Render it with
                          // flutter_markdown for bold figures and tables; this
                          // keeps the example dependency-free.
                          Text(
                            m.text,
                            style: TextStyle(
                              color: m.fromUser
                                  ? scheme.onPrimary
                                  : scheme.onSurface,
                              height: 1.35,
                            ),
                          ),
                          if (m.escalated)
                            Padding(
                              padding: const EdgeInsets.only(top: 8),
                              child: Text(
                                'A support colleague has been notified',
                                style: TextStyle(
                                    fontSize: 11, color: scheme.tertiary),
                              ),
                            ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: Row(
                children: _suggestions.entries
                    .map((e) => Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: ActionChip(
                            label: Text(e.key),
                            onPressed: _sending ? null : () => _send(e.value),
                          ),
                        ))
                    .toList(),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _input,
                      enabled: !_sending,
                      textInputAction: TextInputAction.send,
                      onSubmitted: _send,
                      decoration: const InputDecoration(
                        hintText: 'Ask anything about DigiPay…',
                        border: OutlineInputBorder(),
                        isDense: true,
                        contentPadding:
                            EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: _sending ? null : () => _send(_input.text),
                    icon: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

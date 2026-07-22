export function markdownPlugin() {
    return {
        name: 'markdown-plugin',
        onMessageReceived: (msg) => {
            // Strips extra markdown formatting or sanitizes html strings if needed
            return msg;
        }
    };
}
export function analyticsPlugin(onEvent) {
    return {
        name: 'analytics-plugin',
        onInit: (client) => {
            if (client && client.on) {
                client.on('message', (msg) => {
                    if (onEvent)
                        onEvent('chat_message_sent', { role: msg.role, intent: msg.intent });
                });
                client.on('escalate', (msg) => {
                    if (onEvent)
                        onEvent('chat_escalated', { cscId: client.cscId });
                });
            }
        }
    };
}
//# sourceMappingURL=index.js.map
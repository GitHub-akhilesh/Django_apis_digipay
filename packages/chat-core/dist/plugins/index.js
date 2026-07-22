"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.markdownPlugin = markdownPlugin;
exports.analyticsPlugin = analyticsPlugin;
function markdownPlugin() {
    return {
        name: 'markdown-plugin',
        onMessageReceived: (msg) => {
            // Strips extra markdown formatting or sanitizes html strings if needed
            return msg;
        }
    };
}
function analyticsPlugin(onEvent) {
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

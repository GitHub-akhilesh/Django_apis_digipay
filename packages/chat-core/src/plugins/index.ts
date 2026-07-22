/**
 * Default Plugin implementations for @digipay/chat-core
 */
import { ChatPlugin, ChatMessage } from '../types';

export function markdownPlugin(): ChatPlugin {
  return {
    name: 'markdown-plugin',
    onMessageReceived: (msg: ChatMessage) => {
      // Strips extra markdown formatting or sanitizes html strings if needed
      return msg;
    }
  };
}

export function analyticsPlugin(onEvent?: (eventName: string, payload: any) => void): ChatPlugin {
  return {
    name: 'analytics-plugin',
    onInit: (client: any) => {
      if (client && client.on) {
        client.on('message', (msg: ChatMessage) => {
          if (onEvent) onEvent('chat_message_sent', { role: msg.role, intent: msg.intent });
        });
        client.on('escalate', (msg: ChatMessage) => {
          if (onEvent) onEvent('chat_escalated', { cscId: client.cscId });
        });
      }
    }
  };
}

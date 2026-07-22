import React from 'react';
import { ChatClient, ChatClientOptions, ChatMessage } from '@digipay/chat-core';
export interface ChatContextValue {
    client: ChatClient | null;
    messages: ChatMessage[];
    isTyping: boolean;
    isEscalated: boolean;
    sendMessage: (text: string) => Promise<any>;
    seedTestData: () => Promise<any>;
}
export interface ChatProviderProps extends ChatClientOptions {
    children: React.ReactNode;
}
export declare const ChatProvider: React.FC<ChatProviderProps>;
export declare const useChatContext: () => ChatContextValue;

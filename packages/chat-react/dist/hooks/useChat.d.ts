export declare function useChat(): {
    client: import("@digipay/chat-core").ChatClient;
    sendMessage: (text: string) => Promise<any>;
    seedTestData: () => Promise<any>;
    isTyping: boolean;
    isEscalated: boolean;
};
export declare function useMessages(): import("@digipay/chat-core").ChatMessage[];
export declare function useSession(): string;

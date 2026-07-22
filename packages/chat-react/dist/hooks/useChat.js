"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.useChat = useChat;
exports.useMessages = useMessages;
exports.useSession = useSession;
const ChatContext_1 = require("../context/ChatContext");
function useChat() {
    const { client, sendMessage, seedTestData, isTyping, isEscalated } = (0, ChatContext_1.useChatContext)();
    return {
        client,
        sendMessage,
        seedTestData,
        isTyping,
        isEscalated
    };
}
function useMessages() {
    const { messages } = (0, ChatContext_1.useChatContext)();
    return messages;
}
function useSession() {
    const { client } = (0, ChatContext_1.useChatContext)();
    return client ? client.sessionId : null;
}

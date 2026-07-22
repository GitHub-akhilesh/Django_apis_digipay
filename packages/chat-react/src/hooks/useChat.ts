import { useChatContext } from '../context/ChatContext';

export function useChat() {
  const { client, sendMessage, seedTestData, isTyping, isEscalated } = useChatContext();
  return {
    client,
    sendMessage,
    seedTestData,
    isTyping,
    isEscalated
  };
}

export function useMessages() {
  const { messages } = useChatContext();
  return messages;
}

export function useSession() {
  const { client } = useChatContext();
  return client ? client.sessionId : null;
}

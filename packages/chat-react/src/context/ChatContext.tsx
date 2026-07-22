import React, { createContext, useContext, useEffect, useState } from 'react';
import { ChatClient, ChatClientOptions, ChatMessage } from '@digipay/chat-core';

export interface ChatContextValue {
  client: ChatClient | null;
  messages: ChatMessage[];
  isTyping: boolean;
  isEscalated: boolean;
  sendMessage: (text: string) => Promise<any>;
  seedTestData: () => Promise<any>;
}

const ChatContext = createContext<ChatContextValue | undefined>(undefined);

export interface ChatProviderProps extends ChatClientOptions {
  children: React.ReactNode;
}

export const ChatProvider: React.FC<ChatProviderProps> = ({ children, ...options }) => {
  const [client] = useState(() => new ChatClient(options));
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [isEscalated, setIsEscalated] = useState<boolean>(false);

  useEffect(() => {
    const unsubMsg = client.on('message', (msg: ChatMessage) => {
      setMessages([...client.history]);
    });

    const unsubTyping = client.on('typing', (typing: boolean) => {
      setIsTyping(typing);
    });

    const unsubEscalate = client.on('escalate', () => {
      setIsEscalated(true);
    });

    client.authenticate();

    return () => {
      unsubMsg();
      unsubTyping();
      unsubEscalate();
      client.destroy();
    };
  }, [client]);

  const sendMessage = async (text: string) => {
    return await client.sendMessage(text);
  };

  const seedTestData = async () => {
    return await client.seedTestData();
  };

  return (
    <ChatContext.Provider
      value={{
        client,
        messages,
        isTyping,
        isEscalated,
        sendMessage,
        seedTestData
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChatContext = (): ChatContextValue => {
  const ctx = useContext(ChatContext);
  if (!ctx) {
    throw new Error('useChatContext must be used within a <ChatProvider>');
  }
  return ctx;
};

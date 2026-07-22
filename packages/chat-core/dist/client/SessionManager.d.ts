/**
 * SessionManager service for handling chat sessions, token caching, and storage.
 */
import { ChatSession } from '../types';
export declare class SessionManager {
    private keyPrefix;
    getOrCreateSession(cscId: string, customSessionId?: string): ChatSession;
    clearSession(cscId: string): void;
}

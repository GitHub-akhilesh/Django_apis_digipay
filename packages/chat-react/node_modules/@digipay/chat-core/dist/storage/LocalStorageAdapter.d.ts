/**
 * LocalStorage and MemoryStorage Adapters for @digipay/chat-core
 */
import { StorageAdapter } from './StorageAdapter';
export declare class MemoryStorageAdapter implements StorageAdapter {
    private store;
    getItem(key: string): string | null;
    setItem(key: string, value: string): void;
    removeItem(key: string): void;
}
export declare class LocalStorageAdapter implements StorageAdapter {
    private fallback;
    private isAvailable;
    getItem(key: string): string | null;
    setItem(key: string, value: string): void;
    removeItem(key: string): void;
}

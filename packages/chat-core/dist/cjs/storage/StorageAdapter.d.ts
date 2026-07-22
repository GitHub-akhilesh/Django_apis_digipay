/**
 * Storage Adapter Interface for @digipay/chat-core (Milestone A)
 */
export interface StorageAdapter {
    getItem(key: string): Promise<string | null> | string | null;
    setItem(key: string, value: string): Promise<void> | void;
    removeItem(key: string): Promise<void> | void;
}
//# sourceMappingURL=StorageAdapter.d.ts.map
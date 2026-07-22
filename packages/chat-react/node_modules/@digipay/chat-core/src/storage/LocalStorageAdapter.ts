/**
 * LocalStorage and MemoryStorage Adapters for @digipay/chat-core
 */
import { StorageAdapter } from './StorageAdapter';

export class MemoryStorageAdapter implements StorageAdapter {
  private store = new Map<string, string>();

  getItem(key: string): string | null {
    return this.store.get(key) || null;
  }

  setItem(key: string, value: string): void {
    this.store.set(key, value);
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }
}

export class LocalStorageAdapter implements StorageAdapter {
  private fallback = new MemoryStorageAdapter();

  private isAvailable(): boolean {
    return typeof localStorage !== 'undefined';
  }

  getItem(key: string): string | null {
    if (this.isAvailable()) {
      return localStorage.getItem(key);
    }
    return this.fallback.getItem(key);
  }

  setItem(key: string, value: string): void {
    if (this.isAvailable()) {
      localStorage.setItem(key, value);
    } else {
      this.fallback.setItem(key, value);
    }
  }

  removeItem(key: string): void {
    if (this.isAvailable()) {
      localStorage.removeItem(key);
    } else {
      this.fallback.removeItem(key);
    }
  }
}

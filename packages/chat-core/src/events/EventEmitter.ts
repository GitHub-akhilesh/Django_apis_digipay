/**
 * Typed Event Emitter for DigiPay Chat Core SDK (Phase 3)
 */

type EventCallback<T = any> = (data: T) => void;

export class TypedEventEmitter {
  private listeners: Map<string, EventCallback[]> = new Map();

  on<T = any>(event: string, callback: EventCallback<T>): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)!.push(callback);

    // Return unsubscribe function
    return () => this.off(event, callback);
  }

  off(event: string, callback: EventCallback): void {
    const list = this.listeners.get(event);
    if (list) {
      this.listeners.set(
        event,
        list.filter(cb => cb !== callback)
      );
    }
  }

  emit<T = any>(event: string, data?: T): void {
    const list = this.listeners.get(event);
    if (list) {
      list.forEach(cb => cb(data));
    }
  }
}

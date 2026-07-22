/**
 * Typed Event Emitter for DigiPay Chat Core SDK (Phase 3)
 */
type EventCallback<T = any> = (data: T) => void;
export declare class TypedEventEmitter {
    private listeners;
    on<T = any>(event: string, callback: EventCallback<T>): () => void;
    off(event: string, callback: EventCallback): void;
    emit<T = any>(event: string, data?: T): void;
}
export {};

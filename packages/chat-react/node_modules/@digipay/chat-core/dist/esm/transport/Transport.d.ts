/**
 * Transport Layer Interface for @digipay/chat-core (Milestone A)
 */
export interface TransportRequest {
    url: string;
    method?: string;
    headers?: Record<string, string>;
    body?: any;
}
export interface TransportResponse<T = any> {
    status: number;
    ok: boolean;
    data: T;
}
export interface Transport {
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send<T = any>(request: TransportRequest): Promise<TransportResponse<T>>;
}
//# sourceMappingURL=Transport.d.ts.map
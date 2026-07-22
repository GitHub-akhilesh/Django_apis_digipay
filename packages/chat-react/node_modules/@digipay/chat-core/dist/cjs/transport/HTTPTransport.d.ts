/**
 * HTTP Transport Implementation using fetch API
 */
import { Transport, TransportRequest, TransportResponse } from './Transport';
export declare class HTTPTransport implements Transport {
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send<T = any>(req: TransportRequest): Promise<TransportResponse<T>>;
}
//# sourceMappingURL=HTTPTransport.d.ts.map
/**
 * Middleware Pipeline System for @digipay/chat-core (Milestone A)
 */
import { TransportRequest, TransportResponse } from '../transport/Transport';
export type MiddlewareNext = (req: TransportRequest) => Promise<TransportResponse>;
export type MiddlewareFunction = (req: TransportRequest, next: MiddlewareNext) => Promise<TransportResponse>;
export declare class MiddlewarePipeline {
    private middlewares;
    use(middleware: MiddlewareFunction): void;
    execute(initialReq: TransportRequest, finalHandler: (req: TransportRequest) => Promise<TransportResponse>): Promise<TransportResponse>;
}
export declare function loggerMiddleware(): MiddlewareFunction;

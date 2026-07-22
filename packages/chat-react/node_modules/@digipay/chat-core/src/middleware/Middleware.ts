/**
 * Middleware Pipeline System for @digipay/chat-core (Milestone A)
 */
import { TransportRequest, TransportResponse } from '../transport/Transport';

export type MiddlewareNext = (req: TransportRequest) => Promise<TransportResponse>;

export type MiddlewareFunction = (
  req: TransportRequest,
  next: MiddlewareNext
) => Promise<TransportResponse>;

export class MiddlewarePipeline {
  private middlewares: MiddlewareFunction[] = [];

  use(middleware: MiddlewareFunction): void {
    this.middlewares.push(middleware);
  }

  async execute(
    initialReq: TransportRequest,
    finalHandler: (req: TransportRequest) => Promise<TransportResponse>
  ): Promise<TransportResponse> {
    let index = -1;

    const dispatch = async (i: number, req: TransportRequest): Promise<TransportResponse> => {
      if (i <= index) {
        throw new Error('next() called multiple times');
      }
      index = i;

      if (i === this.middlewares.length) {
        return finalHandler(req);
      }

      const middleware = this.middlewares[i];
      return middleware(req, (nextReq) => dispatch(i + 1, nextReq));
    };

    return dispatch(0, initialReq);
  }
}

export function loggerMiddleware(): MiddlewareFunction {
  return async (req, next) => {
    console.log(`[DigiPay SDK Request] ${req.method || 'POST'} ${req.url}`);
    const res = await next(req);
    console.log(`[DigiPay SDK Response] ${res.status} OK=${res.ok}`);
    return res;
  };
}

export class MiddlewarePipeline {
    constructor() {
        this.middlewares = [];
    }
    use(middleware) {
        this.middlewares.push(middleware);
    }
    async execute(initialReq, finalHandler) {
        let index = -1;
        const dispatch = async (i, req) => {
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
export function loggerMiddleware() {
    return async (req, next) => {
        console.log(`[DigiPay SDK Request] ${req.method || 'POST'} ${req.url}`);
        const res = await next(req);
        console.log(`[DigiPay SDK Response] ${res.status} OK=${res.ok}`);
        return res;
    };
}
//# sourceMappingURL=Middleware.js.map
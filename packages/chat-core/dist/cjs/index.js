"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * Main export entrypoint for @digipay/chat-core (Milestone A)
 */
__exportStar(require("./types"), exports);
__exportStar(require("./events/EventEmitter"), exports);
__exportStar(require("./transport/Transport"), exports);
__exportStar(require("./transport/HTTPTransport"), exports);
__exportStar(require("./storage/StorageAdapter"), exports);
__exportStar(require("./storage/LocalStorageAdapter"), exports);
__exportStar(require("./auth/AuthProvider"), exports);
__exportStar(require("./auth/JWTAuthProvider"), exports);
__exportStar(require("./middleware/Middleware"), exports);
__exportStar(require("./client/SessionManager"), exports);
__exportStar(require("./client/ChatClient"), exports);
__exportStar(require("./plugins"), exports);
//# sourceMappingURL=index.js.map
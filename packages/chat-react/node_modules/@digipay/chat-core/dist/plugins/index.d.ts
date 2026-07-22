/**
 * Default Plugin implementations for @digipay/chat-core
 */
import { ChatPlugin } from '../types';
export declare function markdownPlugin(): ChatPlugin;
export declare function analyticsPlugin(onEvent?: (eventName: string, payload: any) => void): ChatPlugin;

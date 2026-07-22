import React from 'react';
export interface DigiPayChatWidgetProps {
    cscId?: string;
    baseUrl?: string;
    username?: string;
    position?: 'bottom-right' | 'bottom-left';
    mode?: 'floating' | 'inline' | 'sidebar';
}
export declare const DigiPayChatWidget: React.FC<DigiPayChatWidgetProps>;

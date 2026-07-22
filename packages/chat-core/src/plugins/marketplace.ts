/**
 * DigiPay Chat SDK — Modular Plugin Marketplace Infrastructure
 * Defines plug-and-play extensions for Markdown, Analytics, Voice Input, Attachments, and Feedback.
 */

export interface IChatPlugin {
  name: string;
  version: string;
  onInit?: (client: any) => void;
  onMessageSent?: (message: string) => void;
  onResponseReceived?: (response: any) => void;
  onError?: (error: Error) => void;
}

export class MarkdownPlugin implements IChatPlugin {
  name = 'digipay-plugin-markdown';
  version = '1.0.0';

  onResponseReceived(response: any) {
    // Markdown formatting hook
    if (typeof response === 'string') {
      return response.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }
  }
}

export class AnalyticsPlugin implements IChatPlugin {
  name = 'digipay-plugin-analytics';
  version = '1.0.0';

  onMessageSent(message: string) {
    console.log(`[Analytics] Tracked message event: length=${message.length}`);
  }
}

export class VoicePlugin implements IChatPlugin {
  name = 'digipay-plugin-voice';
  version = '1.0.0';

  startListening(): void {
    console.log('[VoicePlugin] Speech recognition activated.');
  }
}

export class AttachmentPlugin implements IChatPlugin {
  name = 'digipay-plugin-attachment';
  version = '1.0.0';

  uploadAttachment(file: File): Promise<string> {
    return Promise.resolve(`https://cdn.digipay.com/attachments/${file.name}`);
  }
}

export class FeedbackPlugin implements IChatPlugin {
  name = 'digipay-plugin-feedback';
  version = '1.0.0';

  submitRating(messageId: string, rating: number, comment?: string) {
    return { status: 'submitted', messageId, rating, comment };
  }
}

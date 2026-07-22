import React from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { DigiPayChatWidget } from '../components/DigiPayChatWidget';

const meta: Meta<typeof DigiPayChatWidget> = {
  title: 'DigiPay/DigiPayChatWidget',
  component: DigiPayChatWidget,
  tags: ['autodocs'],
  argTypes: {
    cscId: { control: 'text' },
    mode: { control: 'select', options: ['floating', 'sidebar', 'inline'] },
    theme: { control: 'select', options: ['light', 'dark', 'system'] },
    primaryColor: { control: 'color' },
  },
};

export default meta;
type Story = StoryObj<typeof DigiPayChatWidget>;

export const FloatingMode: Story = {
  args: { cscId: '500100100014', mode: 'floating', theme: 'dark' },
};

export const SidebarMode: Story = {
  args: { cscId: '500100100014', mode: 'sidebar', theme: 'light' },
};

export const InlineMode: Story = {
  args: { cscId: '500100100014', mode: 'inline', theme: 'dark' },
};

export const EmptyChat: Story = {
  args: { cscId: '500100100014', mode: 'inline', theme: 'dark' },
};

export const LongConversation: Story = {
  args: { cscId: '500100100014', mode: 'inline', theme: 'light' },
};

export const MarkdownResponse: Story = {
  args: { cscId: '500100100014', mode: 'inline', theme: 'dark' },
};

export const ErrorState: Story = {
  args: { cscId: '500100100014', mode: 'floating', theme: 'dark' },
};

export const TypingIndicator: Story = {
  args: { cscId: '500100100014', mode: 'floating', theme: 'light' },
};

export const ReconnectMode: Story = {
  args: { cscId: '500100100014', mode: 'floating', theme: 'dark' },
};

export const OfflineMode: Story = {
  args: { cscId: '500100100014', mode: 'floating', theme: 'dark' },
};

export const RTLLayout: Story = {
  args: { cscId: '500100100014', mode: 'inline', theme: 'dark' },
};

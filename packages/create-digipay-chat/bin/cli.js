#!/usr/bin/env node

/**
 * create-digipay-chat CLI Scaffolder
 * Usage: npx create-digipay-chat [project-directory] --template [react|vite|next|html]
 */

const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const projectDir = args[0] || 'my-digipay-chat-app';

console.log('==================================================');
console.log('⚡ DigiPay Chat SDK Project Scaffolder CLI (v2.0.0-RC1)');
console.log('==================================================');
console.log(`\n🚀 Initializing DigiPay Chat starter template in: ./${projectDir}\n`);

const sampleTemplate = `import React from 'react';
import { DigiPayChatWidget } from '@digipay/chat-react';

export default function App() {
  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>DigiPay Merchant Portal App</h1>
      <DigiPayChatWidget cscId="500100100014" mode="floating" theme="dark" />
    </div>
  );
}
`;

try {
  const targetPath = path.resolve(process.cwd(), projectDir);
  if (!fs.existsSync(targetPath)) {
    fs.mkdirSync(targetPath, { recursive: true });
  }

  fs.writeFileSync(path.join(targetPath, 'App.jsx'), sampleTemplate, 'utf8');

  console.log('✅ Template successfully generated!');
  console.log('\nNext steps:');
  console.log(`  1. cd ${projectDir}`);
  console.log('  2. npm install @digipay/chat-react');
  console.log('  3. npm run dev\n');
} catch (err) {
  console.error('❌ Failed to scaffold project:', err.message);
  process.exit(1);
}

import type { Metadata } from 'next';
import './globals.css';
import './retro.css';
import './features.css';
export const metadata: Metadata = { title: 'Mirova — Ideas, connected.', description: 'Your Miro boards and research, connected to a grounded Gemini copilot.' };
export default function RootLayout({children}: Readonly<{children:React.ReactNode}>) { return <html lang="en"><head><link rel="preconnect" href="https://fonts.googleapis.com"/><link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous"/><link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,500;12..96,600;12..96,700&family=Instrument+Sans:wght@400;500;600;700&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet"/></head><body>{children}</body></html> }

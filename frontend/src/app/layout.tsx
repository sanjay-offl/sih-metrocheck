import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { ToastProvider } from '@/components/ui/toast';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata: Metadata = {
  title: 'MetroCheck | Legal Metrology Compliance System',
  description:
    'AI-powered compliance checking for packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans`}>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
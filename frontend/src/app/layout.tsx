import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import '@/styles/globals.css';
import { SessionProvider } from '@/store/sessionStore';
import { ConfigProvider } from '@/store/configStore';
import { NegotiationProvider } from '@/store/negotiationStore';
import { Header } from '@/components/Header';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Multi-Agent Marketplace',
  description: 'Simulate ecommerce negotiations with AI-powered buyer & sellers',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <SessionProvider>
          <ConfigProvider>
            <NegotiationProvider>
              <Header />
              {children}
            </NegotiationProvider>
          </ConfigProvider>
        </SessionProvider>
      </body>
    </html>
  );
}


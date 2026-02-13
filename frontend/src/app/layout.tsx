import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'Eco-Lens: Virtual Air Quality Matrix',
  description:
    'Real-time air quality monitoring dashboard with virtual sensor data visualization, pollution forecasting, and health impact analysis.',
  keywords: [
    'air quality',
    'pollution monitoring',
    'AQI',
    'environmental dashboard',
    'sensor data',
  ],
  authors: [{ name: 'Eco-Lens Team' }],
  themeColor: '#0a0e17',
  viewport: 'width=device-width, initial-scale=1',
  icons: {
    icon: '/favicon.ico',
  },
  openGraph: {
    title: 'Eco-Lens: Virtual Air Quality Matrix',
    description:
      'Turn traffic cameras into pollution sensors using Computer Vision + Environmental Physics.',
    images: [{ url: '/og-image.png', width: 1200, height: 630 }],
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body
        className={`${inter.className} bg-navy-950 text-[#f0f4f8] min-h-screen antialiased`}
      >
        {children}
      </body>
    </html>
  );
}

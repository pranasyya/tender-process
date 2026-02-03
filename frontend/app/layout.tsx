import React from "react"
import type { Metadata } from 'next'
import { Plus_Jakarta_Sans, Space_Grotesk } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import { TenderProvider } from '@/app/context/TenderContext'
import { ThemeProvider } from '@/app/context/ThemeContext'
import { LayoutContent } from '@/app/LayoutContent'
import './globals.css'

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Megha AI - Tender Discovery',
  description: 'Discover and analyze government tenders with Megha AI-powered insights',
  generator: 'v0.app',
  icons: {
    icon: '/meghaai.png',
    apple: '/meghaai.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${plusJakarta.variable} ${spaceGrotesk.variable} font-sans antialiased`}>
        <ThemeProvider>
          <TenderProvider>
            <LayoutContent>
              {children}
            </LayoutContent>
            <Analytics />
          </TenderProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}

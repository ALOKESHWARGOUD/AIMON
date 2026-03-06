import type { Metadata } from 'next'
import '../styles/globals.css'

export const metadata: Metadata = {
  title: 'AIMON Dashboard - AI Monitoring Control Center',
  description: 'Real-time monitoring dashboard for the AIMON AI Monitoring Framework',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="font-sans bg-slate-950 text-slate-100 min-h-screen" suppressHydrationWarning>
        {children}
      </body>
    </html>
  )
}

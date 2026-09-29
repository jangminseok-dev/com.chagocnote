import type { Metadata, Viewport } from 'next'
import localFont from 'next/font/local'
import type { ReactNode } from 'react'

import './globals.css'

// 가변 글꼴 하나는 2MB 라 무겁다. 쓰는 굵기 셋의 subset 만 직접 싣는다(외부 도메인 요청 없음).
const pretendard = localFont({
  src: [
    { path: '../node_modules/pretendard/dist/web/static/woff2-subset/Pretendard-Regular.subset.woff2', weight: '400' },
    { path: '../node_modules/pretendard/dist/web/static/woff2-subset/Pretendard-SemiBold.subset.woff2', weight: '600' },
    { path: '../node_modules/pretendard/dist/web/static/woff2-subset/Pretendard-Bold.subset.woff2', weight: '700' },
  ],
  display: 'swap',
})

export const metadata: Metadata = {
  title: '차곡노트 미용 알림장',
  robots: { index: false, follow: false },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#f5f5f5',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko" className={pretendard.className}>
      <body>{children}</body>
    </html>
  )
}

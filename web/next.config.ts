import type { NextConfig } from 'next'

const config: NextConfig = {
  poweredByHeader: false,
  // next dev 가 AGENTS.md·CLAUDE.md 를 만들지 않게 한다.
  agentRules: false,
  // 백엔드가 만드는 링크는 http://127.0.0.1:3010/r/… 다. next dev 는 localhost 만 믿으므로 이 이름을 더한다.
  allowedDevOrigins: ['127.0.0.1'],
  // next dev 는 들어온 요청의 주소(토큰이 든 /r/…)를 찍는다. 끈다(next start 는 원래 찍지 않는다).
  logging: { incomingRequests: false },
  async headers() {
    return [
      {
        // 정적 파일(글꼴 등)과 공통 미리보기 그림은 뺀다 — 토큰과 상관없고, 미리보기 로봇이 캐시 금지 그림을 버릴 수 있다.
        source: '/((?!_next/static/|og-default\\.png$).*)',
        headers: [
          { key: 'X-Robots-Tag', value: 'noindex, nofollow' },
          { key: 'Cache-Control', value: 'private, no-store' },
          { key: 'Referrer-Policy', value: 'no-referrer' },
        ],
      },
    ]
  },
}

export default config

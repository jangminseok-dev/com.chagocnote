import type { NextConfig } from 'next'

const config: NextConfig = {
  poweredByHeader: false,
  // next dev 가 AGENTS.md·CLAUDE.md 를 만들지 않게 한다.
  agentRules: false,
  async headers() {
    return [
      {
        // 정적 파일(글꼴 등)은 뺀다 — 주소에 해시가 있어 오래 캐시해도 된다.
        source: '/((?!_next/static/).*)',
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

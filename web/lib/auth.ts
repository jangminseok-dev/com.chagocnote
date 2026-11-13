import { authBaseUrl } from './config'

export type LoginResult = { kind: 'ok'; accessToken: string; expiresIn: number } | { kind: 'rejected' | 'unavailable' }

const TIMEOUT_MS = 5000

/**
 * 웹 세션 로그인. 인증 프로세스가 30분짜리 액세스 토큰 하나만 준다(리프레시 없음).
 * 웹 서버가 인증 프로세스에서 부르는 경로는 이것 하나다.
 */
export async function webLogin(provider: 'dev', token: string): Promise<LoginResult> {
  try {
    const res = await fetch(`${authBaseUrl()}/v1/auth/social`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, token, session: 'web' }),
      cache: 'no-store',
      signal: AbortSignal.timeout(TIMEOUT_MS),
    })
    if (res.status === 200) {
      const body = (await res.json()) as { access_token?: unknown; refresh_token?: unknown; expires_in?: unknown }
      // 리프레시 토큰이 왔다면 웹 세션이 아니다. 쿠키에 넣지 않고 버린다.
      if (body.refresh_token !== null) return { kind: 'unavailable' }
      if (typeof body.access_token !== 'string' || typeof body.expires_in !== 'number' || body.expires_in <= 0) {
        return { kind: 'unavailable' }
      }
      return { kind: 'ok', accessToken: body.access_token, expiresIn: body.expires_in }
    }
    const rejected = res.status >= 400 && res.status < 500 && res.status !== 429
    return { kind: rejected ? 'rejected' : 'unavailable' }
  } catch {
    // 연결 실패, 시간 초과, 깨진 JSON
    return { kind: 'unavailable' }
  }
}

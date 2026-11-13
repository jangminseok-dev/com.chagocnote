import { cookies } from 'next/headers'
import { secureCookies } from './config'
import { open, seal } from './seal'
import { isTokenShaped } from './token'

export const SESSION_COOKIE = 'cn_session'
export const CLAIM_COOKIE = 'cn_claim'
/** 잇기 쿠키가 사는 시간 — 로그인하는 동안만 알림장 토큰을 들고 있는다. */
export const CLAIM_TTL_SECONDS = 600

/** 웹 세션. 30분짜리 액세스 토큰 하나이고 연장하지 않는다. expiresAt 은 초다. */
export type Session = { accessToken: string; expiresAt: number }

const now = () => Math.floor(Date.now() / 1000)

function options(maxAge: number) {
  return { httpOnly: true, sameSite: 'lax' as const, path: '/', maxAge, secure: secureCookies() }
}

/** 세션을 읽는다. 쿠키가 없거나 열리지 않거나 시간이 지났으면 null 이다. */
export async function readSession(): Promise<Session | null> {
  const sealed = (await cookies()).get(SESSION_COOKIE)?.value
  if (!sealed) return null
  const plain = await open('session', sealed)
  if (plain === null) return null
  try {
    const { t, e } = JSON.parse(plain) as { t?: unknown; e?: unknown }
    if (typeof t !== 'string' || typeof e !== 'number' || e <= now()) return null
    return { accessToken: t, expiresAt: e }
  } catch {
    return null
  }
}

/** 세션 쿠키를 쓴다. 쿠키의 수명은 토큰의 수명과 같다. 경로 핸들러에서만 부른다. */
export async function writeSession(accessToken: string, expiresIn: number): Promise<void> {
  const sealed = await seal('session', JSON.stringify({ t: accessToken, e: now() + expiresIn }))
  ;(await cookies()).set(SESSION_COOKIE, sealed, options(expiresIn))
}

export async function clearSession(): Promise<void> {
  ;(await cookies()).delete(SESSION_COOKIE)
}

/** 로그인하고 돌아와 이을 알림장 토큰을 잠깐 맡긴다. */
export async function writeClaim(reportToken: string): Promise<void> {
  ;(await cookies()).set(CLAIM_COOKIE, await seal('claim', reportToken), options(CLAIM_TTL_SECONDS))
}

/** 맡긴 토큰을 꺼내고 쿠키를 지운다. 없거나 토큰 모양이 아니면 null 이다. */
export async function takeClaim(): Promise<string | null> {
  const store = await cookies()
  const sealed = store.get(CLAIM_COOKIE)?.value
  if (!sealed) return null
  store.delete(CLAIM_COOKIE)
  const token = await open('claim', sealed)
  return token !== null && isTokenShaped(token) ? token : null
}

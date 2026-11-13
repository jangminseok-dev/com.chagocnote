import { notFound, redirect } from 'next/navigation'
import type { Failure } from './guardian'
import { readSession, type Session } from './session'

// 내 기록 아래의 페이지가 함께 쓰는 것. 페이지는 쿠키를 읽기만 한다(쓰는 일은 경로 핸들러가 한다).

const loginFor = (here: string) => `/login?next=${encodeURIComponent(here)}`

/** 세션을 준다. 없으면(끝났으면) 로그인으로 보내고, 로그인 뒤 here 로 돌아온다. here 는 safeNext 가 받는 경로여야 한다. */
export async function requireSession(here: string): Promise<Session> {
  return (await readSession()) ?? redirect(loginFor(here))
}

/**
 * 백엔드 호출이 실패했을 때 — 토큰이 끝났으면 로그인으로, 없는 것이면 404 로 떠나고,
 * 남는 둘(정지된 계정, 닿지 못함)은 그릴 오류 화면의 종류를 준다.
 */
export function screenFor(failure: Failure, here: string): 'forbidden' | 'unavailable' {
  if (failure.kind === 'unauthenticated') redirect(loginFor(here))
  if (failure.kind === 'not_found') notFound()
  return failure.kind
}

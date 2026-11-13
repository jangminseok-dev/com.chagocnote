import { isCrossSite, seeOther } from '../../lib/origin'
import { clearSession } from '../../lib/session'

/** 로그아웃. 쿠키를 지운다 — 토큰은 30분 뒤 스스로 끝난다. */
export async function POST(request: Request) {
  if (isCrossSite(request)) return new Response(null, { status: 403 })
  await clearSession()
  return seeOther('/login')
}

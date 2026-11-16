import { isCrossSite, seeOther } from '../../lib/origin'
import { clearClaim, clearJoin, clearSession } from '../../lib/session'

/** 로그아웃. 쿠키를 지운다 — 토큰은 30분 뒤 스스로 끝난다. */
export async function POST(request: Request) {
  if (isCrossSite(request)) return new Response(null, { status: 403 })
  await clearSession()
  // 로그인하다 만 사람이 맡겨 둔 알림장 토큰도 버린다 — 다음에 로그인하는 사람의 계정에 이어지지 않게.
  await clearClaim()
  await clearJoin()   // 맡겨 둔 가족 초대 코드도(⑫)
  return seeOther('/login')
}

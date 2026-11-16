import { devLogin } from '../../../../lib/config'
import { joinFamily } from '../../../../lib/guardian'
import { isCrossSite, seeOther } from '../../../../lib/origin'
import { clearSession, readSession, writeJoin } from '../../../../lib/session'
import { isTokenShaped } from '../../../../lib/token'

/**
 * 가족으로 잇는다(⑫). 로그인돼 있으면 바로 잇고, 아니면 코드를 잠깐 사는 쿠키(cn_join)에 맡기고 로그인으로 보낸다 —
 * 코드가 든 주소를 새로 만들지 않는다. 잇지 못하면(없음·쓰임·가득·잦음) 내 기록의 한 가지 안내로 간다.
 */
export async function POST(request: Request, { params }: { params: Promise<{ code: string }> }) {
  if (!devLogin()) return new Response(null, { status: 404 })
  if (isCrossSite(request)) return new Response(null, { status: 403 })
  const { code } = await params
  if (!isTokenShaped(code)) return new Response(null, { status: 404 })
  const session = await readSession()
  if (session !== null) {
    const joined = await joinFamily(session.accessToken, code)
    if (joined !== 'unauthenticated') return seeOther(joined === 'joined' ? '/me' : '/me?notice=invite')
    await clearSession()
  }
  await writeJoin(code)
  return seeOther('/login')
}

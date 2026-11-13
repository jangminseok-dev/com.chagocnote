import { devLogin } from '../../../../lib/config'
import { claimLink } from '../../../../lib/guardian'
import { isCrossSite, seeOther } from '../../../../lib/origin'
import { clearSession, readSession, writeClaim } from '../../../../lib/session'
import { isTokenShaped } from '../../../../lib/token'

/**
 * 받은 알림장으로 계정을 잇는다(알림장 꼬리의 버튼).
 * 로그인돼 있으면 바로 잇고, 아니면 토큰을 잠깐 사는 쿠키에 맡기고 로그인으로 보낸다 — 토큰이 든 주소를 새로 만들지 않는다.
 */
export async function POST(request: Request, { params }: { params: Promise<{ token: string }> }) {
  // 로그인할 수단이 없으면 버튼도 없고 이 경로도 없다.
  if (!devLogin()) return new Response(null, { status: 404 })
  if (isCrossSite(request)) return new Response(null, { status: 403 })
  const { token } = await params
  if (!isTokenShaped(token)) return new Response(null, { status: 404 })

  const session = await readSession()
  if (session !== null) {
    const claimed = await claimLink(session.accessToken, token)
    // 닫힘·없음·횟수 초과·연결 실패는 말없이 내 기록으로 간다. 이미 이어진 보호자면 기록이 보인다.
    if (claimed !== 'unauthenticated') return seeOther(claimed === 'taken' ? '/me?notice=taken' : '/me')
    await clearSession()
  }
  await writeClaim(token)
  return seeOther('/login')
}

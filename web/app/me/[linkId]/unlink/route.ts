import { endLink } from '../../../../lib/guardian'
import { idFrom } from '../../../../lib/next-path'
import { isCrossSite, seeOther } from '../../../../lib/origin'
import { clearSession, readSession } from '../../../../lib/session'

/** 보호자가 연결을 끊는다. 끊은 뒤 내 기록으로 돌아간다. */
export async function POST(request: Request, { params }: { params: Promise<{ linkId: string }> }) {
  if (isCrossSite(request)) return new Response(null, { status: 403 })
  const linkId = idFrom((await params).linkId)
  if (linkId === null) return new Response(null, { status: 404 })

  const session = await readSession()
  if (session === null) return seeOther('/login')

  // 이미 끊긴 연결(404)이나 닿지 못한 경우도 내 기록으로 간다 — 목록이 지금 상태를 보여 준다.
  if ((await endLink(session.accessToken, linkId)) !== 'unauthenticated') return seeOther('/me')
  await clearSession()
  return seeOther('/login')
}

import { createInvite } from '../../../../lib/guardian'
import { idFrom } from '../../../../lib/next-path'
import { isCrossSite } from '../../../../lib/origin'
import { clearSession, readSession } from '../../../../lib/session'

const NO_STORE = { 'Cache-Control': 'no-store' }

/**
 * 가족 초대를 만든다(⑫). 브라우저 스크립트가 부르고, 초대 주소의 경로(`/j/<코드>`)만 JSON 으로 받아 공유 시트·복사로 넘긴다.
 * 코드를 페이지 주소·쿠키에 싣지 않고 기록하지 않는다. 응답은 저장되지 않는다.
 */
export async function POST(request: Request, { params }: { params: Promise<{ linkId: string }> }) {
  if (isCrossSite(request)) return new Response(null, { status: 403 })
  const linkId = idFrom((await params).linkId)
  if (linkId === null) return new Response(null, { status: 404 })
  const session = await readSession()
  if (session === null) return new Response(null, { status: 401 })
  const made = await createInvite(session.accessToken, linkId)
  if (made.kind === 'ok') return Response.json({ path: `/j/${made.code}` }, { headers: NO_STORE })
  if (made.kind === 'unauthenticated') {
    await clearSession()
    return new Response(null, { status: 401 })
  }
  const status = { full: 409, busy: 429, not_found: 404, unavailable: 503 }[made.kind]
  return new Response(null, { status, headers: NO_STORE })
}

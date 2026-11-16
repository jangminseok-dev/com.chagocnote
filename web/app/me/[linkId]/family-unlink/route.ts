import { endFamily } from '../../../../lib/guardian'
import { idFrom } from '../../../../lib/next-path'
import { isCrossSite, seeOther } from '../../../../lib/origin'
import { clearSession, readSession } from '../../../../lib/session'

/** 기본 보호자가 가족 한 명(family_id), 없으면 모두를 끊는다(⑫). 끊은 뒤 내 기록으로 돌아간다. */
export async function POST(request: Request, { params }: { params: Promise<{ linkId: string }> }) {
  if (isCrossSite(request)) return new Response(null, { status: 403 })
  const linkId = idFrom((await params).linkId)
  if (linkId === null) return new Response(null, { status: 404 })
  let familyId: number | null = null
  try {
    const raw = (await request.formData()).get('family_id')
    if (typeof raw === 'string' && raw !== '') {
      familyId = idFrom(raw)
      if (familyId === null) return new Response(null, { status: 404 })
    }
  } catch {
    // 본문이 없으면 모두 끊기다.
  }
  const session = await readSession()
  if (session === null) return seeOther('/login')
  if ((await endFamily(session.accessToken, linkId, familyId)) !== 'unauthenticated') return seeOther('/me')
  await clearSession()
  return seeOther('/login')
}

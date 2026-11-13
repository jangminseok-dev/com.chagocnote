import { webLogin } from '../../../lib/auth'
import { devLogin } from '../../../lib/config'
import { claimLink } from '../../../lib/guardian'
import { safeNext } from '../../../lib/next-path'
import { isCrossSite, seeOther } from '../../../lib/origin'
import { takeClaim, writeSession } from '../../../lib/session'

const text = (value: FormDataEntryValue | null) => (typeof value === 'string' ? value : '')

/** 개발용 로그인(이름 한 칸). 설정이 꺼져 있으면 없는 경로다. */
export async function POST(request: Request) {
  if (!devLogin()) return new Response(null, { status: 404 })
  if (isCrossSite(request)) return new Response(null, { status: 403 })

  let form: FormData
  try {
    form = await request.formData()
  } catch {
    return seeOther('/login?error=1')
  }
  const next = safeNext(text(form.get('next')))
  const failed = next === '/me' ? '/login?error=1' : `/login?error=1&next=${encodeURIComponent(next)}`

  const name = text(form.get('name')).trim()
  if (name.length < 1 || name.length > 50) return seeOther(failed)

  const result = await webLogin('dev', name)
  if (result.kind !== 'ok') return seeOther(failed)

  await writeSession(result.accessToken, result.expiresIn)

  // 알림장의 버튼으로 왔으면 맡겨 둔 토큰으로 잇고 내 기록으로 간다. 로그인이 실패했을 때는 꺼내지 않는다(위에서 돌아갔다).
  const reportToken = await takeClaim()
  if (reportToken === null) return seeOther(next)
  const claimed = await claimLink(result.accessToken, reportToken)
  return seeOther(claimed === 'taken' ? '/me?notice=taken' : '/me')
}

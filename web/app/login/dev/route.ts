import { webLogin } from '../../../lib/auth'
import { devLogin } from '../../../lib/config'
import { safeNext } from '../../../lib/next-path'
import { isCrossSite, seeOther } from '../../../lib/origin'
import { writeSession } from '../../../lib/session'

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
  return seeOther(next)
}

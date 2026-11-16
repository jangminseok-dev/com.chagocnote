import { clientIpFrom } from '../../../../lib/client-ip'
import { submitIntake } from '../../../../lib/form'
import { isCrossSite } from '../../../../lib/origin'

// 백엔드의 상한과 같다(동의서 제출과 같은 한도).
const MAX_BODY_BYTES = 131_072

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

/**
 * 문진표 제출. 보호자의 브라우저가 적은 것을 보내면 웹 서버가 백엔드로 넘기고, 상태 코드만 본문 없이 돌려준다.
 * 본문(이름·전화번호·적은 글)을 기록에 남기지 않는다. 칸의 규칙은 백엔드가 본다 — 여기서는 모양만 본다.
 */
export async function POST(request: Request, { params }: { params: Promise<{ token: string }> }) {
  // 다른 사이트가 보호자의 브라우저로 문진표를 내게 하지 않는다. 헤더가 없는 옛 브라우저는 통과한다.
  if (isCrossSite(request)) return new Response(null, { status: 403 })

  // 본문을 읽기 전에 크기를 본다 — 길이를 밝히지 않은 본문도 받지 않는다.
  const length = request.headers.get('content-length') ?? ''
  if (!/^\d+$/.test(length) || Number(length) > MAX_BODY_BYTES) return new Response(null, { status: 413 })

  let body: unknown
  try {
    body = await request.json()
  } catch {
    return new Response(null, { status: 422 })
  }
  if (!isObject(body) || !isObject(body.pet) || typeof body.privacy_agreed !== 'boolean') {
    return new Response(null, { status: 422 })
  }

  const { token } = await params
  const status = await submitIntake(token, clientIpFrom(request.headers), body)
  return new Response(null, { status })
}

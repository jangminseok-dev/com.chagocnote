import { clientIpFrom } from '../../../../lib/client-ip'
import { submitConsent } from '../../../../lib/form'
import { isCrossSite } from '../../../../lib/origin'

// 서명 그림 65,536바이트의 base64(87,384글자)와 나머지 칸을 넉넉히 덮는다. 백엔드의 상한과 같다.
const MAX_BODY_BYTES = 131_072

function text(value: unknown): value is string {
  return typeof value === 'string'
}

/**
 * 동의서 제출. 보호자의 브라우저가 서명한 것을 보내면 웹 서버가 백엔드로 넘기고, 상태 코드만 본문 없이 돌려준다.
 * 본문(이름·서명)을 기록에 남기지 않는다.
 */
export async function POST(request: Request, { params }: { params: Promise<{ token: string }> }) {
  // 다른 사이트가 보호자의 브라우저로 서명을 내게 하지 않는다. 헤더가 없는 옛 브라우저는 통과한다.
  if (isCrossSite(request)) return new Response(null, { status: 403 })

  // 본문을 읽기 전에 크기를 본다 — 길이를 밝히지 않은 본문도 받지 않는다.
  const length = request.headers.get('content-length') ?? ''
  if (!/^\d+$/.test(length) || Number(length) > MAX_BODY_BYTES) return new Response(null, { status: 413 })

  let body: Record<string, unknown>
  try {
    body = (await request.json()) as Record<string, unknown>
  } catch {
    return new Response(null, { status: 422 })
  }
  if (body === null || typeof body !== 'object') return new Response(null, { status: 422 })
  const { doc_digest, signer_name, signature_png } = body
  if (!text(doc_digest) || !text(signer_name) || !text(signature_png)) return new Response(null, { status: 422 })

  const { token } = await params
  const status = await submitConsent(token, clientIpFrom(request.headers), { doc_digest, signer_name, signature_png })
  return new Response(null, { status })
}

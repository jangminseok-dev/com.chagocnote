import { clientIpFrom } from '../../../../lib/client-ip'
import { markViewed } from '../../../../lib/report'

/** 열람 신호. 알림장 화면이 브라우저에서 열렸을 때 보낸다. 백엔드의 상태 코드를 본문 없이 돌려준다. */
export async function POST(request: Request, { params }: { params: Promise<{ token: string }> }) {
  // 다른 사이트가 보호자의 브라우저로 신호를 보내게 하지 않는다. 헤더가 없는 옛 브라우저는 통과한다.
  const site = request.headers.get('sec-fetch-site')
  if (site !== null && site !== 'same-origin') return new Response(null, { status: 403 })

  const { token } = await params
  return new Response(null, { status: await markViewed(token, clientIpFrom(request.headers)) })
}

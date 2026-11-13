/**
 * 다른 사이트가 보호자의 브라우저로 보낸 요청인가. 상태를 바꾸는 경로가 먼저 본다.
 * 헤더가 없는 옛 브라우저는 통과한다(쿠키의 SameSite=Lax 가 막는다).
 */
export function isCrossSite(request: Request): boolean {
  const site = request.headers.get('sec-fetch-site')
  return site !== null && site !== 'same-origin'
}

/** 폼 POST 뒤의 이동. 주소는 상대 경로 그대로 둔다 — 요청의 Host 로 절대 주소를 만들지 않는다. */
export function seeOther(path: string): Response {
  return new Response(null, { status: 303, headers: { Location: path } })
}

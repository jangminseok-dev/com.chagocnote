/**
 * 보호자의 접속 주소 — x-forwarded-for 의 첫 값.
 * Vercel 은 이 헤더를 플랫폼이 덮어쓴다. 직접 노출한 서버에서는 위조할 수 있다.
 */
export function clientIpFrom(headers: Headers): string | null {
  const first = headers.get('x-forwarded-for')?.split(',')[0].trim()
  return first || null
}

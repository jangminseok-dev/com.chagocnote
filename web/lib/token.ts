// 백엔드가 만드는 토큰은 URL 안전 base64 43글자다. 자바스크립트의 $ 는 (m 없이) 끝의 줄바꿈 앞에서 맞지 않는다.
const TOKEN = /^[A-Za-z0-9_-]{43}$/

/** 토큰의 모양인가. 아니면 백엔드를 부르지 않는다. */
export function isTokenShaped(value: string): boolean {
  return TOKEN.test(value)
}

// 주소에서 온 글자를 믿기 전에 모양을 본다. 자바스크립트의 $ 는 끝의 줄바꿈 앞에서 맞지 않는다.

// 15자리까지 — 자바스크립트의 안전한 정수 안이다.
const ID = '[1-9]\\d{0,14}'
const ID_ONLY = new RegExp(`^${ID}$`)
const NEXT = new RegExp(`^/me(/${ID}){0,2}(\\?pet=${ID})?$`)
const CURSOR = /^[A-Za-z0-9_=-]{1,300}$/

/** 로그인 뒤 돌아갈 경로. 내 기록 아래의 경로만 받고 그 밖은 /me 다 — 다른 사이트로 내보내지 않는다. */
export function safeNext(value: string | null | undefined): string {
  return value && NEXT.test(value) ? value : '/me'
}

/** 경로·질의의 숫자. 양의 정수 모양이 아니면 null 이다. */
export function idFrom(value: string | undefined): number | null {
  return value !== undefined && ID_ONLY.test(value) ? Number(value) : null
}

/** 쪽 표시. 모양이 틀리면 없는 것으로 친다. */
export function cursorFrom(value: string | undefined): string | null {
  return value !== undefined && CURSOR.test(value) ? value : null
}

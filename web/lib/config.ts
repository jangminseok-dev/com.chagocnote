// 설정은 서버에서만 읽는다. process.env 를 읽는 곳은 이 파일 하나다.

function required(name: string): string {
  const value = process.env[name]
  // 값은 메시지에 넣지 않는다.
  if (!value) throw new Error(`환경 변수 ${name} 이 없다.`)
  return value
}

/** 백엔드 주소. 끝의 / 는 뗀다. */
export function apiBaseUrl(): string {
  return required('API_BASE_URL').replace(/\/+$/, '')
}

/** 백엔드와 나눈 비밀값. 맞을 때만 백엔드가 웹이 보낸 접속 주소를 믿는다. */
export function webSecret(): string {
  return required('REPORT_WEB_SECRET')
}

/** 인증 프로세스 주소(로그인). 끝의 / 는 뗀다. */
export function authBaseUrl(): string {
  return required('AUTH_BASE_URL').replace(/\/+$/, '')
}

/** 세션·잇기 쿠키를 봉하는 비밀값. 32글자 이상이어야 한다. */
export function sessionSecret(): string {
  const value = required('WEB_SESSION_SECRET')
  // 값은 메시지에 넣지 않는다.
  if (value.length < 32) throw new Error('환경 변수 WEB_SESSION_SECRET 이 32글자보다 짧다.')
  return value
}

/** 개발용 로그인을 그리고 받는가. 기본은 꺼짐이다. */
export function devLogin(): boolean {
  return process.env.DEV_LOGIN === '1'
}

/** 쿠키에 Secure 를 붙이는가. 로컬(next dev)은 http 라 붙이지 않는다. */
export function secureCookies(): boolean {
  return process.env.NODE_ENV === 'production'
}

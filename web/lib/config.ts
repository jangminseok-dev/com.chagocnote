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

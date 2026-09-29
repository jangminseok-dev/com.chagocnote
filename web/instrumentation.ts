import { apiBaseUrl, webSecret } from './lib/config'

/** 서버가 뜰 때 한 번 불린다. 필수 설정이 없으면 여기서 던져 요청을 받기 전에 알린다. */
export function register() {
  apiBaseUrl()
  webSecret()
}

import { cache } from 'react'
import type { ErrorKind } from '../components/ErrorScreen'
import { apiBaseUrl, webSecret } from './config'
import { isTokenShaped } from './token'

export type ConsentPart = 'basic' | 'senior' | 'condition'

/** 문서의 순서. */
export const CONSENT_PARTS: ConsentPart[] = ['basic', 'senior', 'condition']

export type ConsentPet = { name: string; conditions: string[]; parts: ConsentPart[] }

/** 열려 있는 동의서. 문안은 백엔드가 열 때 조립한 것이다 — 웹은 온 것만 그린다. */
export type OpenForm = {
  kind: 'consent'
  state: 'open'
  shop: { name: string }
  previous_consent_on: string | null // 바뀐 부분만 받을 때의 지난 동의 날(YYYY-MM-DD)
  pets: ConsentPet[]
  texts: Partial<Record<ConsentPart, { body: string }>>
  doc_digest: string // 보호자가 읽은 것의 지문 — 낼 때 그대로 돌려보낸다
}

/** 이미 낸(또는 그 사이 매장에서 받은) 동의서. 낸 내용은 다시 오지 않는다. */
export type SubmittedForm = {
  kind: 'consent'
  state: 'submitted'
  shop: { name: string }
  submitted_on: string | null
}

export type FormResult = { kind: 'ok'; form: OpenForm | SubmittedForm } | { kind: ErrorKind }

export type ConsentBody = { doc_digest: string; signer_name: string; signature_png: string }

const TIMEOUT_MS = 5000

/** 토큰은 헤더로만 보낸다 — 주소에 두지 않는다. 알림장과 헤더 이름이 다르다(서로의 경로에서 읽히지 않는다). */
function call(method: 'GET' | 'POST', path: string, token: string, clientIp: string | null, body?: string): Promise<Response> {
  const headers: Record<string, string> = {
    'X-Form-Token': token,
    'X-Report-Web-Secret': webSecret(),
  }
  if (clientIp !== null) headers['X-Report-Client-IP'] = clientIp
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  return fetch(`${apiBaseUrl()}${path}`, {
    method,
    headers,
    body,
    cache: 'no-store',
    signal: AbortSignal.timeout(TIMEOUT_MS),
  })
}

const ERROR_KINDS: Record<number, ErrorKind> = { 404: 'not_found', 410: 'closed', 429: 'busy' }

export async function fetchForm(token: string, clientIp: string | null): Promise<FormResult> {
  if (!isTokenShaped(token)) return { kind: 'not_found' }
  try {
    const res = await call('GET', '/v1/public/form', token, clientIp)
    if (res.status === 200) return { kind: 'ok', form: (await res.json()) as OpenForm | SubmittedForm }
    return { kind: ERROR_KINDS[res.status] ?? 'unavailable' }
  } catch {
    // 연결 실패, 시간 초과, 깨진 JSON
    return { kind: 'unavailable' }
  }
}

/** 요청 하나 안에서는 백엔드를 한 번만 부른다(generateMetadata 와 본문이 나눠 쓴다). */
export const getForm = cache(fetchForm)

const SUBMIT_STATUSES = [204, 404, 409, 410, 413, 422, 429]

/** 서명을 보내고 웹이 낼 상태 코드를 돌려준다. */
export async function submitConsent(token: string, clientIp: string | null, body: ConsentBody): Promise<number> {
  if (!isTokenShaped(token)) return 404
  try {
    const res = await call('POST', '/v1/public/form/consent', token, clientIp, JSON.stringify(body))
    return SUBMIT_STATUSES.includes(res.status) ? res.status : 503
  } catch {
    return 503
  }
}

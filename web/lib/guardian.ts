import { apiBaseUrl } from './config'
import type { Cover, Report } from './report'

// 로그인한 보호자의 읽기와 잇기·끊기. 전부 웹 서버가 세션의 액세스 토큰으로 부른다.

/** 401 | 403 | 404·422 | 그 밖(연결 실패·시간 초과·5xx·깨진 JSON) */
export type Failure = { kind: 'unauthenticated' | 'forbidden' | 'not_found' | 'unavailable' }

export type GuardianLink = { link_id: number; shop_name: string; linked_at: string }
export type GuardianPet = { pet_id: number; name: string | null }
export type ReportItem = {
  report_id: number
  visit_date: string // YYYY-MM-DD
  pet_id: number | null // 보호자만의 방문이면 null
  pet_name: string | null
  cover: Cover | null // 서명 주소 — 저장하지 않는다
  media_count: number
}
export type ReportPage = { items: ReportItem[]; next_cursor: string | null }

const TIMEOUT_MS = 5000
const PREFIX = '/v1/me/guardian'

function call(method: 'GET' | 'POST' | 'DELETE', path: string, accessToken: string, reportToken?: string): Promise<Response> {
  const headers: Record<string, string> = { Authorization: `Bearer ${accessToken}` }
  if (reportToken !== undefined) headers['X-Report-Token'] = reportToken
  return fetch(`${apiBaseUrl()}${PREFIX}${path}`, {
    method,
    headers,
    cache: 'no-store',
    signal: AbortSignal.timeout(TIMEOUT_MS),
  })
}

const FAILURES: Record<number, Failure['kind']> = { 401: 'unauthenticated', 403: 'forbidden', 404: 'not_found', 422: 'not_found' }

async function read<T>(path: string, accessToken: string): Promise<{ ok: T } | Failure> {
  try {
    const res = await call('GET', path, accessToken)
    if (res.status === 200) return { ok: (await res.json()) as T }
    return { kind: FAILURES[res.status] ?? 'unavailable' }
  } catch {
    return { kind: 'unavailable' }
  }
}

/** 내 연결 — 매장 이름과 이은 날. 정지·폐업한 매장의 연결은 백엔드가 뺀다. */
export async function getLinks(accessToken: string): Promise<{ kind: 'ok'; links: GuardianLink[] } | Failure> {
  const result = await read<{ items: GuardianLink[] }>('/links', accessToken)
  return 'ok' in result ? { kind: 'ok', links: result.ok.items } : result
}

/** 그 연결에서 알림장을 받은 적 있는 아이들. */
export async function getPets(accessToken: string, linkId: number): Promise<{ kind: 'ok'; pets: GuardianPet[] } | Failure> {
  const result = await read<{ items: GuardianPet[] }>(`/links/${linkId}/pets`, accessToken)
  return 'ok' in result ? { kind: 'ok', pets: result.ok.items } : result
}

/** 지난 알림장 한 쪽(최신순 20개). */
export async function getReports(
  accessToken: string,
  linkId: number,
  query: { petId: number | null; cursor: string | null },
): Promise<{ kind: 'ok'; page: ReportPage } | Failure> {
  const params = new URLSearchParams()
  if (query.petId !== null) params.set('pet_id', String(query.petId))
  if (query.cursor !== null) params.set('cursor', query.cursor)
  const suffix = params.size > 0 ? `?${params}` : ''
  const result = await read<ReportPage>(`/links/${linkId}/reports${suffix}`, accessToken)
  return 'ok' in result ? { kind: 'ok', page: result.ok } : result
}

/** 알림장 한 장 — 공개 알림장과 같은 본문이고 기간(expires_at)은 늘 null 이다. */
export async function getGuardianReport(
  accessToken: string,
  linkId: number,
  reportId: number,
): Promise<{ kind: 'ok'; report: Report } | Failure> {
  const result = await read<Report>(`/links/${linkId}/reports/${reportId}`, accessToken)
  return 'ok' in result ? { kind: 'ok', report: result.ok } : result
}

/** 200·201 | 410 | 409 | 404 | 429 | 401 | 그 밖 */
export type ClaimResult = 'linked' | 'closed' | 'taken' | 'not_found' | 'busy' | 'unauthenticated' | 'unavailable'

const CLAIMS: Record<number, ClaimResult> = {
  200: 'linked',
  201: 'linked',
  410: 'closed',
  409: 'taken',
  404: 'not_found',
  429: 'busy',
  401: 'unauthenticated',
}

/** 받은 알림장으로 계정을 잇는다. 알림장 토큰은 헤더로만 넘긴다. */
export async function claimLink(accessToken: string, reportToken: string): Promise<ClaimResult> {
  try {
    const res = await call('POST', '/links', accessToken, reportToken)
    return CLAIMS[res.status] ?? 'unavailable'
  } catch {
    return 'unavailable'
  }
}

export type EndResult = 'ended' | 'not_found' | 'unauthenticated' | 'unavailable'

const ENDS: Record<number, EndResult> = { 204: 'ended', 404: 'not_found', 422: 'not_found', 401: 'unauthenticated' }

/** 보호자가 연결을 끊는다. */
export async function endLink(accessToken: string, linkId: number): Promise<EndResult> {
  try {
    const res = await call('DELETE', `/links/${linkId}`, accessToken)
    return ENDS[res.status] ?? 'unavailable'
  } catch {
    return 'unavailable'
  }
}

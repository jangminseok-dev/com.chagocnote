import { cache } from 'react'
import type { ErrorKind } from '../components/ErrorScreen'
import { apiBaseUrl, webSecret } from './config'
import { isTokenShaped } from './token'

export type { ErrorKind }

export type Media = {
  kind: 'photo' | 'video'
  phase: 'before' | 'after'
  width: number
  height: number
  duration_seconds: number | null
  display_url: string // 사진은 표시용, 영상은 원본(재생용)
  thumb_url: string // 영상이면 포스터
  download_url: string
}

export type Cover = { url: string; width: number; height: number }

export type Menu = { name: string; amount?: number | null }

export type Shop = { name: string; phone: string | null; address: string | null }

/** 공개 알림장. 매장이 끈 항목은 칸이 없고(undefined), 켰지만 값이 없으면 null 이다. */
export type Report = {
  pet_name: string | null
  visit_date: string // YYYY-MM-DD, 매장 시간대의 날짜
  care_note: string | null
  media: Media[] // 후 → 전
  cover: Cover | null
  expires_at: string | null // 시간대가 붙은 ISO. null 이면 기간이 없다
  menus?: Menu[] | null
  total_amount?: number | null
  weight_kg?: number | null
  shop?: Shop | null
}

export type ReportResult = { kind: 'ok'; report: Report } | { kind: ErrorKind }

const TIMEOUT_MS = 5000

function call(method: 'GET' | 'POST', path: string, token: string, clientIp: string | null): Promise<Response> {
  const headers: Record<string, string> = {
    'X-Report-Token': token,
    'X-Report-Web-Secret': webSecret(),
  }
  if (clientIp !== null) headers['X-Report-Client-IP'] = clientIp
  return fetch(`${apiBaseUrl()}${path}`, {
    method,
    headers,
    cache: 'no-store',
    signal: AbortSignal.timeout(TIMEOUT_MS),
  })
}

const ERROR_KINDS: Record<number, ErrorKind> = { 404: 'not_found', 410: 'closed', 429: 'busy' }

export async function fetchReport(token: string, clientIp: string | null): Promise<ReportResult> {
  if (!isTokenShaped(token)) return { kind: 'not_found' }
  try {
    const res = await call('GET', '/v1/public/report', token, clientIp)
    if (res.status === 200) return { kind: 'ok', report: (await res.json()) as Report }
    return { kind: ERROR_KINDS[res.status] ?? 'unavailable' }
  } catch {
    // 연결 실패, 시간 초과, 깨진 JSON
    return { kind: 'unavailable' }
  }
}

/** 요청 하나 안에서는 백엔드를 한 번만 부른다(generateMetadata 와 본문이 나눠 쓴다). */
export const getReport = cache(fetchReport)

const VIEWED_STATUSES = [204, 404, 410, 429]

/** 열람 신호를 보내고 웹이 낼 상태 코드를 돌려준다. */
export async function markViewed(token: string, clientIp: string | null): Promise<number> {
  if (!isTokenShaped(token)) return 404
  try {
    const res = await call('POST', '/v1/public/report/viewed', token, clientIp)
    return VIEWED_STATUSES.includes(res.status) ? res.status : 503
  } catch {
    return 503
  }
}

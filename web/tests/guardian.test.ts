import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import {
  claimLink, createInvite, endFamily, endLink, getFamily, getGuardianReport, getLinks, getMedia, getPets, getReports, getWeights,
  joinFamily,
} from '../lib/guardian'
import type { Report } from '../lib/report'

const fetchMock = vi.fn<typeof fetch>()
const ACCESS = 'access-abc'
const REPORT_TOKEN = 'ok'.padEnd(43, 'A')
const REPORT: Report = { pet_name: '두부', visit_date: '2026-09-28', care_note: null, media: [], cover: null, expires_at: null }

function respondWith(status: number, body: unknown = { code: 'X', message: 'x' }) {
  fetchMock.mockResolvedValue(new Response(status === 204 ? null : JSON.stringify(body), { status }))
}

function sent() {
  const [url, init] = fetchMock.mock.calls[0]
  return { url: String(url), init, headers: new Headers(init?.headers) }
}

beforeEach(() => {
  vi.stubEnv('API_BASE_URL', 'http://backend:8000/')
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

/** 읽기 넷 — 이름, 부르는 함수, 기대 주소, 200 의 본문, 기대 결과. */
const READS = [
  ['getLinks', () => getLinks(ACCESS), '/v1/me/guardian/links',
    { items: [{ link_id: 11, shop_name: 'Hiss Haus', linked_at: '2026-11-01T10:00:00+09:00' }] },
    { kind: 'ok', links: [{ link_id: 11, shop_name: 'Hiss Haus', linked_at: '2026-11-01T10:00:00+09:00' }] }],
  ['getPets', () => getPets(ACCESS, 11), '/v1/me/guardian/links/11/pets',
    { items: [{ pet_id: 7, name: null }] },
    { kind: 'ok', pets: [{ pet_id: 7, name: null }] }],
  ['getReports', () => getReports(ACCESS, 11, { petId: null, cursor: null }), '/v1/me/guardian/links/11/reports',
    { items: [], next_cursor: null },
    { kind: 'ok', page: { items: [], next_cursor: null } }],
  ['getGuardianReport', () => getGuardianReport(ACCESS, 11, 501), '/v1/me/guardian/links/11/reports/501',
    REPORT,
    { kind: 'ok', report: REPORT }],
  // 사진 모아 보기와 몸무게(⑫) — 고른 것만 질의에 싣는다.
  ['getMedia', () => getMedia(ACCESS, 11, { petId: 7, year: 2026, phase: 'after', cursor: 'c2' }),
    '/v1/me/guardian/links/11/media?pet_id=7&year=2026&phase=after&cursor=c2',
    { items: [], next_cursor: null, years: [2026] },
    { kind: 'ok', page: { items: [], next_cursor: null, years: [2026] } }],
  ['getMedia(빈 거르기)', () => getMedia(ACCESS, 11, { petId: null, year: null, phase: null, cursor: null }),
    '/v1/me/guardian/links/11/media',
    { items: [], next_cursor: null, years: [] },
    { kind: 'ok', page: { items: [], next_cursor: null, years: [] } }],
  ['getWeights', () => getWeights(ACCESS, 11, 7), '/v1/me/guardian/links/11/pets/7/weights',
    { items: [{ visit_date: '2026-11-01', weight_kg: 3.2 }] },
    { kind: 'ok', weights: [{ visit_date: '2026-11-01', weight_kg: 3.2 }] }],
] as const

test.each(READS)('%s 는 액세스 토큰을 들고 캐시 없이 GET 하고 200 의 본문을 준다', async (_name, call, path, body, expected) => {
  respondWith(200, body)
  expect(await call()).toEqual(expected)
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(sent().url).toBe(`http://backend:8000${path}`)
  expect(sent().init?.method).toBe('GET')
  expect(sent().init?.cache).toBe('no-store')
  expect(sent().init?.signal).toBeInstanceOf(AbortSignal)
  expect(sent().headers.get('Authorization')).toBe(`Bearer ${ACCESS}`)
})

const FAILURES = [
  [401, 'unauthenticated'],
  [403, 'forbidden'],
  [404, 'not_found'],
  [422, 'not_found'],
  [429, 'unavailable'],
  [500, 'unavailable'],
] as const

test.each(READS.flatMap(([name, call]) => FAILURES.map(([status, kind]) => [name, status, kind, call] as const)))(
  '%s %s → %s',
  async (_name, status, kind, call) => {
    respondWith(status)
    expect(await call()).toEqual({ kind })
  },
)

test.each(READS)('%s 는 fetch 가 던지면 unavailable 이다', async (_name, call) => {
  fetchMock.mockRejectedValue(new Error('연결 실패'))
  expect(await call()).toEqual({ kind: 'unavailable' })
})

test.each(READS)('%s 는 깨진 JSON 이면 unavailable 이다', async (_name, call) => {
  fetchMock.mockResolvedValue(new Response('<html>', { status: 200 }))
  expect(await call()).toEqual({ kind: 'unavailable' })
})

test('getReports 는 pet_id 와 cursor 가 있을 때만 질의에 넣는다', async () => {
  respondWith(200, { items: [], next_cursor: null })
  await getReports(ACCESS, 11, { petId: 7, cursor: null })
  expect(sent().url).toBe('http://backend:8000/v1/me/guardian/links/11/reports?pet_id=7')
  fetchMock.mockClear()
  await getReports(ACCESS, 11, { petId: null, cursor: 'a=b' })
  expect(sent().url).toBe('http://backend:8000/v1/me/guardian/links/11/reports?cursor=a%3Db')
  fetchMock.mockClear()
  await getReports(ACCESS, 11, { petId: 7, cursor: 'c2' })
  expect(sent().url).toBe('http://backend:8000/v1/me/guardian/links/11/reports?pet_id=7&cursor=c2')
})

test.each([
  [201, 'linked'],
  [200, 'linked'],
  [410, 'closed'],
  [409, 'taken'],
  [404, 'not_found'],
  [429, 'busy'],
  [401, 'unauthenticated'],
  [403, 'unavailable'],
  [500, 'unavailable'],
])('claimLink %s → %s', async (status, result) => {
  respondWith(status, { link_id: 11 })
  expect(await claimLink(ACCESS, REPORT_TOKEN)).toBe(result)
})

test('claimLink 는 알림장 토큰을 헤더로만 보내고 주소·본문에 넣지 않는다', async () => {
  respondWith(201, { link_id: 11 })
  await claimLink(ACCESS, REPORT_TOKEN)
  expect(sent().url).toBe('http://backend:8000/v1/me/guardian/links')
  expect(sent().init?.method).toBe('POST')
  expect(sent().init?.body).toBeUndefined()
  expect(sent().headers.get('X-Report-Token')).toBe(REPORT_TOKEN)
  expect(sent().headers.get('Authorization')).toBe(`Bearer ${ACCESS}`)
})

test('claimLink 는 fetch 가 던지면 unavailable 이다', async () => {
  fetchMock.mockRejectedValue(new Error('연결 실패'))
  expect(await claimLink(ACCESS, REPORT_TOKEN)).toBe('unavailable')
})

test.each([
  [204, 'ended'],
  [404, 'not_found'],
  [422, 'not_found'],
  [401, 'unauthenticated'],
  [500, 'unavailable'],
])('endLink %s → %s', async (status, result) => {
  respondWith(status)
  expect(await endLink(ACCESS, 11)).toBe(result)
  expect(sent().url).toBe('http://backend:8000/v1/me/guardian/links/11')
  expect(sent().init?.method).toBe('DELETE')
  expect(sent().headers.get('Authorization')).toBe(`Bearer ${ACCESS}`)
})

test('endLink 는 fetch 가 던지면 unavailable 이다', async () => {
  fetchMock.mockRejectedValue(new Error('연결 실패'))
  expect(await endLink(ACCESS, 11)).toBe('unavailable')
})

// ── 가족(⑫) ─────────────────────────────────────────────────────────────

const CODE = 'i'.repeat(43)

test.each([
  [201, { code: CODE, expires_at: '2026-11-17T10:00:00+09:00' }, { kind: 'ok', code: CODE, expiresAt: '2026-11-17T10:00:00+09:00' }],
  [409, { code: 'GUARDIAN_FAMILY_FULL' }, { kind: 'full' }],
  [429, {}, { kind: 'busy' }],
  [404, {}, { kind: 'not_found' }],
  [401, {}, { kind: 'unauthenticated' }],
  [500, {}, { kind: 'unavailable' }],
])('createInvite %s', async (status, body, expected) => {
  respondWith(status, body)
  expect(await createInvite(ACCESS, 11)).toEqual(expected)
  expect(sent().url).toBe('http://backend:8000/v1/me/guardian/links/11/family-invites')
  expect(sent().init?.method).toBe('POST')
})

test.each([
  [201, 'joined'], [200, 'joined'], [404, 'not_found'], [409, 'full'], [429, 'busy'], [401, 'unauthenticated'], [500, 'unavailable'],
])('joinFamily %s → %s', async (status, result) => {
  respondWith(status, { link_id: 21 })
  expect(await joinFamily(ACCESS, CODE)).toBe(result)
})

test('joinFamily 는 초대 코드를 헤더로만 보낸다', async () => {
  respondWith(201, { link_id: 21 })
  await joinFamily(ACCESS, CODE)
  expect(sent().url).toBe('http://backend:8000/v1/me/guardian/family-links')
  expect(sent().headers.get('X-Family-Invite')).toBe(CODE)
  expect(sent().init?.body).toBeUndefined()
})

test('getFamily 는 가족 줄을 준다', async () => {
  respondWith(200, { items: [{ family_id: 21, linked_at: '2026-11-16T10:00:00+09:00', unseen: true }] })
  expect(await getFamily(ACCESS, 11)).toEqual({ kind: 'ok', family: [{ family_id: 21, linked_at: '2026-11-16T10:00:00+09:00', unseen: true }] })
  expect(sent().url).toBe('http://backend:8000/v1/me/guardian/links/11/family')
})

test.each([[21, '/v1/me/guardian/links/11/family/21'], [null, '/v1/me/guardian/links/11/family']])(
  'endFamily(%s) 는 그 줄(없으면 모두)을 지운다', async (familyId, path) => {
    respondWith(204, null)
    expect(await endFamily(ACCESS, 11, familyId)).toBe('ended')
    expect(sent().url).toBe(`http://backend:8000${path}`)
    expect(sent().init?.method).toBe('DELETE')
  })


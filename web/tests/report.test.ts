import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { fetchReport, markViewed, type Report } from '../lib/report'

const TOKEN = 'ok'.padEnd(43, 'A')
const REPORT: Report = {
  pet_name: '두부',
  visit_date: '2026-09-28',
  care_note: null,
  media: [],
  cover: null,
  expires_at: null,
}

const fetchMock = vi.fn<typeof fetch>()

function respondWith(status: number, body: unknown = { code: 'X', message: 'x' }) {
  fetchMock.mockResolvedValue(new Response(status === 204 ? null : JSON.stringify(body), { status }))
}

function sent() {
  const [url, init] = fetchMock.mock.calls[0]
  return { url, init, headers: new Headers(init?.headers) }
}

beforeEach(() => {
  vi.stubEnv('API_BASE_URL', 'http://backend:8000/')
  vi.stubEnv('REPORT_WEB_SECRET', 'test-secret')
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

test('알림장을 백엔드의 공개 주소에서 캐시 없이 가져온다', async () => {
  respondWith(200, REPORT)
  await fetchReport(TOKEN, '203.0.113.7')
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(sent().url).toBe('http://backend:8000/v1/public/report')
  expect(sent().init?.method).toBe('GET')
  expect(sent().init?.cache).toBe('no-store')
  expect(sent().init?.signal).toBeInstanceOf(AbortSignal)
})

test('토큰·웹 비밀값·접속 주소를 헤더로 보낸다', async () => {
  respondWith(200, REPORT)
  await fetchReport(TOKEN, '203.0.113.7')
  expect(sent().headers.get('X-Report-Token')).toBe(TOKEN)
  expect(sent().headers.get('X-Report-Web-Secret')).toBe('test-secret')
  expect(sent().headers.get('X-Report-Client-IP')).toBe('203.0.113.7')
})

test('접속 주소가 null 이면 접속 주소 헤더가 없다', async () => {
  respondWith(200, REPORT)
  await fetchReport(TOKEN, null)
  expect(sent().headers.has('X-Report-Client-IP')).toBe(false)
  expect(sent().headers.get('X-Report-Token')).toBe(TOKEN)
})

test('200 이면 알림장을 돌려준다', async () => {
  respondWith(200, REPORT)
  expect(await fetchReport(TOKEN, null)).toEqual({ kind: 'ok', report: REPORT })
})

test.each([
  [404, 'not_found'],
  [410, 'closed'],
  [429, 'busy'],
  [500, 'unavailable'],
  [503, 'unavailable'],
  [401, 'unavailable'],
  [204, 'unavailable'],
])('백엔드가 %i 이면 %s 다', async (status, kind) => {
  respondWith(status)
  expect(await fetchReport(TOKEN, null)).toEqual({ kind })
})

test('연결에 실패하면 unavailable 이다', async () => {
  fetchMock.mockRejectedValue(new TypeError('fetch failed'))
  expect(await fetchReport(TOKEN, null)).toEqual({ kind: 'unavailable' })
})

test('200 인데 JSON 이 깨졌으면 unavailable 이다', async () => {
  fetchMock.mockResolvedValue(new Response('{"pet_name": "두', { status: 200 }))
  expect(await fetchReport(TOKEN, null)).toEqual({ kind: 'unavailable' })
})

test('형식이 틀린 토큰은 백엔드를 부르지 않고 not_found 다', async () => {
  respondWith(200, REPORT)
  expect(await fetchReport('짧은토큰', null)).toEqual({ kind: 'not_found' })
  expect(await fetchReport(`${TOKEN}\n`, null)).toEqual({ kind: 'not_found' })
  expect(fetchMock).not.toHaveBeenCalled()
})

test('열람 신호는 같은 헤더로 POST 한다', async () => {
  respondWith(204)
  await markViewed(TOKEN, '203.0.113.7')
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(sent().url).toBe('http://backend:8000/v1/public/report/viewed')
  expect(sent().init?.method).toBe('POST')
  expect(sent().init?.cache).toBe('no-store')
  expect(sent().headers.get('X-Report-Token')).toBe(TOKEN)
  expect(sent().headers.get('X-Report-Web-Secret')).toBe('test-secret')
  expect(sent().headers.get('X-Report-Client-IP')).toBe('203.0.113.7')
})

test.each([
  [204, 204],
  [404, 404],
  [410, 410],
  [429, 429],
  [500, 503],
  [503, 503],
  [200, 503],
  [401, 503],
])('열람 신호에 백엔드가 %i 이면 웹은 %i 다', async (status, expected) => {
  respondWith(status)
  expect(await markViewed(TOKEN, null)).toBe(expected)
})

test('열람 신호의 연결이 실패하면 503 이다', async () => {
  fetchMock.mockRejectedValue(new TypeError('fetch failed'))
  expect(await markViewed(TOKEN, null)).toBe(503)
})

test('형식이 틀린 토큰의 열람 신호는 백엔드를 부르지 않고 404 다', async () => {
  respondWith(204)
  expect(await markViewed('짧은토큰', null)).toBe(404)
  expect(fetchMock).not.toHaveBeenCalled()
})

import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { fetchForm, submitConsent, submitIntake, type OpenForm, type SubmittedForm } from '../lib/form'

const TOKEN = 'ok'.padEnd(43, 'A')
const OPEN: OpenForm = {
  kind: 'consent',
  state: 'open',
  shop: { name: 'Hiss Haus' },
  previous_consent_on: null,
  pets: [{ name: '두부', conditions: ['심장 질환'], parts: ['basic', 'condition'] }],
  texts: { basic: { body: '미용 안내' }, condition: { body: '지병 안내' } },
  doc_digest: 'd'.repeat(64),
}
const SUBMITTED: SubmittedForm = { kind: 'consent', state: 'submitted', shop: { name: 'Hiss Haus' }, submitted_on: '2026-11-16' }
const BODY = { doc_digest: 'd'.repeat(64), signer_name: '김민지', signature_png: 'AAAA' }

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

test('서류를 백엔드의 공개 주소에서 캐시 없이 가져온다', async () => {
  respondWith(200, OPEN)
  expect(await fetchForm(TOKEN, '203.0.113.7')).toEqual({ kind: 'ok', form: OPEN })
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(sent().url).toBe('http://backend:8000/v1/public/form')
  expect(sent().init?.method).toBe('GET')
  expect(sent().init?.cache).toBe('no-store')
  expect(sent().init?.signal).toBeInstanceOf(AbortSignal)
})

test('토큰은 서류 헤더로, 웹 비밀값과 접속 주소를 함께 보낸다', async () => {
  respondWith(200, OPEN)
  await fetchForm(TOKEN, '203.0.113.7')
  expect(sent().headers.get('X-Form-Token')).toBe(TOKEN)
  expect(sent().headers.has('X-Report-Token')).toBe(false)
  expect(sent().headers.get('X-Report-Web-Secret')).toBe('test-secret')
  expect(sent().headers.get('X-Report-Client-IP')).toBe('203.0.113.7')
  expect(String(sent().url)).not.toContain(TOKEN)
})

test('접속 주소가 null 이면 접속 주소 헤더가 없다', async () => {
  respondWith(200, OPEN)
  await fetchForm(TOKEN, null)
  expect(sent().headers.has('X-Report-Client-IP')).toBe(false)
})

test.each(['', 'short', 'a'.repeat(44), `${'a'.repeat(42)}!`])('토큰 모양이 아니면(%s) 백엔드를 부르지 않는다', async (token) => {
  expect(await fetchForm(token, null)).toEqual({ kind: 'not_found' })
  expect(await submitConsent(token, null, BODY)).toBe(404)
  expect(fetchMock).not.toHaveBeenCalled()
})

test('이미 낸 서류도 그대로 돌려준다', async () => {
  respondWith(200, SUBMITTED)
  expect(await fetchForm(TOKEN, null)).toEqual({ kind: 'ok', form: SUBMITTED })
})

test.each([
  [404, 'not_found'],
  [410, 'closed'],
  [429, 'busy'],
  [500, 'unavailable'],
  [403, 'unavailable'],
] as const)('상태 코드 %i 는 %s 다', async (status, kind) => {
  respondWith(status)
  expect(await fetchForm(TOKEN, null)).toEqual({ kind })
})

test('연결이 끊기거나 본문이 깨져 있으면 unavailable 이다', async () => {
  fetchMock.mockRejectedValue(new TypeError('fetch failed'))
  expect(await fetchForm(TOKEN, null)).toEqual({ kind: 'unavailable' })
  fetchMock.mockResolvedValue(new Response('<html>', { status: 200 }))
  expect(await fetchForm(TOKEN, null)).toEqual({ kind: 'unavailable' })
})

test('서명은 본문을 JSON 으로, 토큰은 헤더로 보낸다', async () => {
  respondWith(204)
  expect(await submitConsent(TOKEN, '203.0.113.7', BODY)).toBe(204)
  expect(sent().url).toBe('http://backend:8000/v1/public/form/consent')
  expect(sent().init?.method).toBe('POST')
  expect(sent().headers.get('X-Form-Token')).toBe(TOKEN)
  expect(sent().headers.get('Content-Type')).toBe('application/json')
  expect(sent().headers.get('X-Report-Client-IP')).toBe('203.0.113.7')
  expect(JSON.parse(String(sent().init?.body))).toEqual(BODY)
})

test.each([204, 404, 409, 410, 413, 422, 429])('서명의 상태 코드 %i 는 그대로 돌려준다', async (status) => {
  respondWith(status)
  expect(await submitConsent(TOKEN, null, BODY)).toBe(status)
})

test('서명에서 그 밖의 상태 코드와 연결 실패는 503 이다', async () => {
  respondWith(500)
  expect(await submitConsent(TOKEN, null, BODY)).toBe(503)
  respondWith(200, {})
  expect(await submitConsent(TOKEN, null, BODY)).toBe(503)
  fetchMock.mockRejectedValue(new TypeError('fetch failed'))
  expect(await submitConsent(TOKEN, null, BODY)).toBe(503)
})


test.each([204, 404, 410, 413, 422, 429])('문진표 제출은 백엔드의 상태 코드 %i 를 그대로 돌려준다', async (status) => {
  respondWith(status)
  const body = { guardian: null, pet: { name: '콩이' }, extras: [], privacy_agreed: true, done: true }
  expect(await submitIntake(TOKEN, '203.0.113.7', body)).toBe(status)
  expect(sent().url).toBe('http://backend:8000/v1/public/form/intake')
  expect(sent().init?.method).toBe('POST')
  expect(sent().headers.get('X-Form-Token')).toBe(TOKEN)
  expect(JSON.parse(String(sent().init?.body))).toEqual(body)
})

test('문진표 제출 — 모르는 상태 코드와 연결 실패는 503, 토큰의 모양이 아니면 부르지 않고 404', async () => {
  respondWith(500)
  expect(await submitIntake(TOKEN, null, { pet: {} })).toBe(503)
  fetchMock.mockRejectedValue(new Error('연결 실패'))
  expect(await submitIntake(TOKEN, null, { pet: {} })).toBe(503)
  fetchMock.mockReset()
  expect(await submitIntake('짧은토큰', null, { pet: {} })).toBe(404)
  expect(fetchMock).not.toHaveBeenCalled()
})

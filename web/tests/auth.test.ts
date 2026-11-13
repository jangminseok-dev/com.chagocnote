import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { webLogin } from '../lib/auth'

const fetchMock = vi.fn<typeof fetch>()
const OK = { access_token: 'access-abc', refresh_token: null, token_type: 'Bearer', expires_in: 1800, user_id: 5, is_new_user: false }

function respondWith(status: number, body: unknown = { code: 'X', message: 'x' }) {
  fetchMock.mockResolvedValue(new Response(JSON.stringify(body), { status }))
}

beforeEach(() => {
  vi.stubEnv('AUTH_BASE_URL', 'http://auth:9000/')
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

test('웹 로그인은 인증 주소에 session: web 을 넣어 캐시 없이 보낸다', async () => {
  respondWith(200, OK)
  await webLogin('dev', '이름')
  expect(fetchMock).toHaveBeenCalledTimes(1)
  const [url, init] = fetchMock.mock.calls[0]
  expect(url).toBe('http://auth:9000/v1/auth/social')
  expect(init?.method).toBe('POST')
  expect(init?.cache).toBe('no-store')
  expect(init?.signal).toBeInstanceOf(AbortSignal)
  expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json')
  expect(JSON.parse(String(init?.body))).toEqual({ provider: 'dev', token: '이름', session: 'web' })
})

test('200 이면 액세스 토큰과 수명을 준다', async () => {
  respondWith(200, OK)
  expect(await webLogin('dev', '이름')).toEqual({ kind: 'ok', accessToken: 'access-abc', expiresIn: 1800 })
})

test('리프레시 토큰이 온 200 은 unavailable 이다 — 웹에 리프레시를 두지 않는다', async () => {
  respondWith(200, { ...OK, refresh_token: 'r' })
  expect(await webLogin('dev', '이름')).toEqual({ kind: 'unavailable' })
})

test.each([
  ['토큰이 없는', { ...OK, access_token: undefined }],
  ['수명이 숫자가 아닌', { ...OK, expires_in: '1800' }],
  ['수명이 0 인', { ...OK, expires_in: 0 }],
])('%s 200 은 unavailable 이다', async (_name, body) => {
  respondWith(200, body)
  expect(await webLogin('dev', '이름')).toEqual({ kind: 'unavailable' })
})

test.each([
  [400, 'rejected'],
  [401, 'rejected'],
  [403, 'rejected'],
  [422, 'rejected'],
  [429, 'unavailable'],
  [500, 'unavailable'],
  [503, 'unavailable'],
])('로그인 %s → %s', async (status, kind) => {
  respondWith(status)
  expect(await webLogin('dev', '이름')).toEqual({ kind })
})

test('fetch 가 던지면 unavailable 이다', async () => {
  fetchMock.mockRejectedValue(new Error('연결 실패'))
  expect(await webLogin('dev', '이름')).toEqual({ kind: 'unavailable' })
})

test('깨진 JSON 은 unavailable 이다', async () => {
  fetchMock.mockResolvedValue(new Response('<html>', { status: 200 }))
  expect(await webLogin('dev', '이름')).toEqual({ kind: 'unavailable' })
})

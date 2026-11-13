import { afterEach, expect, test, vi } from 'vitest'
import { apiBaseUrl, authBaseUrl, devLogin, secureCookies, sessionSecret, webSecret } from '../lib/config'

afterEach(() => {
  vi.unstubAllEnvs()
})

test('API_BASE_URL 을 읽는다', () => {
  vi.stubEnv('API_BASE_URL', 'http://backend:8000')
  expect(apiBaseUrl()).toBe('http://backend:8000')
})

test('API_BASE_URL 끝의 / 를 뗀다', () => {
  vi.stubEnv('API_BASE_URL', 'http://backend:8000/')
  expect(apiBaseUrl()).toBe('http://backend:8000')
})

test('REPORT_WEB_SECRET 을 읽는다', () => {
  vi.stubEnv('REPORT_WEB_SECRET', 'test-secret')
  expect(webSecret()).toBe('test-secret')
})

test.each([
  ['없으면', undefined],
  ['비어 있으면', ''],
])('API_BASE_URL 이 %s 변수 이름을 말하며 던진다', (_name, value) => {
  vi.stubEnv('API_BASE_URL', value)
  expect(() => apiBaseUrl()).toThrow('API_BASE_URL')
})

test.each([
  ['없으면', undefined],
  ['비어 있으면', ''],
])('REPORT_WEB_SECRET 이 %s 변수 이름을 말하며 던진다', (_name, value) => {
  vi.stubEnv('REPORT_WEB_SECRET', value)
  expect(() => webSecret()).toThrow('REPORT_WEB_SECRET')
})

test('AUTH_BASE_URL 끝의 / 를 뗀다', () => {
  vi.stubEnv('AUTH_BASE_URL', 'http://auth:9000/')
  expect(authBaseUrl()).toBe('http://auth:9000')
})

test.each([
  ['없으면', undefined],
  ['비어 있으면', ''],
])('AUTH_BASE_URL 이 %s 변수 이름을 말하며 던진다', (_name, value) => {
  vi.stubEnv('AUTH_BASE_URL', value)
  expect(() => authBaseUrl()).toThrow('AUTH_BASE_URL')
})

test('WEB_SESSION_SECRET 이 32글자 이상이면 읽는다', () => {
  vi.stubEnv('WEB_SESSION_SECRET', 's'.repeat(32))
  expect(sessionSecret()).toBe('s'.repeat(32))
})

test.each([
  ['없으면', undefined],
  ['비어 있으면', ''],
  ['32글자보다 짧으면', 'q'.repeat(31)],
])('WEB_SESSION_SECRET 이 %s 변수 이름을 말하며 던지고 값은 말하지 않는다', (_name, value) => {
  vi.stubEnv('WEB_SESSION_SECRET', value)
  expect(() => sessionSecret()).toThrow('WEB_SESSION_SECRET')
  if (value) expect(() => sessionSecret()).not.toThrow(value)
})

test.each([
  ['1', true],
  ['0', false],
  ['true', false],
  [undefined, false],
])('DEV_LOGIN 이 %s 이면 %s', (value, expected) => {
  vi.stubEnv('DEV_LOGIN', value)
  expect(devLogin()).toBe(expected)
})

test('운영 빌드에서만 쿠키에 Secure 를 붙인다', () => {
  vi.stubEnv('NODE_ENV', 'production')
  expect(secureCookies()).toBe(true)
  vi.stubEnv('NODE_ENV', 'development')
  expect(secureCookies()).toBe(false)
})

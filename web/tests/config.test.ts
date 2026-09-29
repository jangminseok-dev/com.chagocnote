import { afterEach, expect, test, vi } from 'vitest'
import { apiBaseUrl, webSecret } from '../lib/config'

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

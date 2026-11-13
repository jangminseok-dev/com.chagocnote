// @vitest-environment node
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

type Options = { httpOnly?: boolean; sameSite?: string; path?: string; maxAge?: number; secure?: boolean }

// next/headers 의 cookies() 대신 쓰는 가짜 — 값과 마지막으로 쓴 옵션을 기억한다.
const jar = new Map<string, string>()
const written = new Map<string, Options>()
const deleted: string[] = []

vi.mock('next/headers', () => ({
  cookies: async () => ({
    get: (name: string) => (jar.has(name) ? { name, value: jar.get(name) } : undefined),
    set: (name: string, value: string, options: Options) => {
      jar.set(name, value)
      written.set(name, options)
    },
    delete: (name: string) => {
      jar.delete(name)
      deleted.push(name)
    },
  }),
}))

import {
  CLAIM_COOKIE,
  SESSION_COOKIE,
  clearClaim,
  clearSession,
  readSession,
  takeClaim,
  writeClaim,
  writeSession,
} from '../lib/session'

const REPORT_TOKEN = 'ok'.padEnd(43, 'A')

beforeEach(() => {
  jar.clear()
  written.clear()
  deleted.length = 0
  vi.stubEnv('WEB_SESSION_SECRET', 's'.repeat(40))
  vi.useFakeTimers({ now: new Date('2026-11-13T10:00:00Z') })
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllEnvs()
})

test('세션을 쓰면 httpOnly·lax·path / ·maxAge 1800 이고 값에 토큰이 보이지 않는다', async () => {
  await writeSession('access-token-abc', 1800)
  expect(written.get(SESSION_COOKIE)).toEqual({ httpOnly: true, sameSite: 'lax', path: '/', maxAge: 1800, secure: false })
  expect(jar.get(SESSION_COOKIE)).not.toContain('access-token')
})

test('NODE_ENV 가 production 이면 secure 다', async () => {
  vi.stubEnv('NODE_ENV', 'production')
  await writeSession('t', 1800)
  await writeClaim(REPORT_TOKEN)
  expect(written.get(SESSION_COOKIE)?.secure).toBe(true)
  expect(written.get(CLAIM_COOKIE)?.secure).toBe(true)
})

test('쓴 세션을 읽으면 토큰과 끝나는 시각이 온다', async () => {
  await writeSession('access-token-abc', 1800)
  expect(await readSession()).toEqual({
    accessToken: 'access-token-abc',
    expiresAt: Date.parse('2026-11-13T10:30:00Z') / 1000,
  })
})

test('끝나는 시각이 지난 세션은 null 이다', async () => {
  await writeSession('t', 1800)
  vi.advanceTimersByTime(1799_000)
  expect(await readSession()).not.toBeNull()
  vi.advanceTimersByTime(2_000)
  expect(await readSession()).toBeNull()
})

test('쿠키가 없으면 null 이다', async () => {
  expect(await readSession()).toBeNull()
  expect(await takeClaim()).toBeNull()
})

test.each(['', 'garbage', 'A'.repeat(300)])('깨진 쿠키(%s)는 null 이다', async (value) => {
  jar.set(SESSION_COOKIE, value)
  expect(await readSession()).toBeNull()
})

test('잇기 쿠키로 봉한 값을 세션 쿠키에 넣으면 null 이다', async () => {
  await writeClaim(REPORT_TOKEN)
  jar.set(SESSION_COOKIE, jar.get(CLAIM_COOKIE)!)
  expect(await readSession()).toBeNull()
})

test('세션을 지우면 쿠키가 지워진다', async () => {
  await writeSession('t', 1800)
  await clearSession()
  expect(deleted).toEqual([SESSION_COOKIE])
  expect(await readSession()).toBeNull()
})

test('잇기 쿠키는 httpOnly·lax·maxAge 600 이고 값에 토큰이 보이지 않는다', async () => {
  await writeClaim(REPORT_TOKEN)
  expect(written.get(CLAIM_COOKIE)).toEqual({ httpOnly: true, sameSite: 'lax', path: '/', maxAge: 600, secure: false })
  expect(jar.get(CLAIM_COOKIE)).not.toContain(REPORT_TOKEN)
})

test('takeClaim 은 값을 주고 쿠키를 지운다', async () => {
  await writeClaim(REPORT_TOKEN)
  expect(await takeClaim()).toBe(REPORT_TOKEN)
  expect(deleted).toEqual([CLAIM_COOKIE])
  expect(await takeClaim()).toBeNull()
})

test('clearClaim 은 맡긴 토큰을 버린다', async () => {
  await writeClaim(REPORT_TOKEN)
  await clearClaim()
  expect(deleted).toEqual([CLAIM_COOKIE])
  expect(await takeClaim()).toBeNull()
})

test('takeClaim 은 토큰 모양이 아닌 값이면 null 이고 쿠키를 지운다', async () => {
  await writeClaim('토큰이 아닌 글자')
  expect(await takeClaim()).toBeNull()
  expect(deleted).toEqual([CLAIM_COOKIE])
})

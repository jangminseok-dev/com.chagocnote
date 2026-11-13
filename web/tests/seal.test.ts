// @vitest-environment node
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { open, seal } from '../lib/seal'

beforeEach(() => {
  vi.stubEnv('WEB_SESSION_SECRET', 's'.repeat(40))
})

afterEach(() => {
  vi.unstubAllEnvs()
})

test('봉한 값을 같은 용도로 열면 원래 글자다', async () => {
  expect(await open('session', await seal('session', '값 하나'))).toBe('값 하나')
})

test('같은 값을 두 번 봉하면 글자가 다르다', async () => {
  expect(await seal('session', 'x')).not.toBe(await seal('session', 'x'))
})

test('봉한 값에 원래 글자가 보이지 않고 쿠키에 넣을 수 있는 글자뿐이다', async () => {
  const sealed = await seal('session', 'access-token-글자')
  expect(sealed).not.toContain('access-token')
  expect(sealed).toMatch(/^[A-Za-z0-9_-]+$/)
})

test.each(['', 'abc', '!!!!', 'A'.repeat(500), '한글'])('아무 글자(%s)는 null 이다', async (value) => {
  expect(await open('session', value)).toBeNull()
})

// 글자가 아니라 바이트를 뒤집는다 — base64url 의 마지막 글자는 남는 비트가 있어 바꿔도 같은 바이트일 수 있다.
test.each([
  ['첫', 0],
  ['가운데', 14],
  ['마지막', -1],
])('%s 바이트를 바꾸면 null 이다', async (_name, index) => {
  const bytes = Buffer.from(await seal('session', '값'), 'base64url')
  const at = index < 0 ? bytes.length + index : index
  bytes[at] ^= 0x01
  expect(await open('session', bytes.toString('base64url'))).toBeNull()
})

test('다른 용도로 봉한 값은 null 이다', async () => {
  expect(await open('session', await seal('claim', 'x'))).toBeNull()
  expect(await open('claim', await seal('session', 'x'))).toBeNull()
})

test('비밀값이 바뀌면 null 이다', async () => {
  const sealed = await seal('session', 'x')
  vi.stubEnv('WEB_SESSION_SECRET', 't'.repeat(40))
  expect(await open('session', sealed)).toBeNull()
})

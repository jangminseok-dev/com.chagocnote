import { expect, test } from 'vitest'
import { cursorFrom, idFrom, safeNext } from '../lib/next-path'

test.each(['/me', '/me/12', '/me/12/345', '/me/12?pet=7'])('%s 는 그대로다', (value) => {
  expect(safeNext(value)).toBe(value)
})

test.each([
  null,
  undefined,
  '',
  '//evil.example',
  '/\\evil.example',
  'https://evil.example/me',
  '/r/abc',
  '/me/../r',
  '/me/0',
  '/me/12/345/6',
  '/me/12?pet=7&x=1',
  '/me/12?cursor=a',
  '/me\n',
  '/me/12\n',
  '/login',
  '/me/',
  ' /me',
])('%j 는 /me 다', (value) => {
  expect(safeNext(value)).toBe('/me')
})

test.each([
  ['12', 12],
  ['1', 1],
  ['0', null],
  ['-1', null],
  ['1e3', null],
  ['12a', null],
  ['012', null],
  ['', null],
  [undefined, null],
  ['12\n', null],
  ['9'.repeat(16), null], // 자바스크립트의 안전한 정수를 넘는다
])('idFrom(%j) 는 %s', (value, expected) => {
  expect(idFrom(value)).toBe(expected)
})

test.each([
  ['abc-_=09', 'abc-_=09'],
  ['', null],
  [undefined, null],
  ['<script>', null],
  ['a b', null],
  ['a'.repeat(301), null],
  ['abc\n', null],
])('cursorFrom(%j) 는 %j', (value, expected) => {
  expect(cursorFrom(value)).toBe(expected)
})

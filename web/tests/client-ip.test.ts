import { expect, test } from 'vitest'
import { clientIpFrom } from '../lib/client-ip'

test('x-forwarded-for 의 값이 접속 주소다', () => {
  expect(clientIpFrom(new Headers({ 'x-forwarded-for': '203.0.113.7' }))).toBe('203.0.113.7')
})

test('값이 여럿이면 첫 값이고 공백을 뗀다', () => {
  expect(clientIpFrom(new Headers({ 'x-forwarded-for': ' 203.0.113.7 , 10.0.0.1, 10.0.0.2' }))).toBe('203.0.113.7')
})

test('헤더가 없으면 null 이다', () => {
  expect(clientIpFrom(new Headers())).toBeNull()
})

test('헤더가 비어 있으면 null 이다', () => {
  expect(clientIpFrom(new Headers({ 'x-forwarded-for': '' }))).toBeNull()
  expect(clientIpFrom(new Headers({ 'x-forwarded-for': ' , 10.0.0.1' }))).toBeNull()
})

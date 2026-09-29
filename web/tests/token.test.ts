import { expect, test } from 'vitest'
import { isTokenShaped } from '../lib/token'

const TOKEN = 'aZ09_-'.padEnd(43, 'A')

test('43글자이고 글자가 맞으면 토큰 모양이다', () => {
  expect(isTokenShaped(TOKEN)).toBe(true)
})

test.each([
  ['42글자', TOKEN.slice(0, 42)],
  ['44글자', `${TOKEN}A`],
  ['빈 값', ''],
  ['한글', '가'.repeat(43)],
  ['공백이 든 값', `${TOKEN.slice(0, 42)} `],
  ['= 패딩', `${TOKEN.slice(0, 42)}=`],
  ['/ 가 든 값', `${TOKEN.slice(0, 42)}/`],
  ['% 가 든 값', `${TOKEN.slice(0, 42)}%`],
  ['끝에 줄바꿈이 붙은 값', `${TOKEN}\n`],
  ['가운데 줄바꿈이 든 값', `${TOKEN.slice(0, 21)}\n${TOKEN.slice(0, 21)}`],
  ['수천 글자', 'A'.repeat(5000)],
])('%s 은 토큰 모양이 아니다', (_name, value) => {
  expect(isTokenShaped(value)).toBe(false)
})

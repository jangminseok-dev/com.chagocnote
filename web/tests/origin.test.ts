import { expect, test } from 'vitest'
import { isCrossSite, seeOther } from '../lib/origin'

const request = (site: string | null) =>
  new Request('http://web.test/logout', { method: 'POST', headers: site === null ? {} : { 'Sec-Fetch-Site': site } })

test.each([
  [null, false], // 헤더가 없는 옛 브라우저는 통과한다
  ['same-origin', false],
  ['cross-site', true],
  ['same-site', true],
  ['none', true],
])('sec-fetch-site 가 %s 이면 isCrossSite 는 %s', (site, expected) => {
  expect(isCrossSite(request(site))).toBe(expected)
})

test('seeOther 는 303 이고 Location 이 상대 경로 그대로이며 본문이 없다', async () => {
  const res = seeOther('/me?notice=taken')
  expect(res.status).toBe(303)
  expect(res.headers.get('location')).toBe('/me?notice=taken')
  expect(await res.text()).toBe('')
})

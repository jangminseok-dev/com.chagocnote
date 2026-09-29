import { randomBytes } from 'node:crypto'
import { readFileSync } from 'node:fs'

import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

import { dayNumber, monthAndWeekday } from '../../lib/format'

type Links = { live: string; closed: string; long: string; visitDate: string; api: string; staffLogin: string; visitPath: string }
const links: Links = JSON.parse(readFileSync('test-results/e2e-links.json', 'utf8'))

/** 앱 쪽 API 로 방문을 읽어 알림장을 처음 연 시각을 본다. */
async function firstViewedAt(request: APIRequestContext): Promise<string | null> {
  const login = await request.post(`${links.api}/v1/auth/social`, { data: { provider: 'dev', token: links.staffLogin } })
  const { access_token } = await login.json()
  const visit = await request.get(`${links.api}${links.visitPath}`, { headers: { Authorization: `Bearer ${access_token}` } })
  return (await visit.json()).report.first_viewed_at
}

/** 브라우저가 보낸 열람 신호 POST 를 센다. */
function countViewed(page: Page): () => number {
  let count = 0
  page.on('request', (req) => {
    if (req.method() === 'POST' && req.url().endsWith('/viewed')) count += 1
  })
  return () => count
}

/** 다음에 오는 열람 신호의 응답. */
function nextViewed(page: Page) {
  return page.waitForResponse((res) => res.request().method() === 'POST' && res.url().endsWith('/viewed'))
}

/** 주소가 url 인지 본다. 실패해도 토큰이 든 주소를 출력하지 않는다. */
async function expectUrl(page: Page, url: string, message: string) {
  await expect.poll(() => page.url() === url, { message }).toBe(true)
}

async function heroWidth(page: Page): Promise<number> {
  const img = page.locator('[data-section="hero"] img')
  await expect.poll(() => img.evaluate((el: HTMLImageElement) => el.complete)).toBe(true)
  return img.evaluate((el: HTMLImageElement) => el.naturalWidth)
}

test('살아 있는 링크를 열면 대표 사진이 그려지고 열람 신호가 한 번 나가 방문에 처음 연 시각이 남는다', async ({
  page,
  request,
}) => {
  expect(await firstViewedAt(request)).toBeNull()
  const hosts = new Set<string>()
  page.on('request', (req) => hosts.add(new URL(req.url()).host))
  const errors: string[] = []
  page.on('console', (msg) => msg.type() === 'error' && errors.push(msg.text()))
  page.on('pageerror', (error) => errors.push(error.message))
  const viewed = countViewed(page)
  const signal = page.waitForResponse((res) => res.request().method() === 'POST' && res.url().endsWith('/viewed'))

  const res = await page.goto(links.live)
  expect(res?.status()).toBe(200)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('두부의 미용 알림장')
  const date = page.locator('[data-section="date"]')
  await expect(date).toContainText(dayNumber(links.visitDate))
  for (const word of monthAndWeekday(links.visitDate)) await expect(date).toContainText(word)
  expect(await heroWidth(page)).toBeGreaterThan(0)

  expect((await signal).status()).toBe(204)
  await page.waitForLoadState('networkidle')
  expect(viewed()).toBe(1)
  await expect.poll(() => firstViewedAt(request)).not.toBeNull()
  expect([...hosts].sort()).toEqual(['127.0.0.1:3010', '127.0.0.1:9010'])
  expect(errors).toEqual([])
})

test('여러 번 새로 고쳐도 처음 연 시각은 그대로다', async ({ page, request }) => {
  // 앞 테스트가 이미 열었다.
  const first = await firstViewedAt(request)
  expect(first).not.toBeNull()

  for (const open of [() => page.goto(links.live), () => page.reload(), () => page.reload()]) {
    const signal = nextViewed(page)
    await open()
    expect((await signal).status()).toBe(204)
  }

  expect(await firstViewedAt(request)).toBe(first)
})

test('썸네일을 눌러 크게 보고 다음으로 넘긴 뒤 닫는다', async ({ page }) => {
  await page.goto(links.live)
  await page.getByRole('button', { name: /^1번째 .* 크게 보기$/ }).click()
  const dialog = page.getByRole('dialog', { name: '크게 보기' })
  await expect(dialog).toContainText('1 / 2')
  await dialog.getByRole('button', { name: '다음' }).click()
  await expect(dialog).toContainText('2 / 2')
  await expect(dialog.getByRole('button', { name: '다음' })).toBeDisabled()
  await dialog.getByRole('button', { name: '닫기' }).click()
  await expect(dialog).toHaveCount(0)
})

test.describe('뒤로 가기', () => {
  // 카카오톡에서 연 것처럼 알림장 앞에 다른 페이지를 하나 둔다.
  test.beforeEach(async ({ page }) => {
    await page.goto('about:blank')
    await page.goto(links.live)
    await page.getByRole('button', { name: /^1번째 .* 크게 보기$/ }).click()
    await expect(page.getByRole('dialog', { name: '크게 보기' })).toBeVisible()
  })

  test('크게 보기를 연 채 뒤로 가면 크게 보기만 닫히고, 한 번 더 가면 알림장을 떠난다', async ({ page }) => {
    await page.goBack()
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await expectUrl(page, links.live, '알림장의 주소가 아니다')
    await expect(page).toHaveTitle('두부의 미용 알림장')
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('두부의 미용 알림장')

    await page.goBack()
    await expectUrl(page, 'about:blank', '알림장을 떠나지 않았다')
  })

  test('닫기 버튼으로 닫은 뒤에는 뒤로 가기 한 번에 알림장을 떠난다', async ({ page }) => {
    await page.getByRole('dialog').getByRole('button', { name: '닫기' }).click()
    await expect(page.getByRole('dialog')).toHaveCount(0)

    await page.goBack()
    await expectUrl(page, 'about:blank', '알림장을 떠나지 않았다')
  })
})

for (const width of [320, 390]) {
  test(`긴 글·긴 이름의 알림장도 폭 ${width} 에서 옆으로 밀리지 않는다`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await page.goto(links.long)
    await expect(page.locator('[data-section="note"]')).toContainText('https://example.com/')
    await expect(page.locator('[data-section="care"]')).toContainText('띄어쓰기없는아주긴메뉴이름')
    await expect(page.locator('[data-section="shop"]')).toContainText('서울특별시마포구아주긴길이름로')

    const { scroll, inner } = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      inner: window.innerWidth,
    }))
    // 모바일 기기로 흉내 내면 넘치는 만큼 화면을 축소해 innerWidth 가 커진다. 폭 그대로인지도 본다.
    expect(inner).toBe(width)
    expect(scroll).toBeLessThanOrEqual(inner)
  })
}

test('하나 저장을 누르면 내려받기가 시작된다', async ({ page }) => {
  await page.goto(links.live)
  const download = page.waitForEvent('download')
  await page.locator('[data-section="hero"]').getByRole('link', { name: '저장' }).click()
  expect((await download).suggestedFilename()).toMatch(/^chagocnote-\d+\.jpg$/)
})

test('끊은 링크는 200 이고 "닫힌 알림장이에요" 이며 열람 신호가 나가지 않는다', async ({ page }) => {
  const viewed = countViewed(page)
  const res = await page.goto(links.closed)
  expect(res?.status()).toBe(200)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('닫힌 알림장이에요')
  await page.waitForLoadState('networkidle')
  expect(viewed()).toBe(0)
})

test('없는 토큰은 404 이고 브라우저 화면에 "알림장을 찾을 수 없어요" 가 보인다', async ({ page }) => {
  const res = await page.goto(`/r/${randomBytes(32).toString('base64url')}`)
  expect(res?.status()).toBe(404)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('알림장을 찾을 수 없어요')
})

test.describe('자바스크립트를 끈 브라우저', () => {
  test.use({ javaScriptEnabled: false })

  test('살아 있는 링크의 제목·케어 메모·대표 사진이 보인다', async ({ page }) => {
    await page.goto(links.live)
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('두부의 미용 알림장')
    await expect(page.locator('[data-section="note"]')).toContainText('눈물 자국을 닦았어요.')
    expect(await heroWidth(page)).toBeGreaterThan(0)
  })
})

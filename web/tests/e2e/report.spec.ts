import { randomBytes } from 'node:crypto'
import { readFileSync } from 'node:fs'

import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

import { dayNumber, monthAndWeekday } from '../../lib/format'

type Links = { live: string; closed: string; visitDate: string; api: string; staffLogin: string; visitPath: string }
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

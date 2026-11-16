import { readFileSync } from 'node:fs'

import { devices, expect, test, type Browser, type Page } from '@playwright/test'

// ⑫ 보호자 기록 모아 보기 — 알림장 끝의 리뷰 줄, 사진 모아 보기(날짜 묶음·거르기·몸무게·크게 보기 확대·한 쪽 저장),
// 보던 자리로 돌아가기, 가족 초대 → 다른 계정이 잇기 → 그 한 명만 끊기.
// 적힌 순서대로 돈다(workers: 1). 첫 테스트가 이은 연결을 뒤 테스트가 쓴다. 준비물은 셋째 고객(콩이)이다 — 다른 흐름과 나눠 쓰지 않는다.
// 초대 주소(코드)·알림장 주소(토큰)는 출력하지 않는다.

type Links = {
  archiveReview: string; archiveNoReview: string; reviewUrl: string; archiveShop: string
  archiveLogin: string; familyA: string; familyB: string
}
const links: Links = JSON.parse(readFileSync('test-results/e2e-links.json', 'utf8'))
const BASE = 'http://127.0.0.1:3010'
const CLAIM = '로그인하고 지난 기록 보기'
const SAVE_PAGE = '이 화면의 사진 · 영상 모두 저장'

async function signIn(page: Page, name: string) {
  await page.getByLabel('개발용 로그인 이름').fill(name)
  await page.getByRole('button', { name: '로그인' }).click()
}

async function openMe(page: Page, name = links.archiveLogin) {
  await page.goto('/login')
  await signIn(page, name)
  await expect(page).toHaveURL('/me')
}

/** 주소가 맞는지 본다. 실패해도 주소를 출력하지 않는다. */
async function expectPath(page: Page, pattern: RegExp, message: string) {
  await expect.poll(() => {
    const url = new URL(page.url())
    return pattern.test(url.pathname + url.search + url.hash)
  }, { message }).toBe(true)
}

/** 내 기록 → 콩이의 지난 알림장 → 사진 탭. */
async function openPhotos(page: Page) {
  await openMe(page)
  await page.getByRole('link', { name: '콩이' }).click()
  await expectPath(page, /^\/me\/\d+\?pet=\d+$/, '목록의 주소가 아니다')
  await page.locator('[data-section="tabs"]').getByRole('link', { name: '사진' }).click()
  await expectPath(page, /^\/me\/\d+\/photos\?pet=\d+$/, '사진 모아 보기의 주소가 아니다')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('사진 모아 보기')
  // 서버가 그린 단추는 스크립트가 붙기 전에는 눌러도 아무 일이 없다(next dev 는 붙는 데 오래 걸릴 때가 있다).
  await page.waitForLoadState('networkidle')
}

/** 이 브라우저에 파일 공유가 없는 것으로 한다 — 모두 저장이 차례 내려받기로 간다. */
async function withoutShare(page: Page) {
  await page.addInitScript(() => {
    Object.defineProperty(Navigator.prototype, 'share', { value: undefined, configurable: true })
    Object.defineProperty(Navigator.prototype, 'canShare', { value: undefined, configurable: true })
  })
}

/** 초대 단추를 눌러 복사된 초대 주소를 받는다. 복사는 화면 안의 변수로 받는다(시스템 클립보드를 쓰지 않는다). */
async function invite(page: Page): Promise<string> {
  const family = page.locator('[data-section="family"]')
  await page.waitForLoadState('networkidle') // 스크립트가 붙기 전의 단추는 눌러도 아무 일이 없다
  await family.getByRole('button', { name: '가족과 함께 보기' }).click()
  await expect(family.getByRole('status').filter({ hasText: '초대 주소를 복사했어요' })).toBeVisible()
  const url = await page.evaluate(() => (window as unknown as { copied?: string }).copied ?? '')
  expect(/^http:\/\/127\.0\.0\.1:3010\/j\/[A-Za-z0-9_-]{43}$/.test(url), '초대 주소의 모양이 아니다').toBe(true)
  return url
}

/** 다른 사람의 브라우저(새 쿠키)로 초대 주소를 열고 [로그인하고 함께 보기] → 로그인. 코드는 주소·쿠키 값에 보이지 않는다. */
async function joinAs(browser: Browser, url: string, name: string): Promise<Page> {
  const context = await browser.newContext({ ...devices['Pixel 7'], baseURL: BASE })
  const page = await context.newPage()
  await page.goto(url)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('가족의 미용 기록을 함께 볼 수 있어요')
  await page.getByRole('button', { name: '로그인하고 함께 보기' }).click()
  await expect(page).toHaveURL('/login')
  const code = url.slice(url.lastIndexOf('/') + 1)
  const join = (await context.cookies()).find((cookie) => cookie.name === 'cn_join')
  expect(join?.httpOnly).toBe(true)
  expect(join?.value.includes(code)).toBe(false)
  await signIn(page, name)
  await expect.poll(async () => (await context.cookies()).some((cookie) => cookie.name === 'cn_join'), { message: '가족 잇기 쿠키가 남았다' }).toBe(false)
  return page
}

test('리뷰 줄은 리뷰 주소를 넣은 매장의 알림장 끝에 있고 새 창으로 열린다. 이 알림장만 뺀 것에는 없다', async ({ page }) => {
  await page.goto(links.archiveNoReview)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('콩이의 미용 알림장')
  await expect(page.locator('[data-section="review"]')).toHaveCount(0)

  await page.goto(links.archiveReview)
  const review = page.locator('[data-section="review"]')
  const link = review.getByRole('link', { name: '미용이 마음에 드셨다면 후기를 남겨 주세요' })
  await expect(link).toHaveAttribute('href', links.reviewUrl)
  await expect(link).toHaveAttribute('target', '_blank')
  expect((await link.getAttribute('rel'))?.split(' ')).toEqual(expect.arrayContaining(['noopener', 'noreferrer']))
  // 매장 카드 아래, 잇기 버튼 위다.
  const order = await page.locator('[data-section]').evaluateAll((els) => els.map((el) => el.getAttribute('data-section')))
  expect(order.indexOf('review')).toBeGreaterThan(order.indexOf('shop'))
  expect(order.indexOf('review')).toBeLessThan(order.indexOf('claim'))

  // 이 알림장으로 잇는다 — 뒤 테스트가 이 연결을 쓴다.
  await page.getByRole('button', { name: CLAIM }).click()
  await signIn(page, links.archiveLogin)
  await expect(page).toHaveURL('/me')
  const shop = page.locator('[data-section="shop"]')
  await expect(shop).toHaveCount(1)
  await expect(shop.getByRole('link', { name: '콩이' })).toBeVisible()
  // 기본 보호자에게는 가족 구역이 있고 아직 가족 줄은 없다.
  const family = page.locator('[data-section="family"]')
  await expect(family.getByRole('button', { name: '가족과 함께 보기' })).toBeVisible()
  await expect(family.getByRole('listitem')).toHaveCount(0)
})

test('사진 모아 보기는 날짜마다 묶고(최신 먼저) 전후를 거르며 아이의 몸무게를 보인다', async ({ page }) => {
  await openPhotos(page)
  const grid = page.locator('[data-section="grid"]')
  const days = grid.locator('section')
  await expect(days).toHaveCount(2)
  await expect(days.nth(0).getByRole('button')).toHaveCount(1) // 어제 — 후 하나
  await expect(days.nth(1).getByRole('button')).toHaveCount(2) // 여드레 전 — 후·전
  const thumb = days.nth(0).locator('img')
  await expect.poll(() => thumb.evaluate((el: HTMLImageElement) => el.complete && el.naturalWidth > 0)).toBe(true)

  const weights = page.locator('[data-section="weights"]')
  await expect(weights.getByRole('img', { name: '몸무게 변화' })).toBeVisible()
  await expect(weights.getByRole('listitem')).toHaveCount(2)
  await expect(weights).toContainText('4.8 kg')
  await expect(weights).toContainText('5.1 kg')

  const filter = page.locator('[data-section="filter"]')
  await filter.getByRole('link', { name: '전', exact: true }).click()
  await expectPath(page, /^\/me\/\d+\/photos\?pet=\d+&phase=before$/, '전 거르기의 주소가 아니다')
  await expect(page.locator('[data-section="grid"]').getByRole('button')).toHaveCount(1)
  await expect(page.locator('[data-section="filter"]').getByRole('link', { name: '전', exact: true })).toHaveAttribute('aria-current', 'true')

  await page.locator('[data-section="filter"]').getByRole('link', { name: '후', exact: true }).click()
  await expect(page.locator('[data-section="grid"]').getByRole('button')).toHaveCount(2)
  await expect(page.locator('[data-section="filter"]').getByRole('link', { name: /^\d{4}년$/ }).first()).toBeVisible()
})

test('크게 보기에서 두 번 누르면 확대되고 다시 두 번 누르면 돌아온다. 그 날의 알림장으로 가서 돌아가기를 누르면 사진의 그 날로 온다', async ({ page }) => {
  await openPhotos(page)
  const photosUrl = new URL(page.url())
  await page.locator('[data-section="grid"]').getByRole('button').first().click()
  const dialog = page.getByRole('dialog', { name: '크게 보기' })
  await expect(dialog).toBeVisible()
  const stage = dialog.locator('[data-stage]')
  await expect(stage).toHaveAttribute('data-scale', '1')
  await dialog.locator('img').dblclick()
  await expect(stage).toHaveAttribute('data-scale', '2.5')
  await dialog.locator('img').dblclick()
  await expect(stage).toHaveAttribute('data-scale', '1')

  await dialog.getByRole('link', { name: /알림장 보기$/ }).click()
  await expectPath(page, /^\/me\/\d+\/\d+$/, '한 장의 주소가 아니다')
  const reportId = new URL(page.url()).pathname.split('/').at(-1)
  const back = page.getByRole('link', { name: '사진 모아 보기' })
  await expect(back).toHaveAttribute('href', `${photosUrl.pathname}${photosUrl.search}#r${reportId}`)
  await back.click()
  await expect.poll(() => new URL(page.url()).hash, { message: '그 날로 돌아오지 않았다' }).toBe(`#r${reportId}`)
  await expect(page.locator(`#r${reportId}`)).toBeInViewport()
})

test('목록에서 연 한 장의 [지난 알림장]은 그 목록의 그 줄로 돌아간다', async ({ page }) => {
  await openMe(page)
  await page.getByRole('link', { name: '콩이' }).click()
  await expectPath(page, /^\/me\/\d+\?pet=\d+$/, '목록의 주소가 아니다')
  const listUrl = new URL(page.url())
  const items = page.locator('[data-section="item"]')
  await expect(items).toHaveCount(2)
  const id = await items.nth(1).getAttribute('id')
  await items.nth(1).getByRole('link').click()
  await expectPath(page, /^\/me\/\d+\/\d+$/, '한 장의 주소가 아니다')
  const back = page.getByRole('link', { name: '지난 알림장' })
  await expect(back).toHaveAttribute('href', `${listUrl.pathname}${listUrl.search}#${id}`)
  await back.click()
  await expect.poll(() => new URL(page.url()).hash, { message: '그 줄로 돌아오지 않았다' }).toBe(`#${id}`)
})

test('이 쪽 모두 저장은 공유를 못 하는 브라우저에서 이 쪽의 사진 수만큼 차례로 내려받는다', async ({ page }) => {
  await withoutShare(page)
  await openPhotos(page)
  await expect(page.locator('[data-section="save-all"]')).toContainText('이 쪽의 3개를 받아요.')
  const names: string[] = []
  page.on('download', (download) => names.push(download.suggestedFilename()))
  await page.locator('[data-section="save-all"]').getByRole('button', { name: SAVE_PAGE }).click()
  await expect.poll(() => names.length, { timeout: 15_000, message: '내려받은 수가 이 쪽의 사진 수가 아니다' }).toBe(3)
  expect(names.every((name) => /^chagocnote-\d+\.jpg$/.test(name))).toBe(true)
})

test('가족 초대 → 다른 계정이 잇고 함께 본다 → 쓴 초대는 다시 못 쓴다 → 기본 보호자가 그 한 명만 끊는다', async ({ page, browser }) => {
  await page.addInitScript(() => {
    Object.defineProperty(Navigator.prototype, 'share', { value: undefined, configurable: true })
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async (text: string) => void ((window as unknown as { copied?: string }).copied = text) },
    })
  })
  await openMe(page)
  const first = await invite(page)

  // 가족 A — 초대 주소로 로그인하면 같은 기록을 본다. 가족은 다시 초대하지 못한다.
  const a = await joinAs(browser, first, links.familyA)
  await expect(a).toHaveURL('/me')
  const shopA = a.locator('[data-section="shop"]')
  await expect(shopA).toContainText('가족으로 함께 보는 기록이에요')
  await expect(a.locator('[data-section="family"]')).toHaveCount(0)
  await shopA.getByRole('link', { name: '콩이' }).click()
  await expect(a.locator('[data-section="item"]')).toHaveCount(2)

  // 기본 보호자 — 새 가족을 한 번 알리고, 읽은 뒤에는 알리지 않는다.
  await page.reload()
  const family = page.locator('[data-section="family"]')
  await expect(family.getByText('가족 한 명이 함께 보기 시작했어요')).toHaveCount(1)
  await expect(family.getByRole('listitem')).toHaveCount(1)
  await expect(family.getByRole('listitem').first()).toContainText(/^가족 1 · \d+월 \d+일에 이음/)
  await page.reload()
  await expect(family.getByText('가족 한 명이 함께 보기 시작했어요')).toHaveCount(0)

  // 가족 B — 이미 쓰인 초대로는 잇지 못하고 안내가 보인다. 새 초대로는 잇는다(로그인한 채).
  const second = await invite(page)
  const b = await joinAs(browser, first, links.familyB)
  await expect(b).toHaveURL('/me?notice=invite')
  await expect(b.locator('[data-section="notice"]')).toContainText('초대가 끝났거나 이미 쓰였어요')
  await expect(b.locator('[data-section="shop"]')).toHaveCount(0)
  await b.goto(second)
  await b.getByRole('button', { name: '로그인하고 함께 보기' }).click()
  await expect(b).toHaveURL('/me')
  await expect(b.locator('[data-section="shop"]')).toContainText('가족으로 함께 보는 기록이에요')

  // 기본 보호자가 가족 1(A)만 끊는다 — B 는 그대로다.
  await page.reload()
  await expect(family.getByRole('listitem')).toHaveCount(2)
  await family.getByRole('listitem').first().getByRole('button', { name: '끊기' }).click()
  await expect(page).toHaveURL('/me')
  await expect(page.locator('[data-section="family"]').getByRole('listitem')).toHaveCount(1)

  await a.goto('/me')
  await expect(a.locator('[data-section="empty"]')).toContainText('아직 이어진 기록이 없어요')
  await b.goto('/me')
  await expect(b.locator('[data-section="shop"]')).toContainText('가족으로 함께 보는 기록이에요')
  await a.context().close()
  await b.context().close()
})

test.describe('자바스크립트를 끈 브라우저', () => {
  test.use({ javaScriptEnabled: false })

  test('사진 모아 보기의 격자와 거르기 링크가 그대로 동작한다', async ({ page }) => {
    await openMe(page)
    await page.getByRole('link', { name: '콩이' }).click()
    await page.locator('[data-section="tabs"]').getByRole('link', { name: '사진' }).click()
    await expect(page.locator('[data-section="grid"]').getByRole('button')).toHaveCount(3)
    await page.locator('[data-section="filter"]').getByRole('link', { name: '전', exact: true }).click()
    await expect(page.locator('[data-section="grid"]').getByRole('button')).toHaveCount(1)
  })
})

for (const width of [320, 390]) {
  test(`폭 ${width} 에서 가족 구역이 있는 내 기록과 사진 모아 보기가 옆으로 밀리지 않는다`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    const fits = async () => {
      const { scroll, inner } = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, inner: window.innerWidth }))
      expect(inner).toBe(width)
      expect(scroll).toBeLessThanOrEqual(inner)
    }
    await openMe(page)
    await expect(page.locator('[data-section="family"]').getByRole('listitem')).toHaveCount(1)
    await fits()
    await page.getByRole('link', { name: '콩이' }).click()
    await page.locator('[data-section="tabs"]').getByRole('link', { name: '사진' }).click()
    await expect(page.locator('[data-section="weights"]')).toBeVisible()
    await fits()
  })
}

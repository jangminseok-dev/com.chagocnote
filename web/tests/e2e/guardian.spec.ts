import { readFileSync } from 'node:fs'

import { expect, test, type Page } from '@playwright/test'

// 보호자 흐름 — 받은 알림장에서 로그인해 잇고, 내 기록에서 지난 알림장을 보고, 끊는다.
// 적힌 순서대로 돈다(workers: 1). 앞 테스트가 이은 연결을 뒤 테스트가 쓰고, 끝에서 끊는다.

type Links = { guardianLive: string; guardianClosed: string; guardianShop: string; guardianLogin: string; guardianOther: string }
const links: Links = JSON.parse(readFileSync('test-results/e2e-links.json', 'utf8'))
const tokenOf = (url: string) => url.slice(url.lastIndexOf('/') + 1)

const CLAIM = '로그인하고 지난 기록 보기'

async function signIn(page: Page, name: string) {
  await page.getByLabel('개발용 로그인 이름').fill(name)
  await page.getByRole('button', { name: '로그인' }).click()
}

/** 로그인해 내 기록을 연다. */
async function openMe(page: Page, name = links.guardianLogin) {
  await page.goto('/login')
  await signIn(page, name)
  await expect(page).toHaveURL('/me')
}

/** 주소가 맞는지 본다. 실패해도 주소를 출력하지 않는다. */
async function expectPath(page: Page, pattern: RegExp, message: string) {
  await expect.poll(() => pattern.test(new URL(page.url()).pathname + new URL(page.url()).search), { message }).toBe(true)
}

test('알림장의 버튼 → 개발용 로그인 → 내 기록에 매장과 아이가 보인다', async ({ page, context }) => {
  await page.goto(links.guardianLive)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('모카의 미용 알림장')
  await page.getByRole('button', { name: CLAIM }).click()

  // 로그인 화면의 주소에 토큰이 없다 — 토큰은 잠깐 사는 쿠키에 맡겼다.
  await expect(page).toHaveURL('/login')
  const claim = (await context.cookies()).find((cookie) => cookie.name === 'cn_claim')
  expect(claim?.httpOnly).toBe(true)
  expect(claim?.value.includes(tokenOf(links.guardianLive))).toBe(false)

  await signIn(page, links.guardianLogin)
  await expect(page).toHaveURL('/me')
  const shop = page.locator('[data-section="shop"]')
  await expect(shop).toHaveCount(1)
  await expect(shop.getByRole('heading', { level: 2 })).toHaveText(links.guardianShop)
  await expect(shop.getByRole('link', { name: '모카' })).toBeVisible()

  // 잇기 쿠키는 쓰고 지웠고, 세션 쿠키는 스크립트가 읽을 수 없다.
  const cookies = await context.cookies()
  expect(cookies.some((cookie) => cookie.name === 'cn_claim')).toBe(false)
  const session = cookies.find((cookie) => cookie.name === 'cn_session')
  expect(session?.httpOnly).toBe(true)
  expect(session?.sameSite).toBe('Lax')
  expect(await page.evaluate(() => document.cookie)).toBe('')
})

test('아이를 누르면 지난 알림장이 한 장 있고, 누르면 알림장이 열린다(로그인 버튼·기간 문구·열람 신호 없음)', async ({ page }) => {
  let viewed = 0
  page.on('request', (req) => {
    if (req.method() === 'POST' && req.url().endsWith('/viewed')) viewed += 1
  })
  await openMe(page)
  await page.getByRole('link', { name: '모카' }).click()
  await expectPath(page, /^\/me\/\d+\?pet=\d+$/, '목록의 주소가 아니다')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('지난 알림장')

  // 끊은 알림장(둘째 방문)은 없다.
  const items = page.locator('[data-section="item"]')
  await expect(items).toHaveCount(1)
  await expect(items.first()).toContainText('모카')
  await expect(items.first()).toContainText('사진·영상 2')
  const cover = items.first().locator('img')
  await expect.poll(() => cover.evaluate((el: HTMLImageElement) => el.complete && el.naturalWidth > 0)).toBe(true)

  await items.first().getByRole('link').click()
  await expectPath(page, /^\/me\/\d+\/\d+$/, '한 장의 주소가 아니다')
  await expect(page).toHaveTitle('모카의 미용 알림장')
  await expect(page.locator('[data-section="note"]')).toContainText('모카가 얌전히 잘 있었어요.')
  await expect(page.locator('[data-section="claim"]')).toHaveCount(0)
  await expect(page.locator('[data-section="foot"]')).not.toContainText('까지 열려요')
  await page.waitForLoadState('networkidle')
  expect(viewed).toBe(0)

  await page.getByRole('link', { name: '지난 알림장' }).click()
  await expectPath(page, /^\/me\/\d+$/, '전체 목록의 주소가 아니다')
})

test('한 장에서 사진을 크게 보고 뒤로 가면 크게 보기만 닫힌다', async ({ page }) => {
  await openMe(page)
  await page.getByRole('link', { name: '모카' }).click()
  await page.locator('[data-section="item"]').first().getByRole('link').click()
  await expectPath(page, /^\/me\/\d+\/\d+$/, '한 장의 주소가 아니다')
  const reportUrl = page.url()

  await page.getByRole('button', { name: /^1번째 .* 크게 보기$/ }).click()
  await expect(page.getByRole('dialog', { name: '크게 보기' })).toBeVisible()
  await page.goBack()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  expect(page.url()).toBe(reportUrl)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('모카의 미용 알림장')
})

test('세션 쿠키가 사라진 뒤(30분 지남) 목록을 열면 로그인으로 가고, 로그인하면 보던 목록으로 돌아온다', async ({ page, context }) => {
  await openMe(page)
  await page.getByRole('link', { name: '모카' }).click()
  await expectPath(page, /^\/me\/\d+\?pet=\d+$/, '목록의 주소가 아니다')
  const listUrl = page.url()

  await context.clearCookies({ name: 'cn_session' })
  await page.goto(listUrl)
  await expectPath(page, /^\/login\?next=%2Fme%2F\d+%3Fpet%3D\d+$/, '로그인으로 가지 않았다')

  await signIn(page, links.guardianLogin)
  await expect.poll(() => page.url() === listUrl, { message: '보던 목록으로 돌아오지 않았다' }).toBe(true)
  await expect(page.locator('[data-section="item"]')).toHaveCount(1)
})

test('다른 계정이 같은 알림장으로 이으려 하면 안내가 보이고 기록은 비어 있다', async ({ page }) => {
  await page.goto(links.guardianLive)
  await page.getByRole('button', { name: CLAIM }).click()
  await signIn(page, links.guardianOther)

  await expect(page).toHaveURL('/me?notice=taken')
  await expect(page.getByRole('status')).toHaveText('이 알림장은 이미 다른 계정에 이어져 있어요. 매장에 문의해 주세요.')
  await expect(page.locator('[data-section="shop"]')).toHaveCount(0)
  await expect(page.locator('[data-section="empty"]')).toContainText('아직 이어진 기록이 없어요')
})

test('닫힌 알림장의 링크는 로그인만 시키고, 이어진 계정이면 기록이 보인다', async ({ page, context }) => {
  await page.goto(links.guardianClosed)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('닫힌 알림장이에요')
  await page.getByRole('link', { name: CLAIM }).click()
  await expect(page).toHaveURL('/login?next=%2Fme')
  // 닫힌 링크의 토큰은 쿠키에 맡기지 않는다.
  expect((await context.cookies()).some((cookie) => cookie.name === 'cn_claim')).toBe(false)

  await signIn(page, links.guardianLogin)
  await expect(page).toHaveURL('/me')
  await expect(page.getByRole('link', { name: '모카' })).toBeVisible()
})

test('로그인한 채 알림장의 버튼을 누르면 바로 내 기록으로 간다', async ({ page }) => {
  await openMe(page)
  await page.goto(links.guardianLive)
  await page.getByRole('button', { name: CLAIM }).click()
  await expect(page).toHaveURL('/me')
  await expect(page.locator('[data-section="shop"]')).toHaveCount(1)
})

test.describe('자바스크립트를 끈 브라우저', () => {
  test.use({ javaScriptEnabled: false })

  test('알림장의 버튼으로 로그인하고 내 기록·목록·한 장을 본다', async ({ page }) => {
    await page.goto(links.guardianLive)
    await page.getByRole('button', { name: CLAIM }).click()
    await signIn(page, links.guardianLogin)
    await expect(page).toHaveURL('/me')
    await page.getByRole('link', { name: '전체 기록 보기' }).click()
    await expect(page.locator('[data-section="item"]')).toHaveCount(1)
    await page.locator('[data-section="item"]').first().getByRole('link').click()
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('모카의 미용 알림장')
  })
})

for (const width of [320, 390]) {
  test(`폭 ${width} 에서 로그인·내 기록·목록이 옆으로 밀리지 않는다`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    const fits = async () => {
      const { scroll, inner } = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, inner: window.innerWidth }))
      expect(inner).toBe(width)
      expect(scroll).toBeLessThanOrEqual(inner)
    }
    await page.goto('/login')
    await fits()
    await signIn(page, links.guardianLogin)
    await expect(page).toHaveURL('/me')
    await expect(page.locator('[data-section="shop"]')).toHaveCount(1)
    await fits()
    await page.getByRole('link', { name: '전체 기록 보기' }).click()
    await expect(page.locator('[data-section="item"]')).toHaveCount(1)
    await fits()
  })
}

test('연결 끊기를 거절하면 그대로이고, 확인하면 내 기록이 비고 그 연결의 목록은 404 다', async ({ page }) => {
  await openMe(page)
  const listPath = await page.getByRole('link', { name: '전체 기록 보기' }).getAttribute('href')

  const questions: string[] = []
  let answer = false
  page.on('dialog', (dialog) => {
    questions.push(dialog.message())
    void (answer ? dialog.accept() : dialog.dismiss())
  })

  await page.getByRole('button', { name: '연결 끊기' }).click()
  await expect.poll(() => questions.length).toBe(1)
  expect(questions[0]).toContain(links.guardianShop)
  await expect(page.locator('[data-section="shop"]')).toHaveCount(1)

  answer = true
  await page.getByRole('button', { name: '연결 끊기' }).click()
  await expect(page.locator('[data-section="empty"]')).toContainText('아직 이어진 기록이 없어요')
  await expect(page.locator('[data-section="shop"]')).toHaveCount(0)

  const gone = await page.goto(listPath!)
  expect(gone?.status()).toBe(404)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('알림장을 찾을 수 없어요')
})

test('끊은 뒤 같은 알림장으로 다시 이을 수 있다', async ({ page }) => {
  await page.goto(links.guardianLive)
  await page.getByRole('button', { name: CLAIM }).click()
  await signIn(page, links.guardianLogin)
  await expect(page).toHaveURL('/me')
  await expect(page.getByRole('link', { name: '모카' })).toBeVisible()
})

test('로그아웃하면 /me 는 로그인으로 간다', async ({ page }) => {
  await openMe(page)
  await page.getByRole('button', { name: '로그아웃' }).click()
  await expect(page).toHaveURL('/login')
  await page.goto('/me')
  await expect(page).toHaveURL('/login?next=%2Fme')
})

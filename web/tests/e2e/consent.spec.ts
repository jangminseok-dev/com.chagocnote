import { readFileSync } from 'node:fs'

import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

type Links = {
  api: string
  staffLogin: string
  consentLive: string
  consentClosed: string
  consentPetPath: string
  consentPetName: string
  consentPetBody: Record<string, unknown>
}
const links: Links = JSON.parse(readFileSync('test-results/e2e-links.json', 'utf8'))

async function staffToken(request: APIRequestContext): Promise<string> {
  const login = await request.post(`${links.api}/v1/auth/social`, { data: { provider: 'dev', token: links.staffLogin } })
  return (await login.json()).access_token
}

/** 매장 쪽 API 로 그 아이를 읽는다. */
async function pet(request: APIRequestContext) {
  const res = await request.get(`${links.api}${links.consentPetPath}`, {
    headers: { Authorization: `Bearer ${await staffToken(request)}` },
  })
  return (await res.json()).pet
}

/** 서명 칸에 마우스로 선을 긋는다. */
async function sign(page: Page) {
  // 서명 칸이 화면 아래에 있으면 마우스가 닿지 않는다 — 먼저 화면 안으로 올린다.
  const canvas = page.getByLabel('서명하는 곳')
  await canvas.scrollIntoViewIfNeeded()
  const box = await canvas.boundingBox()
  if (box === null) throw new Error('서명 칸이 없다')
  await page.mouse.move(box.x + 30, box.y + 30)
  await page.mouse.down()
  await page.mouse.move(box.x + 90, box.y + 60, { steps: 6 })
  await page.mouse.move(box.x + 150, box.y + 30, { steps: 6 })
  await page.mouse.up()
}

/** 서명 구역의 안내 한 줄. Next 의 경로 알림(role=alert)과 섞이지 않게 구역 안에서 찾는다. */
const notice = (page: Page) => page.locator('[data-section="sign"] [role="alert"]')

const send = (page: Page) => page.getByRole('button', { name: '동의하고 보내기' }).click()

/** 화면이 옆으로 밀리지 않는가. */
async function fitsWidth(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow, '화면이 옆으로 넘친다').toBeLessThanOrEqual(0)
}

test('동의서를 열면 문안과 아이·지병이 보이고 글자를 치는 칸은 이름 하나뿐이다', async ({ page }) => {
  const hosts = new Set<string>()
  page.on('request', (req) => hosts.add(new URL(req.url()).host))

  const res = await page.goto(links.consentLive)

  expect(res?.status()).toBe(200)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('미용 동의서')
  await expect(page.locator('[data-section="part"] h2')).toHaveText(['미용 안내', '나이가 많은 아이', '지병이 있는 아이'])
  await expect(page.locator('[data-section="pets"]')).toContainText(links.consentPetName)
  await expect(page.locator('[data-section="pets"]')).toContainText('알려 주신 지병: 심장 질환')
  // 지병의 메모는 보호자에게 가지 않는다.
  await expect(page.locator('body')).not.toContainText('약 복용 중')
  await expect(page.locator('body')).not.toContainText(/법적|효력/)

  // 편의 기준 — 글자를 치는 칸 하나(이름), 서명, 체크, 보내기.
  expect(await page.locator('input[type="text"], input:not([type]), textarea').count()).toBe(1)
  expect(await page.locator('input[type="checkbox"]').count()).toBe(1)
  expect(await page.locator('button[type="submit"]').count()).toBe(1)
  // 브라우저가 부른 곳은 웹 자신뿐이다 — 백엔드를 직접 부르지 않는다.
  expect([...hosts]).toEqual(['127.0.0.1:3010'])
})

test('폭 320 에서도 옆으로 넘치지 않고, 서명하는 손가락을 따라 화면이 구르지 않는다', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 })
  await page.goto(links.consentLive)

  await fitsWidth(page)
  const canvas = page.getByLabel('서명하는 곳')
  expect(await canvas.evaluate((el) => getComputedStyle(el).touchAction)).toBe('none')
  const box = await canvas.boundingBox()
  expect(box?.width).toBeGreaterThan(250)
  expect(Math.round(((box?.width ?? 0) / (box?.height ?? 1)) * 10)).toBe(25) // 5:2
})

test('빠진 것이 있으면 보내지 않고 무엇이 빠졌는지 말한다', async ({ page }) => {
  let submits = 0
  page.on('request', (req) => {
    if (req.method() === 'POST' && req.url().endsWith('/submit')) submits += 1
  })
  await page.goto(links.consentLive)

  await send(page)
  await expect(notice(page)).toHaveText('이름을 적어 주세요')

  await page.getByLabel('이름').fill('김동의')
  await send(page)
  await expect(notice(page)).toHaveText('서명해 주세요')

  await sign(page)
  await send(page)
  await expect(notice(page)).toHaveText('동의에 체크해 주세요')

  // 서명을 지우면 다시 서명하라고 한다.
  await page.getByRole('button', { name: '다시 쓰기' }).click()
  await page.getByLabel('위 내용을 읽었고 동의합니다').check()
  await send(page)
  await expect(notice(page)).toHaveText('서명해 주세요')
  expect(submits).toBe(0)
})

test('자바스크립트가 꺼져 있어도 문안은 읽히고, 켜 달라는 안내가 보인다', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false })
  const page = await context.newPage()

  const res = await page.goto(links.consentLive)

  expect(res?.status()).toBe(200)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('미용 동의서')
  await expect(page.locator('[data-section="part"] h2')).toHaveText(['미용 안내', '나이가 많은 아이', '지병이 있는 아이'])
  // Playwright 가 스크립트를 끄는 방식으로는 크롬이 <noscript> 를 그리지 않는다(파서는 스크립트가 켜진 줄 안다).
  // 그래서 보이는 글자가 아니라 문서에 그 글이 실려 왔는지를 본다 — 스크립트를 실제로 끈 브라우저는 이것을 그린다.
  expect(await page.locator('[data-section="sign"] noscript').evaluate((el) => el.textContent)).toContain(
    '서명하려면 자바스크립트를 켜 주세요',
  )
  await context.close()
})

test('읽는 사이 지병이 더해지면 다시 읽게 하고, 다시 서명하면 보냈어요가 된다', async ({ page, request }) => {
  await page.goto(links.consentLive)
  await page.getByLabel('이름').fill('김동의')
  await sign(page)
  await page.getByLabel('위 내용을 읽었고 동의합니다').check()

  // 보호자가 읽는 사이 매장이 지병을 하나 더 적는다.
  const updated = await request.put(`${links.api}${links.consentPetPath}`, {
    headers: { Authorization: `Bearer ${await staffToken(request)}` },
    data: {
      ...links.consentPetBody,
      conditions: [...(links.consentPetBody.conditions as unknown[]), { type_code: 'allergy', custom_label: null, note: null }],
    },
  })
  expect(updated.status()).toBe(200)

  await send(page)
  await expect(notice(page)).toHaveText('내용이 바뀌었어요. 다시 읽어 주세요')
  await expect(page.locator('[data-section="pets"]')).toContainText('알려 주신 지병: 심장 질환 · 알레르기')
  await expect(page.getByLabel('이름')).toHaveValue('김동의')
  await expect(page.getByLabel('위 내용을 읽었고 동의합니다')).not.toBeChecked()
  expect((await pet(request)).grooming_consent_on).toBeNull()

  await sign(page)
  await page.getByLabel('위 내용을 읽었고 동의합니다').check()
  await send(page)

  await expect(page.getByRole('heading', { level: 1 })).toHaveText('보냈어요')
  await expect(page.locator('[data-section="submitted"]')).toContainText('에서 확인할게요.')
  await expect(page.getByRole('button', { name: '동의하고 보내기' })).toHaveCount(0)
  expect((await pet(request)).grooming_consent_via).toBe('signature')

  // 새로 고쳐도, 뒤로 갔다 와도 보냈어요다 — 두 번 내지 않는다.
  await page.reload()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('보냈어요')
})

test('끊은 링크는 닫힌 서류라고 말하고 로그인 링크가 없다', async ({ page }) => {
  const res = await page.goto(links.consentClosed)

  expect(res?.status()).toBe(200)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('닫힌 서류예요')
  await expect(page.locator('main')).toContainText('매장에 다시 요청해 주세요')
  await expect(page.locator('a[href="/me"]')).toHaveCount(0)
})

test('지어낸 토큰은 404 다', async ({ page }) => {
  const res = await page.goto(`/f/${'a'.repeat(43)}`)

  expect(res?.status()).toBe(404)
})

test('알림장 링크의 토큰을 동의서 주소에 넣어도 열리지 않는다', async ({ page }) => {
  const { live } = JSON.parse(readFileSync('test-results/e2e-links.json', 'utf8')) as { live: string }

  const res = await page.goto(`/f/${live.split('/').pop()}`)

  expect(res?.status()).toBe(404)
})

import { readFileSync } from 'node:fs'

import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

type Links = {
  api: string
  staffLogin: string
  consentLive: string
  consentClosed: string
  consentTwice: string
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

/** 서명 칸의 잉크 — 어두운 점의 수와, 캔버스 좌표 (x, y) 둘레에 잉크가 있는가. 바탕은 희다. */
async function ink(page: Page, at?: { x: number; y: number }) {
  return page.getByLabel('서명하는 곳').evaluate((el, target) => {
    const canvas = el as HTMLCanvasElement
    const { data } = canvas.getContext('2d')!.getImageData(0, 0, canvas.width, canvas.height)
    let dark = 0
    let near = false
    for (let y = 0; y < canvas.height; y += 1) {
      for (let x = 0; x < canvas.width; x += 1) {
        if (data[(y * canvas.width + x) * 4] < 120) {
          dark += 1
          if (target && Math.abs(x - target.x) <= 12 && Math.abs(y - target.y) <= 12) near = true
        }
      }
    }
    return { dark, near }
  }, at ?? null)
}

/** 손가락으로 긋는다(CDP 의 터치). points 는 화면 좌표의 [손가락마다의 길]이다 — 길이가 같아야 한다. */
async function touch(page: Page, paths: { x: number; y: number }[][]) {
  const cdp = await page.context().newCDPSession(page)
  const frame = (index: number) => paths.map((path, id) => ({ x: path[index].x, y: path[index].y, id }))
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: frame(0) })
  for (let index = 1; index < paths[0].length; index += 1) {
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: frame(index) })
  }
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] })
  await cdp.detach()
}

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

test('폭 320 에서 손가락으로 그으면 그은 자리에 선이 남고 화면이 구르지 않는다', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 })
  await page.goto(links.consentLive)
  const canvas = page.getByLabel('서명하는 곳')
  await canvas.scrollIntoViewIfNeeded()
  const box = (await canvas.boundingBox())!
  const scrollBefore = await page.evaluate(() => window.scrollY)
  expect((await ink(page)).dark).toBe(0)
  await expect(page.getByText('여기에 서명해 주세요')).toBeVisible()

  // 칸의 왼쪽 위 1/4 지점에서 오른쪽 아래 3/4 지점까지 — 세로로도 움직인다(화면을 굴리는 손짓과 같다).
  const path = Array.from({ length: 9 }, (_, i) => ({
    x: box.x + box.width * (0.25 + (0.5 * i) / 8),
    y: box.y + box.height * (0.25 + (0.5 * i) / 8),
  }))
  await touch(page, [path])

  expect(await page.evaluate(() => window.scrollY)).toBe(scrollBefore)
  // 화면의 좌표가 600×240 캔버스의 좌표로 맞게 옮겨진다 — 가운데(300, 120)를 지난다.
  const drawn = await ink(page, { x: 300, y: 120 })
  expect(drawn.dark).toBeGreaterThan(200)
  expect(drawn.near).toBe(true)
  expect((await ink(page, { x: 560, y: 30 })).near).toBe(false)
  await expect(page.getByText('여기에 서명해 주세요')).toHaveCount(0)
})

test('서명하는 중에 닿은 둘째 손가락은 선을 긋지 않는다', async ({ page }) => {
  await page.goto(links.consentLive)
  const canvas = page.getByLabel('서명하는 곳')
  await canvas.scrollIntoViewIfNeeded()
  const box = (await canvas.boundingBox())!
  const at = (fx: number, fy: number) => ({ x: box.x + box.width * fx, y: box.y + box.height * fy })
  // 첫 손가락은 왼쪽 위에서 짧게, 둘째 손가락(손바닥)은 오른쪽 아래에 닿아 조금 움직인다.
  const first = [at(0.1, 0.2), at(0.15, 0.25), at(0.2, 0.2), at(0.25, 0.25)]
  const second = [at(0.85, 0.8), at(0.86, 0.82), at(0.87, 0.8), at(0.88, 0.82)]

  await touch(page, [first, second])

  // 두 손가락 사이(가운데)에도, 둘째 손가락의 자리에도 잉크가 없다.
  expect((await ink(page, { x: 300, y: 120 })).near).toBe(false)
  expect((await ink(page, { x: 516, y: 194 })).near).toBe(false)
  expect((await ink(page, { x: 105, y: 54 })).near).toBe(true)
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

  // 버튼은 잠겨 있고, 이름을 치고 Enter 를 눌러도 나가지 않는다 — 적은 이름이 주소에 실리지 않는다.
  await expect(page.getByRole('button', { name: '동의하고 보내기' })).toBeDisabled()
  await page.getByLabel('이름').fill('김동의')
  await page.getByLabel('이름').press('Enter')
  await page.waitForTimeout(300)
  expect(page.url()).toBe(links.consentLive)
  expect(page.url()).not.toContain('signer_name')
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

  // 서명 칸은 비워졌다 — 다시 서명하지 않고 보내면 보내지 않는다.
  expect((await ink(page)).dark).toBe(0)
  await page.getByLabel('위 내용을 읽었고 동의합니다').check()
  await send(page)
  await expect(notice(page)).toHaveText('서명해 주세요')

  await sign(page)
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

test('두 탭에서 같은 링크를 내면 둘째도 오류가 아니라 보냈어요다', async ({ page, context }) => {
  const other = await context.newPage()
  for (const tab of [page, other]) {
    await tab.goto(links.consentTwice)
    await tab.getByLabel('이름').fill('김동의')
    await sign(tab)
    await tab.getByLabel('위 내용을 읽었고 동의합니다').check()
  }

  // 화면을 다시 읽는 요청을 잠깐 붙들어 둔다 — 그 사이에도 보냈다는 것이 보여야 한다(느린 망).
  await page.route('**/f/**', async (route) => {
    if (route.request().method() === 'GET' && route.request().headers().rsc !== undefined) {
      await new Promise((resolve) => setTimeout(resolve, 1500))
    }
    await route.continue()
  })
  await send(page)
  await expect(page.locator('[data-section="sign"] [role="status"]')).toContainText('보냈어요.')
  await expect(page.locator('[data-section="sign"] [role="status"]')).toBeFocused()
  await expect(page.getByRole('button', { name: '동의하고 보내기' })).toHaveCount(0)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('보냈어요')

  // 둘째 탭은 이미 낸 링크에 낸다(410) — 닫힌 서류나 오류가 아니라 보냈어요로 바뀐다.
  await other.bringToFront()
  await send(other)
  await expect(other.getByRole('heading', { level: 1 })).toHaveText('보냈어요')
  await expect(other.locator('body')).not.toContainText('닫힌 서류')
})

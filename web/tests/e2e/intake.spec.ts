import { readFileSync } from 'node:fs'

import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

type Links = {
  api: string
  staffLogin: string
  intakeNew: string
  intakeUpdate: string
  intakeClosed: string
  intakeAnswers: string
  intakePetName: string
  intakePhone: string
}
const links: Links = JSON.parse(readFileSync('test-results/e2e-links.json', 'utf8'))

/** 매장 쪽 API 로 받은 문진표를 읽는다. */
async function answers(request: APIRequestContext) {
  const login = await request.post(`${links.api}/v1/auth/social`, { data: { provider: 'dev', token: links.staffLogin } })
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` }
  const list = (await (await request.get(`${links.api}${links.intakeAnswers}`, { headers })).json()).items
  return Promise.all(
    list.map(async (item: { answer_id: number }) =>
      (await request.get(`${links.api}${links.intakeAnswers}/${item.answer_id}`, { headers })).json()),
  )
}

const chip = (page: Page, name: string) => page.getByRole('button', { name, exact: true })

/** 아이 하나를 적는다 — 글자를 치는 것은 이름뿐이고 나머지는 고른다. */
async function fillPet(page: Page, name: string) {
  await page.getByLabel('아이 이름').fill(name)
  await chip(page, '강아지').click()
  await chip(page, '푸들').click()
  await chip(page, '남아').click()
  await chip(page, '안 했어요').click()
  await chip(page, '몰라요').click()
  await chip(page, '모르겠어요').click()
  await chip(page, '없어요').click()
  await page.getByLabel('개인정보 수집·이용에 동의해요').check()
}

test.describe.configure({ mode: 'serial' })

test('필수로 글자를 치는 칸은 넷 이하이고 폭 320 에서 옆으로 넘치지 않는다', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 })
  await page.goto(links.intakeNew)

  await expect(page.getByRole('heading', { name: '문진표' })).toBeVisible()
  await expect(page.locator('input[data-required-text="true"]')).toHaveCount(3)
  expect(await page.locator('input[data-required-text="true"]').count()).toBeLessThanOrEqual(4)
  // 지병을 고르고 품종을 직접 적는 가장 긴 모양에서도 넘치지 않는다.
  await chip(page, '강아지').click()
  await chip(page, '직접 적기').click()
  await chip(page, '심장 질환').click()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(0)
})

test('빠진 칸이 있으면 보내지 않고 그 칸의 이름으로 말한다', async ({ page }) => {
  await page.goto(links.intakeNew)
  await page.getByLabel('보호자 이름').fill('김새손님')

  await page.getByRole('button', { name: '보내기', exact: true }).click()

  await expect(page.locator('form [role="alert"]')).toHaveText('전화번호를 적어 주세요')
  await expect(page.getByLabel('보호자 이름')).toHaveValue('김새손님')
})

// 아래의 내기 테스트보다 앞에 둔다 — 다 적은 링크에는 폼이 없다.
test('자바스크립트를 끈 브라우저에는 켜 달라는 안내가 실려 오고 버튼이 잠겨 있다', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false })
  const page = await context.newPage()
  await page.goto(links.intakeNew)

  expect(await page.content()).toContain('문진표를 적으려면 자바스크립트를 켜 주세요')
  await expect(page.getByRole('button', { name: '보내기', exact: true })).toBeDisabled()
  await context.close()
})

test('새 손님이 아이 둘을 적어 낸다 — 둘째는 보호자 칸이 없고, 다 적으면 보냈어요 화면이다', async ({ page, request }) => {
  await page.goto(links.intakeNew)
  await page.getByLabel('보호자 이름').fill('김새손님')
  await page.getByLabel('전화번호').fill(links.intakePhone)
  await fillPet(page, '모카')
  await page.getByLabel(/싫어하는 것/).fill('드라이기 소리')

  await page.getByRole('button', { name: '보내고 다른 아이도 적기' }).click()

  // next dev 는 제출 경로를 처음 부를 때 그 자리에서 빌드한다 — 첫 제출은 넉넉히 기다린다.
  await expect(page.locator('form [role="status"]')).toHaveText('모카의 문진표를 보냈어요. 다음 아이를 적어 주세요.', { timeout: 20_000 })
  await expect(page.getByLabel('보호자 이름')).toHaveCount(0)
  await expect(page.getByLabel('아이 이름')).toHaveValue('')
  await fillPet(page, '라떼')
  await page.getByRole('button', { name: '보내기', exact: true }).click()

  await expect(page.locator('[data-section="submitted"]')).toContainText('보냈어요')
  // 새로 고쳐도 같은 화면이고 폼이 다시 열리지 않는다.
  await page.reload()
  await expect(page.locator('[data-section="submitted"]')).toBeVisible()
  await expect(page.getByLabel('아이 이름')).toHaveCount(0)

  const received = (await answers(request)).filter((a) => a.guardian_name === '김새손님')
  expect(received.map((a) => a.pet_name).sort()).toEqual(['라떼', '모카'])
  expect(received.every((a) => a.guardian_phone === links.intakePhone && a.breed === '푸들' && a.weight_kg === null)).toBe(true)
  expect(received.find((a) => a.pet_name === '모카').dislikes).toBe('드라이기 소리')
})

test('다시 받는 문진표는 아이 이름만 보이고 바뀐 것만 적어 보낸다', async ({ page, request }) => {
  await page.goto(links.intakeUpdate)

  await expect(page.getByRole('heading', { name: `${links.intakePetName}의 문진표` })).toBeVisible()
  await expect(page.getByText('바뀐 것만 적어 주세요. 적지 않은 것은 그대로 둘게요.')).toBeVisible()
  await expect(page.getByLabel('보호자 이름')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '보내고 다른 아이도 적기' })).toHaveCount(0)
  // 지금 값(품종·몸무게)이 화면에 없다.
  await expect(page.getByLabel('몸무게(kg)')).toHaveValue('')
  await expect(page.getByText('말티즈')).toHaveCount(0)

  await page.getByLabel('몸무게(kg)').fill('5.1')
  await page.getByLabel('개인정보 수집·이용에 동의해요').check()
  await page.getByRole('button', { name: '보내기', exact: true }).click()

  await expect(page.locator('[data-section="submitted"]')).toContainText('보냈어요')
  const updated = (await answers(request)).find((a) => a.mode === 'update')
  expect([updated.pet_name, updated.weight_kg, updated.breed]).toEqual([links.intakePetName, 5.1, null])
})

test('끊은 문진표 링크는 닫힌 화면이고 폼이 없다', async ({ page }) => {
  const response = await page.goto(links.intakeClosed)

  expect(response?.status()).toBe(200)
  await expect(page.getByLabel('아이 이름')).toHaveCount(0)
  await expect(page.getByRole('link', { name: /로그인/ })).toHaveCount(0)
})

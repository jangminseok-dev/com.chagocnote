// 실제 브라우저 흐름(pnpm e2e)의 준비물 — 게이트웨이로 매장·고객·방문·사진 둘(전·후)·기록을 만들고
// 알림장을 보낸 뒤 끊고 다시 보내, 끊은 링크 하나와 살아 있는 링크 하나를 test-results/e2e-links.json 에 쓴다.
// 화면이 옆으로 밀리지 않는지 볼 긴 글 알림장도 하나 더 만든다(같은 매장·반려동물의 다른 방문).
// 보호자 흐름(guardian.spec.ts)이 쓸 둘째 고객도 만든다 — 살아 있는 알림장 하나와 끊은 알림장 하나, 로그인할 이름 둘.
// 위의 살아 있는 링크는 "아직 아무도 열지 않았다"를 보는 데 쓰므로 보호자 흐름과 나눠 쓰지 않는다.
// 동의서 흐름(consent.spec.ts)이 쓸 고객 둘도 만든다 — 서명할 동의서 링크 하나와 끊은 링크 하나.
// 사용: infra/ 에서 개발 스택과 web 을 띄운 뒤 web/ 에서 pnpm e2e:prepare → pnpm e2e.
// e2e 는 살아 있는 링크를 아직 아무도 열지 않았다고 보므로 e2e 를 돌릴 때마다 먼저 이것을 돌린다.
// 개발 DB 와 버킷에 확인용 매장·유저·고객·방문·사진·알림장 링크가 남는다.
// 링크(토큰)는 화면에 찍지 않는다. 링크 파일은 gitignore 안(test-results)에 있다.
import { execFileSync } from 'node:child_process'
import { mkdirSync, writeFileSync } from 'node:fs'

const BASE = process.env.BASE ?? 'http://127.0.0.1:8080'
const STAMP = Math.floor(Date.now() / 1000)
const PHONE = `010${String(STAMP % 100000000).padStart(8, '0')}`
// 30×40 회색 JPEG. 표시용·썸네일에도 그대로 올린다 — 브라우저가 실제로 그릴 수 있는 그림이면 된다.
const JPEG = Buffer.from(
  '/9j/4AAQSkZJRgABAgAAAQABAAD//gAQTGF2YzYyLjI4LjEwMgD/2wBDAAgQEBMQExYWFhYWFhoYGhsbGxoaGhobGxsdHR0iIiIdHR0bGx0dICAiIiUmJSMjIiMmJigoKDAwLi44ODpFRVP/xABMAAEBAAAAAAAAAAAAAAAAAAAABwEBAQAAAAAAAAAAAAAAAAAAAAQQAQAAAAAAAAAAAAAAAAAAAAARAQAAAAAAAAAAAAAAAAAAAAD/wAARCAAoAB4DASIAAhEAAxEA/9oADAMBAAIRAxEAPwCkgIFYAAAAAAAAAD//2Q==',
  'base64',
)

async function call(method, path, token, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token && { Authorization: `Bearer ${token}` }) },
    body: body && JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${method} ${path.replace(/\d+/g, '{id}')} → ${res.status}`)
  return res.status === 204 ? null : res.json()
}
const login = (name) => call('POST', '/v1/auth/social', null, { provider: 'dev', token: name })

// 어제 11시(서울). 실행 시각과 상관없이 방문이 자정을 넘기지 않는다.
function yesterday11() {
  const seoul = new Date(Date.now() + 9 * 3600_000 - 24 * 3600_000)
  return `${seoul.toISOString().slice(0, 10)}T11:00:00+09:00`
}

async function photo(S, token) {
  const issued = await call('POST', `${S}/media/uploads`, token, {
    kind: 'photo', content_type: 'image/jpeg', byte_size: JPEG.length, width: 300, height: 400,
  })
  for (const url of Object.values(issued.puts)) {
    const res = await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'image/jpeg' }, body: JPEG })
    if (!res.ok) throw new Error(`사진 올리기 → ${res.status}`)
  }
  await call('POST', `${S}/media/${issued.media_id}/confirm`, token)
  return issued.media_id
}

// 1. 매장과 직원
const op = await login(`e2e-op-${STAMP}`)
execFileSync('docker', ['compose', '-f', '../infra/docker-compose.yml', 'exec', '-T', 'backend',
  'python', 'scripts/grant_operator.py', String(op.user_id)], { stdio: 'ignore' })
const shop = await call('POST', '/v1/platform/shops', op.access_token, { name: `알림장웹-${STAMP}` })
const owner = await login(`e2e-owner-${STAMP}`)
await call('POST', '/v1/invites/accept', owner.access_token, { code: shop.owner_invite_code })
const S = `/v1/shops/${shop.shop_id}`
const staffLogin = `e2e-staff-${STAMP}`
const staff = (await login(staffLogin)).access_token
await call('POST', '/v1/invites/accept', staff, { code: (await call('POST', `${S}/invites`, owner.access_token)).code })

// 2. 고객·방문·기록
const registered = await call('POST', `${S}/customers`, staff, {
  customer: { name: '김보호', phone: PHONE, marketing_consent: true },
  pet: { name: '두부', species: 'dog', breed: '말티즈', sex: 'female', neutered: true, birth_year: 2021, weight_kg: 3.2, no_known_conditions: true },
})
const pet = registered.pets[0].pet_id
const startsAt = yesterday11()
const visit = (await call('POST', `${S}/visits`, staff, {
  customer_id: registered.customer.customer_id, pet_ids: [pet], starts_at: startsAt,
})).visits[0].visit_id
const V = `${S}/visits/${visit}`
await call('POST', `${S}/visits/transitions`, staff, { visit_ids: [visit], action: 'start' })
const before = await photo(S, staff)
const after = await photo(S, staff)
const menu = (await call('GET', `${S}/menus`, staff)).items[0].menu_id
await call('PUT', `${V}/record`, staff, {
  weight_kg: 3.4, care_note: '눈물 자국을 닦았어요.\n다음 주에 한 번 더 봐 주세요.', payment_method: 'card', total_amount: 25000,
  items: [{ menu_id: menu, amount: 25000 }],
  media: [{ media_id: before, phase: 'before', sort_order: 0 }, { media_id: after, phase: 'after', sort_order: 0 }],
})
await call('POST', `${S}/visits/transitions`, staff, { visit_ids: [visit], action: 'complete' })

// 3. 보내고 끊고 다시 보낸다 — 끊은 링크와 살아 있는 링크
const closed = (await call('PUT', `${V}/report`, staff, { hidden_media_ids: [] })).link.url
await call('DELETE', `${V}/report`, staff)
const live = (await call('PUT', `${V}/report`, staff, { hidden_media_ids: [] })).link.url

// 4. 긴 글 알림장 — 띄어쓰기 없는 긴 글·긴 이름. 길이는 백엔드 스키마의 한도다
//    (주소 255: update_shop_schema, 메뉴 이름 30: create_menu_schema, 케어 메모 1000: put_visit_record_schema).
//    매장 주소는 이 확인용 매장의 설정이라 살아 있는 링크에도 보인다.
await call('PUT', `${S}/settings`, owner.access_token, {
  name: shop.name, address: '서울특별시마포구아주긴길이름로'.repeat(20).slice(0, 255),
})
const longMenu = (await call('POST', `${S}/menus`, owner.access_token, { name: '띄어쓰기없는아주긴메뉴이름'.repeat(3).slice(0, 30) })).menu_id
const longVisit = (await call('POST', `${S}/visits`, staff, {
  customer_id: registered.customer.customer_id, pet_ids: [pet], starts_at: startsAt.replace('T11:', 'T15:'),
})).visits[0].visit_id
const LV = `${S}/visits/${longVisit}`
await call('POST', `${S}/visits/transitions`, staff, { visit_ids: [longVisit], action: 'start' })
await call('PUT', `${LV}/record`, staff, {
  care_note: `${'a'.repeat(600)}\nhttps://example.com/${'b'.repeat(300)}\n${'🐶'.repeat(60)}`,
  total_amount: 1234567, items: [{ menu_id: longMenu, amount: 1234567 }],
})
await call('POST', `${S}/visits/transitions`, staff, { visit_ids: [longVisit], action: 'complete' })
const long = (await call('PUT', `${LV}/report`, staff, { hidden_media_ids: [] })).link.url

// 5. 보호자 흐름 — 둘째 고객(반려동물 모카)의 방문 둘. 하나는 사진과 함께 보내고, 하나는 보낸 뒤 끊는다.
const second = await call('POST', `${S}/customers`, staff, {
  customer: { name: '김기록', phone: `010${String((STAMP + 1) % 100000000).padStart(8, '0')}`, marketing_consent: true },
  pet: { name: '모카', species: 'dog', breed: '푸들', sex: 'male', neutered: true, birth_year: 2020, weight_kg: 4.1, no_known_conditions: true },
})
async function guardianVisit(hour, withPhoto) {
  const id = (await call('POST', `${S}/visits`, staff, {
    customer_id: second.customer.customer_id, pet_ids: [second.pets[0].pet_id], starts_at: startsAt.replace('T11:', `T${hour}:`),
  })).visits[0].visit_id
  await call('POST', `${S}/visits/transitions`, staff, { visit_ids: [id], action: 'start' })
  const media = withPhoto ? [{ media_id: await photo(S, staff), phase: 'after', sort_order: 0 }, { media_id: await photo(S, staff), phase: 'before', sort_order: 0 }] : []
  await call('PUT', `${S}/visits/${id}/record`, staff, {
    care_note: '모카가 얌전히 잘 있었어요.', payment_method: 'card', total_amount: 25000, items: [{ menu_id: menu, amount: 25000 }], media,
  })
  await call('POST', `${S}/visits/transitions`, staff, { visit_ids: [id], action: 'complete' })
  return `${S}/visits/${id}`
}
const guardianLive = (await call('PUT', `${await guardianVisit('13', true)}/report`, staff, { hidden_media_ids: [] })).link.url
const closedVisit = await guardianVisit('17', false)
const guardianClosed = (await call('PUT', `${closedVisit}/report`, staff, { hidden_media_ids: [] })).link.url
await call('DELETE', `${closedVisit}/report`, staff)

// 6. 동의서 흐름(consent.spec.ts) — 노령·지병 아이 둘(고객도 둘). 하나는 서명할 링크, 하나는 보낸 뒤 끊은 링크.
const seniorYear = new Date().getFullYear() - 12
const HEART = { type_code: 'heart_disease', custom_label: null, note: '약 복용 중' }
const consentPet = (name) => ({
  name, species: 'dog', breed: '말티즈', sex: 'female', neutered: true, birth_year: seniorYear, weight_kg: 3.2,
  no_known_conditions: false, conditions: [HEART],
})
async function consentFamily(name, offset) {
  const family = await call('POST', `${S}/customers`, staff, {
    customer: { name: '김동의', phone: `010${String((STAMP + offset) % 100000000).padStart(8, '0')}`, marketing_consent: true },
    pet: consentPet(name),
  })
  const petId = family.pets[0].pet_id
  return { petId, sent: await call('POST', `${S}/consent-forms`, staff, { pet_ids: [petId] }) }
}
const signing = await consentFamily('초코', 2)
const revoked = await consentFamily('라떼', 3)
const twice = await consentFamily('두유', 4) // 두 탭에서 같은 링크를 내는 테스트가 쓴다
await call('DELETE', `${S}/forms/${revoked.sent.form_id}`, staff)

mkdirSync('test-results', { recursive: true })
writeFileSync('test-results/e2e-links.json', JSON.stringify(
  {
    live, closed, long, visitDate: startsAt.slice(0, 10), api: BASE, staffLogin, visitPath: V,
    guardianLive, guardianClosed, guardianShop: shop.name,
    guardianLogin: `e2e-guardian-${STAMP}`, guardianOther: `e2e-guardian-other-${STAMP}`,
    consentLive: signing.sent.url, consentClosed: revoked.sent.url, consentTwice: twice.sent.url, consentPetPath: `${S}/pets/${signing.petId}`,
    consentPetName: '초코', consentPetBody: consentPet('초코'),
  }, null, 2,
))
console.log(`준비 완료 — 매장 ${shop.shop_id}, 방문 ${visit}. 링크는 test-results/e2e-links.json 에 있다.`)

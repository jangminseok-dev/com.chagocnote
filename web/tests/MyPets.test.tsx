import { render, screen, within } from '@testing-library/react'
import { expect, test } from 'vitest'

import { MyPets, type ShopPets } from '../components/MyPets'

const EMPTY_TITLE = '아직 이어진 기록이 없어요'
const EMPTY_TEXT =
  '매장에서 받은 미용 알림장을 열고 [로그인하고 지난 기록 보기]를 눌러 주세요. 알림장이 닫혔다면 매장에 다시 보내 달라고 요청해 주세요.'
const TAKEN = '이 알림장은 이미 다른 계정에 이어져 있어요. 매장에 문의해 주세요.'

const HISS: ShopPets = {
  link: { link_id: 11, shop_name: 'Hiss Haus', linked_at: '2026-11-01T10:00:00+09:00' },
  pets: [
    { pet_id: 7, name: '두부' },
    { pet_id: 8, name: null },
  ],
}
const SECOND: ShopPets = { link: { link_id: 12, shop_name: '둘째 매장', linked_at: '2026-11-05T15:30:00+09:00' }, pets: [] }

function show(shops: ShopPets[], notice: 'taken' | 'invite' | null = null) {
  const { container } = render(<MyPets shops={shops} notice={notice} />)
  const all = (name: string) => [...container.querySelectorAll<HTMLElement>(`[data-section="${name}"]`)]
  return { container, all }
}

test('머리에 제목 "내 기록" 이 있다', () => {
  const { all } = show([HISS])

  expect(all('me-head')).toHaveLength(1)
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('내 기록')
})

test('매장마다 이름·이은 날·아이들 링크·전체 기록 링크·연결 끊기 폼이 있다', () => {
  const { all } = show([HISS, SECOND])

  const shops = all('shop')
  expect(shops).toHaveLength(2)
  const hiss = within(shops[0])
  expect(hiss.getByRole('heading', { level: 2 })).toHaveTextContent('Hiss Haus')
  expect(shops[0]).toHaveTextContent('2026년 11월 1일부터')
  expect(hiss.getByRole('link', { name: '두부' })).toHaveAttribute('href', '/me/11?pet=7')
  expect(hiss.getByRole('link', { name: '전체 기록 보기' })).toHaveAttribute('href', '/me/11')
  const form = shops[0].querySelector('form')!
  expect(form.getAttribute('action')).toBe('/me/11/unlink')
  expect(form.getAttribute('method')).toBe('post')
  expect(within(form).getByRole('button', { name: '연결 끊기' })).toHaveAttribute('type', 'submit')
  expect(shops[1].querySelector('form')!.getAttribute('action')).toBe('/me/12/unlink')
})

test('이름이 없는 아이는 "우리 아이" 다', () => {
  const { all } = show([HISS])

  expect(within(all('shop')[0]).getByRole('link', { name: '우리 아이' })).toHaveAttribute('href', '/me/11?pet=8')
})

test('아이가 없는 연결은 "아직 받은 알림장이 없어요" 이고 전체 기록 링크는 있다', () => {
  const { all } = show([SECOND])

  const [shop] = all('shop')
  expect(shop).toHaveTextContent('아직 받은 알림장이 없어요')
  expect(within(shop).getAllByRole('link')).toHaveLength(1)
  expect(within(shop).getByRole('link', { name: '전체 기록 보기' })).toHaveAttribute('href', '/me/12')
})

test('아이가 있는 연결에는 "아직 받은 알림장이 없어요" 가 없다', () => {
  const { all } = show([HISS])

  expect(all('shop')[0]).not.toHaveTextContent('아직 받은 알림장이 없어요')
})

test('연결이 없으면 안내가 보이고 매장 구역이 없다', () => {
  const { all } = show([])

  expect(all('shop')).toHaveLength(0)
  const [empty] = all('empty')
  expect(within(empty).getByRole('heading', { level: 2 })).toHaveTextContent(EMPTY_TITLE)
  expect(empty).toHaveTextContent(EMPTY_TEXT)
})

test('연결이 있으면 빈 안내가 없다', () => {
  const { all } = show([HISS])

  expect(all('empty')).toHaveLength(0)
})

test('notice 가 taken 이면 안내가 보이고 null 이면 없다', () => {
  const { unmount } = render(<MyPets shops={[]} notice="taken" />)
  expect(screen.getByRole('status')).toHaveTextContent(TAKEN)
  unmount()

  const { all } = show([HISS])
  expect(all('notice')).toHaveLength(0)
  expect(screen.queryByRole('status')).toBeNull()
})

test('로그아웃 폼이 /logout 으로 간다', () => {
  const { all } = show([])

  const form = all('logout')[0].querySelector('form')!
  expect(form.getAttribute('action')).toBe('/logout')
  expect(form.getAttribute('method')).toBe('post')
  expect(within(form).getByRole('button', { name: '로그아웃' })).toHaveAttribute('type', 'submit')
})

test('매장 이름과 아이 이름의 태그는 글자로 보인다', () => {
  const { container } = show([
    { link: { ...HISS.link, shop_name: '<script>alert(1)</script>' }, pets: [{ pet_id: 7, name: '<img src=x>' }] },
  ])

  expect(container.querySelector('script')).toBeNull()
  expect(container.querySelector('img')).toBeNull()
  expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('<script>alert(1)</script>')
  expect(screen.getByRole('link', { name: '<img src=x>' })).toBeInTheDocument()
})

// ── 가족과 함께 보기(⑫ 설계 3.5) ───────────────────────────────────────────

const PRIMARY: ShopPets = {
  ...HISS,
  link: { ...HISS.link, role: 'primary', family_count: 2, family_max: 3 },
  family: [
    { family_id: 21, linked_at: '2026-11-16T10:00:00+09:00', unseen: true },
    { family_id: 22, linked_at: '2026-11-20T10:00:00+09:00', unseen: false },
  ],
}

test('기본 보호자에게는 한 사람에 한 줄(가족 N · 이은 날)과 끊기, 모두 끊기, 초대 단추와 설명이 있다', () => {
  const { all } = show([PRIMARY])

  const family = all('family')[0]
  expect(family).toHaveTextContent('함께 보는 가족')
  const rows = within(family).getAllByRole('listitem')
  expect(rows.map((row) => row.textContent?.replace('끊기', '').trim())).toEqual(['가족 1 · 11월 16일에 이음', '가족 2 · 11월 20일에 이음'])
  expect(rows[0].querySelector('form')).toHaveAttribute('action', '/me/11/family-unlink')
  expect(rows[0].querySelector('input[name="family_id"]')).toHaveAttribute('value', '21')
  expect(within(family).getByRole('button', { name: '가족 모두 끊기' })).toBeInTheDocument()
  expect(within(family).getByRole('button', { name: '가족과 함께 보기' })).toBeInTheDocument()
  expect(family).toHaveTextContent('초대를 받은 가족이 로그인하면 같은 기록을 함께 봐요. 초대는 하루 동안, 한 사람만 쓸 수 있어요.')
  expect(screen.getByRole('status')).toHaveTextContent('11월 16일에 가족 한 명이 함께 보기 시작했어요')
})

test('가족이 다 찼으면 초대 단추 대신 다 찼다는 말이 있고, 매장이 0 명으로 정했으면 가족 구역이 없다', () => {
  const full = show([{ ...PRIMARY, link: { ...PRIMARY.link, family_count: 3, family_max: 3 } }])
  expect(within(full.all('family')[0]).queryByRole('button', { name: '가족과 함께 보기' })).toBeNull()
  expect(full.all('family')[0]).toHaveTextContent('함께 볼 수 있는 가족이 다 찼어요')
  full.container.remove()

  const off = show([{ ...HISS, link: { ...HISS.link, role: 'primary', family_count: 0, family_max: 0 }, family: [] }])
  expect(off.all('family')).toHaveLength(0)
})

test('가족 연결이면 가족으로 함께 보는 기록이라고 적고 초대·가족 목록이 없다', () => {
  const { all } = show([{ ...HISS, link: { ...HISS.link, role: 'family', family_count: 0, family_max: 0 } }])

  expect(all('shop')[0]).toHaveTextContent('가족으로 함께 보는 기록이에요')
  expect(all('family')).toHaveLength(0)
})

test('초대가 끝났으면 한 가지 안내가 있다', () => {
  show([PRIMARY], 'invite')

  expect(screen.getAllByRole('status').map((s) => s.textContent)).toContain('초대가 끝났거나 이미 쓰였어요. 가족에게 새 초대를 부탁해 주세요.')
})


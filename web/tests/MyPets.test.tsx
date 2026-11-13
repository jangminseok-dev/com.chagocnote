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

function show(shops: ShopPets[], notice: 'taken' | null = null) {
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

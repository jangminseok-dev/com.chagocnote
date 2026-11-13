import { render, screen, within } from '@testing-library/react'
import { expect, test } from 'vitest'

import { ReportList } from '../components/ReportList'
import type { ReportItem, ReportPage } from '../lib/guardian'

const item = (overrides: Partial<ReportItem>): ReportItem => ({
  report_id: 501,
  visit_date: '2026-09-28',
  pet_id: 7,
  pet_name: '두부',
  cover: { url: 'https://media.test/cover.jpg?X-Amz-Signature=s', width: 1200, height: 1600 },
  media_count: 4,
  ...overrides,
})
const BARE = item({ report_id: 502, visit_date: '2026-08-15', pet_id: null, pet_name: null, cover: null, media_count: 0 })

function show(page: ReportPage, petId: number | null = null) {
  const { container } = render(<ReportList linkId={11} petId={petId} page={page} />)
  const all = (name: string) => [...container.querySelectorAll<HTMLElement>(`[data-section="${name}"]`)]
  return { container, all }
}

test('머리에 내 기록으로 가는 링크와 제목 "지난 알림장" 이 있다', () => {
  const { all } = show({ items: [item({})], next_cursor: null })

  const [head] = all('list-head')
  expect(within(head).getByRole('link', { name: '내 기록' })).toHaveAttribute('href', '/me')
  expect(within(head).getByRole('heading', { level: 1 })).toHaveTextContent('지난 알림장')
})

test('항목마다 한 장으로 가는 링크·날짜·이름·사진 수·대표 그림이 있다', () => {
  const { all } = show({ items: [item({})], next_cursor: null })

  const [first] = all('item')
  const link = within(first).getByRole('link')
  expect(link).toHaveAttribute('href', '/me/11/501')
  expect(link).toHaveTextContent('2026년 9월 28일')
  expect(link).toHaveTextContent('두부')
  expect(link).toHaveTextContent('사진·영상 4')
  const img = first.querySelector('img')!
  expect(img).toHaveAttribute('src', 'https://media.test/cover.jpg?X-Amz-Signature=s')
  expect(img).toHaveAttribute('alt', '')
  expect(img).toHaveAttribute('loading', 'lazy')
  expect(img).toHaveAttribute('width', '1200')
  expect(img).toHaveAttribute('height', '1600')
})

test('이름·대표·사진이 없는 항목은 날짜만 있고 그림이 없다', () => {
  const { all } = show({ items: [BARE], next_cursor: null })

  const [only] = all('item')
  expect(within(only).getByRole('link')).toHaveAttribute('href', '/me/11/502')
  expect(only.querySelector('img')).toBeNull()
  expect(only).not.toHaveTextContent('사진·영상')
  expect(within(only).getByRole('link').textContent).toBe('2026년 8월 15일')
})

test('항목은 받은 순서대로다', () => {
  const { all } = show({ items: [item({}), BARE, item({ report_id: 503 })], next_cursor: null })

  expect(all('item').map((el) => el.querySelector('a')!.getAttribute('href'))).toEqual(['/me/11/501', '/me/11/502', '/me/11/503'])
})

test('다음 쪽이 있으면 "더 보기" 가 cursor 를 담는다', () => {
  const { all } = show({ items: [item({})], next_cursor: 'c2' })

  expect(within(all('more')[0]).getByRole('link', { name: '더 보기' })).toHaveAttribute('href', '/me/11?cursor=c2')
})

test('아이로 거른 목록의 "더 보기" 는 pet 도 담는다', () => {
  show({ items: [item({})], next_cursor: 'c2' }, 7)

  expect(screen.getByRole('link', { name: '더 보기' })).toHaveAttribute('href', '/me/11?pet=7&cursor=c2')
})

test('cursor 의 글자는 주소에 맞게 바뀐다', () => {
  show({ items: [item({})], next_cursor: 'a=b' })

  expect(screen.getByRole('link', { name: '더 보기' })).toHaveAttribute('href', '/me/11?cursor=a%3Db')
})

test('다음 쪽이 없으면 "더 보기" 가 없다', () => {
  const { all } = show({ items: [item({})], next_cursor: null })

  expect(all('more')).toHaveLength(0)
})

test('항목이 없으면 "아직 받은 알림장이 없어요" 이고 목록이 없다', () => {
  const { all, container } = show({ items: [], next_cursor: null })

  expect(all('empty')[0]).toHaveTextContent('아직 받은 알림장이 없어요')
  expect(all('item')).toHaveLength(0)
  expect(container.querySelector('ul')).toBeNull()
})

test('이름의 태그는 글자로 보인다', () => {
  const { container } = show({ items: [item({ pet_name: '<img src=x onerror=alert(1)>', cover: null })], next_cursor: null })

  expect(container.querySelector('img')).toBeNull()
  expect(container).toHaveTextContent('<img src=x onerror=alert(1)>')
})

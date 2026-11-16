import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { PhotoArchive } from '../components/PhotoArchive'
import { WeightChart } from '../components/WeightChart'
import type { MediaItem } from '../lib/guardian'
import { makeMedia, makeVideo } from './report-fixture'

// 아이의 사진 모아 보기(⑫ 설계 3.3·3.4).
beforeEach(() => {
  vi.spyOn(window.history, 'pushState').mockImplementation(() => {})
  vi.spyOn(window.history, 'back').mockImplementation(() => {})
})
afterEach(() => {
  vi.restoreAllMocks()
  cleanup()
})

const item = (reportId: number, date: string, extra = {}): MediaItem =>
  ({ ...makeMedia(), report_id: reportId, visit_date: date, ...extra })
const ITEMS: MediaItem[] = [
  item(502, '2026-11-01', { display_url: 'https://media.test/1.jpg', download_url: 'https://media.test/1.jpg?dl' }),
  item(502, '2026-11-01', { phase: 'before', download_url: 'https://media.test/2.jpg?dl' }),
  { ...makeVideo(), report_id: 501, visit_date: '2026-10-03' },
]
const WEIGHTS = [{ visit_date: '2026-10-03', weight_kg: 3.1 }, { visit_date: '2026-11-01', weight_kg: 3.2 }]

function show(extra: Partial<Parameters<typeof PhotoArchive>[0]> = {}) {
  const { container } = render(
    <PhotoArchive linkId={11} petId={7} filter={{ year: null, phase: null }}
      page={{ items: ITEMS, next_cursor: 'c2', years: [2026, 2025] }} weights={WEIGHTS} openedAt={Date.now()} {...extra} />,
  )
  const sections = () => [...container.querySelectorAll('[data-section]')].map((el) => el.getAttribute('data-section'))
  const section = (name: string) => container.querySelector<HTMLElement>(`[data-section="${name}"]`)!
  return { container, sections, section }
}

test('머리·거르기·한 쪽 저장·몸무게·격자·더 보기가 차례로 있다', () => {
  const { sections } = show()

  expect(sections()).toEqual(['photos-head', 'tabs', 'filter', 'save-all', 'weights', 'grid', 'more'])
})

test('[알림장]·[사진]을 오가고 거르기는 아이를 지키며 연도·전후를 고른다', () => {
  const { section } = show({ filter: { year: 2026, phase: null } })

  expect(within(section('tabs')).getByRole('link', { name: '알림장' })).toHaveAttribute('href', '/me/11?pet=7')
  const filter = within(section('filter'))
  expect(filter.getByRole('link', { name: '전체 연도' })).toHaveAttribute('href', '/me/11/photos?pet=7')
  expect(filter.getByRole('link', { name: '2025년' })).toHaveAttribute('href', '/me/11/photos?pet=7&year=2025')
  expect(filter.getByRole('link', { name: '2026년' })).toHaveAttribute('aria-current', 'true')
  expect(filter.getByRole('link', { name: '후' })).toHaveAttribute('href', '/me/11/photos?pet=7&year=2026&phase=after')
})

test('날짜마다 묶고 묶음에는 그 알림장의 줄 id 가 있다 — 한 장에서 돌아오면 그 자리다', () => {
  const { section, container } = show()

  expect(within(section('grid')).getAllByRole('heading').map((h) => h.textContent)).toEqual(['2026년 11월 1일', '2026년 10월 3일'])
  expect(container.querySelector('#r502')).not.toBeNull()
  expect(container.querySelector('#r501')).not.toBeNull()
})

test('누르면 크게 보기가 열리고 아래에 그 알림장으로 가는 줄이 있다', () => {
  show()

  fireEvent.click(screen.getAllByRole('button', { name: /크게 보기/ })[2])

  const dialog = within(screen.getByRole('dialog'))
  expect(dialog.getByText('3 / 3')).toBeInTheDocument()
  expect(dialog.getByRole('link', { name: '10월 3일 알림장 보기' })).toHaveAttribute('href', '/me/11/501')
})

test('크게 보기 아래의 알림장 줄은 쌓아 둔 방문 기록 칸을 그 한 장으로 바꿔 끼운다 — 뒤로 가기 한 번이면 사진이다', () => {
  const replace = vi.fn()
  vi.stubGlobal('location', { ...window.location, replace })
  try {
    show()
    fireEvent.click(screen.getAllByRole('button', { name: /크게 보기/ })[2])

    const link = within(screen.getByRole('dialog')).getByRole('link', { name: '10월 3일 알림장 보기' })
    // fireEvent 는 기본 동작을 막았으면 false 다.
    expect(fireEvent.click(link)).toBe(false)
    expect(replace).toHaveBeenCalledWith('/me/11/501')
    expect(window.history.back).not.toHaveBeenCalled()
  } finally {
    vi.unstubAllGlobals()
  }
})

test('이 쪽만 받는다고 적고, 다음 쪽이 있으면 넘어가서 다시 누르라고 한다', () => {
  const { section } = show()

  expect(within(section('save-all')).getByRole('button', { name: '이 화면의 사진 · 영상 모두 저장' })).toBeInTheDocument()
  expect(section('save-all')).toHaveTextContent('이 쪽의 3개를 받아요. 다음 쪽은 넘어가서 한 번 더 눌러 주세요')
  expect(within(section('more')).getByRole('link', { name: '더 보기' })).toHaveAttribute('href', '/me/11/photos?pet=7&cursor=c2')
})

test('아이를 고르지 않았거나 몸무게가 없으면 몸무게 구역이 없고, 사진이 없으면 빈 화면이다', () => {
  expect(show({ petId: null, weights: null }).sections()).not.toContain('weights')
  cleanup()
  expect(show({ weights: [] }).sections()).not.toContain('weights')
  cleanup()
  const empty = show({ page: { items: [], next_cursor: null, years: [] }, weights: null })
  expect(empty.sections()).toEqual(['photos-head', 'tabs', 'empty'])
  expect(empty.section('empty')).toHaveTextContent('아직 받은 사진이 없어요')
})

test('거른 결과가 비면 거르기는 남아 다른 조건을 고를 수 있고, 그 조건에 없다고 말한다', () => {
  const { sections, section } = show({ filter: { year: null, phase: 'before' }, page: { items: [], next_cursor: null, years: [2026] } })

  expect(sections()).toEqual(['photos-head', 'tabs', 'filter', 'empty', 'weights'])
  expect(section('empty')).toHaveTextContent('이 조건의 사진이 없어요')
  expect(within(section('filter')).getByRole('link', { name: '전체' })).toHaveAttribute('href', '/me/11/photos?pet=7')
})

test('사진 없이 몸무게만 받은 아이도 몸무게를 본다', () => {
  const { sections, section } = show({ page: { items: [], next_cursor: null, years: [] } })

  expect(sections()).toEqual(['photos-head', 'tabs', 'empty', 'weights'])
  expect(section('empty')).toHaveTextContent('아직 받은 사진이 없어요')
})

test('몸무게는 날짜와 kg 의 목록이고 점이 둘 이상이면 선 그림이 있다 — 풀이는 없다', () => {
  const { container } = render(<WeightChart items={WEIGHTS} />)

  expect(screen.getAllByRole('listitem').map((li) => li.textContent)).toEqual(['10월 3일3.1 kg', '11월 1일3.2 kg'])
  expect(container.querySelector('svg polyline')).not.toBeNull()
  expect(container.textContent).not.toMatch(/늘었|줄었|적정/)
  cleanup()
  const one = render(<WeightChart items={WEIGHTS.slice(0, 1)} />)
  expect(one.container.querySelector('svg')).toBeNull()
})

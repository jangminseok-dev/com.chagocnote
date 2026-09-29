import { render, screen, within } from '@testing-library/react'
import { expect, test } from 'vitest'

import { ReportView } from '../components/ReportView'
import type { Report } from '../lib/report'
import { makeFullReport, makeMedia, makeReport, makeVideo } from './report-fixture'

const TOKEN = 'tokentokentokentokentokentokentokentokentok'

function show(report: Report) {
  const { container } = render(<ReportView report={report} token={TOKEN} />)
  const sections = () => [...container.querySelectorAll('[data-section]')].map((el) => el.getAttribute('data-section'))
  const section = (name: string) => container.querySelector<HTMLElement>(`[data-section="${name}"]`)
  return { container, sections, section }
}

test('모든 항목이 있는 알림장은 구역 열이 순서대로 있다', () => {
  const { sections, section } = show(makeFullReport())

  expect(sections()).toEqual(['head', 'date', 'title', 'hero', 'strip', 'note', 'care', 'save-all', 'shop', 'foot'])
  expect(section('head')).toHaveTextContent('Grooming Note')
  expect(section('head')).toHaveTextContent('Hiss Haus')
  expect(section('date')).toHaveTextContent('28')
  expect(section('date')).toHaveTextContent('September')
  expect(section('date')).toHaveTextContent('Monday')
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('두부의 미용 알림장')
  expect(section('note')).toHaveTextContent('Care note')
  expect(section('note')).toHaveTextContent('매장에서 남긴 말')
  expect(screen.getByRole('button', { name: '사진 · 영상 모두 저장' })).toBeInTheDocument()
  expect(section('foot')).toHaveTextContent('이 알림장은 10월 28일까지 열려요')
  expect(section('foot')).toHaveTextContent('차곡노트')
})

test('오늘의 케어에 메뉴와 금액, 합계, 몸무게가 있다', () => {
  const { section } = show(makeFullReport())

  const rows = [...section('care')!.querySelectorAll('li')].map((li) => li.textContent)
  expect(rows).toEqual(['전체 미용55,000', '스파15,000', '합계70,000', '몸무게4.2 kg'])
  expect(section('care')).toHaveTextContent("Today's care")
  expect(section('care')).toHaveTextContent('오늘의 케어')
})

test('매장 구역에 이름·전화·주소와 전화 링크가 있다', () => {
  const { section } = show(makeFullReport())

  const shop = within(section('shop')!)
  expect(shop.getByText('Hiss Haus')).toBeInTheDocument()
  expect(shop.getByText('02-123-4567')).toBeInTheDocument()
  expect(shop.getByText('서울 마포구 ○○로 12, 1층')).toBeInTheDocument()
  expect(shop.getByRole('link', { name: '매장에 전화하기' })).toHaveAttribute('href', 'tel:02-123-4567')
})

test('끈 항목의 구역은 없다', () => {
  const { sections, section, container } = show(makeReport())

  expect(sections()).toEqual(['head', 'date', 'title', 'hero', 'strip', 'note', 'save-all', 'foot'])
  expect(section('head')!.textContent).toBe('Grooming Note')
  expect(container).not.toHaveTextContent('오늘의 케어')
  expect(container).not.toHaveTextContent('Shop')
  expect(container.querySelector('a[href^="tel:"]')).toBeNull()
})

test('메뉴만 켜면 이름만 있고 금액과 합계가 없다', () => {
  const { section } = show(makeReport({ menus: [{ name: '전체 미용' }, { name: '스파' }] }))

  const rows = [...section('care')!.querySelectorAll('li')].map((li) => li.textContent)
  expect(rows).toEqual(['전체 미용', '스파'])
})

test('금액만 켜면 합계만 있다', () => {
  const { section } = show(makeReport({ total_amount: 70000 }))

  const rows = [...section('care')!.querySelectorAll('li')].map((li) => li.textContent)
  expect(rows).toEqual(['합계70,000'])
})

test('켰지만 값이 없는 줄과 전화 버튼은 없고 null 글자가 보이지 않는다', () => {
  const { sections, section, container } = show(
    makeReport({
      menus: [{ name: '전체 미용', amount: null }],
      total_amount: null,
      weight_kg: null,
      shop: { name: 'Hiss Haus', phone: null, address: null },
    }),
  )

  const rows = [...section('care')!.querySelectorAll('li')].map((li) => li.textContent)
  expect(rows).toEqual(['전체 미용'])
  expect(section('shop')!.textContent).toBe('ShopHiss Haus')
  expect(container.querySelector('a')).toBeNull()
  expect(container).not.toHaveTextContent('null')
  expect(container).not.toHaveTextContent('undefined')
  expect(sections()).toContain('shop')
})

test('켠 항목이 모두 null 이면 오늘의 케어와 매장 구역이 없다', () => {
  const { sections } = show(makeReport({ menus: null, total_amount: null, weight_kg: null, shop: null }))

  expect(sections()).toEqual(['head', 'date', 'title', 'hero', 'strip', 'note', 'save-all', 'foot'])
})

test('메뉴가 빈 목록이고 다른 줄도 없으면 오늘의 케어 구역이 없다', () => {
  const { sections } = show(makeReport({ menus: [] }))

  expect(sections()).not.toContain('care')
})

test('미디어도 메모도 없으면 머리와 날짜, 제목, 꼬리만 있다', () => {
  const { sections, container } = show(makeReport({ media: [], cover: null, care_note: null }))

  expect(sections()).toEqual(['head', 'date', 'title', 'foot'])
  expect(container.querySelector('button')).toBeNull()
  expect(container.querySelector('img')).toBeNull()
})

test('보호자만의 방문이면 제목이 미용 알림장이다', () => {
  show(makeReport({ pet_name: null }))

  expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('미용 알림장')
})

test('대표는 첫 미디어의 표시용 사진이고 꼬리표와 순번, 저장 버튼이 있다', () => {
  const first = makeMedia({ display_url: 'https://media.test/first-display.jpg', width: 1200, height: 900 })
  const { section } = show(makeReport({ media: [first, makeMedia({ phase: 'before' })] }))

  const hero = section('hero')!
  const img = hero.querySelector('img')!
  expect(img).toHaveAttribute('src', 'https://media.test/first-display.jpg')
  expect(img).toHaveAttribute('width', '1200')
  expect(img).toHaveAttribute('height', '900')
  expect(img).toHaveAttribute('alt', '미용 후 사진')
  expect(hero).toHaveTextContent('미용 후')
  expect(hero).toHaveTextContent('1 / 2')
  expect(within(hero).getByRole('button', { name: '저장' })).toBeInTheDocument()
  expect(hero.querySelector('[data-play]')).toBeNull()
})

test('미용 전 사진뿐이면 꼬리표가 미용 전이다', () => {
  const { section } = show(makeReport({ media: [makeMedia({ phase: 'before' })] }))

  expect(section('hero')).toHaveTextContent('미용 전')
  expect(section('hero')).not.toHaveTextContent('미용 후')
})

test('미디어가 하나뿐이면 미디어 줄이 없다', () => {
  const { sections, section } = show(makeReport({ media: [makeMedia()] }))

  expect(sections()).not.toContain('strip')
  expect(section('hero')).toHaveTextContent('1 / 1')
  expect(sections()).toContain('save-all')
})

test('미디어 줄에는 머리말과 썸네일이 있고 영상에는 재생 표시와 길이가 있다', () => {
  const { section } = show(makeReport())

  const strip = section('strip')!
  expect(strip).toHaveTextContent('사진 · 영상 5')
  expect(strip).toHaveTextContent('눌러서 크게 보기')
  const items = [...strip.querySelectorAll('li')]
  expect(items).toHaveLength(5)
  expect(items.map((li) => li.querySelector('img')!.getAttribute('src'))).toEqual([
    'https://media.test/thumb.jpg',
    'https://media.test/thumb.jpg',
    'https://media.test/poster.jpg',
    'https://media.test/thumb.jpg',
    'https://media.test/thumb.jpg',
  ])
  expect(items.map((li) => li.querySelector('[data-play]') !== null)).toEqual([false, false, true, false, false])
  expect(items[2]).toHaveTextContent('0:18')
  expect(within(strip).getAllByRole('button')).toHaveLength(5)
  expect(within(strip).getByRole('button', { name: '3번째 미용 후 영상 크게 보기' })).toBeInTheDocument()
})

test('영상만 있는 알림장은 대표가 포스터이고 재생 표시가 있다', () => {
  const { section, container } = show(makeReport({ media: [makeVideo()], cover: null }))

  const hero = section('hero')!
  expect(hero.querySelector('img')).toHaveAttribute('src', 'https://media.test/poster.jpg')
  expect(hero.querySelector('img')).toHaveAttribute('alt', '미용 후 영상')
  expect(hero.querySelector('[data-play]')).not.toBeNull()
  expect(container.querySelector('video')).toBeNull()
})

test('미디어가 33개면 순번은 1 / 33 이고 썸네일이 33개다', () => {
  const media = Array.from({ length: 33 }, () => makeMedia())
  const { section } = show(makeReport({ media }))

  expect(section('hero')).toHaveTextContent('1 / 33')
  expect(section('strip')).toHaveTextContent('사진 · 영상 33')
  expect(section('strip')!.querySelectorAll('li img')).toHaveLength(33)
})

test('케어 메모의 꺾쇠와 줄바꿈은 글자 그대로 보인다', () => {
  const note = '첫 줄 <script>alert(1)</script>\n둘째 줄 <b>굵게</b>'
  const { section } = show(makeReport({ care_note: note }))

  const memo = section('note')!.querySelector('p')!
  expect(memo.textContent).toBe(note)
  expect(memo.children).toHaveLength(0)
  expect(section('note')!.querySelector('script')).toBeNull()
  expect(section('note')!.querySelector('b')).toBeNull()
})

test('무기한 알림장의 꼬리에는 기간 문구가 없다', () => {
  const { section } = show(makeReport({ expires_at: null }))

  expect(section('foot')!.textContent).toBe('차곡노트')
})

test('화면 어디에도 토큰이 없다', () => {
  const { container } = show(makeFullReport())

  expect(container.innerHTML).not.toContain(TOKEN)
})

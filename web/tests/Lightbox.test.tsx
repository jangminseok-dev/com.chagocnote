import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { Lightbox } from '../components/Lightbox'
import { makeMedia, makeVideo } from './report-fixture'

// 확대(⑫ 설계 3.2) — 사진만, 두 번 누르기 1↔2.5배, 두 손가락 벌리기 4배까지, 넘기기는 1배일 때만.
beforeEach(() => {
  vi.spyOn(window.history, 'pushState').mockImplementation(() => {})
  vi.spyOn(window.history, 'back').mockImplementation(() => {})
  vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {})
})
afterEach(() => vi.restoreAllMocks())

const media = [makeMedia(), makeMedia({ display_url: 'https://media.test/2.jpg' }), makeVideo()]

function open(start = 0) {
  render(<Lightbox media={media} start={start} onClose={() => {}} />)
  const dialog = within(screen.getByRole('dialog'))
  const stage = document.querySelector<HTMLElement>('[data-stage]')!
  const scale = () => Number(stage.getAttribute('data-scale'))
  return { dialog, stage, scale }
}

const touch = (x: number, y: number) => ({ clientX: x, clientY: y })

test('사진을 두 번 누르면 2.5배로 커지고 다시 두 번 누르면 돌아온다', () => {
  const { stage, scale } = open()

  fireEvent.doubleClick(stage.querySelector('img')!)
  expect(scale()).toBe(2.5)
  expect(stage.querySelector('img')!.style.transform).toContain('scale(2.5)')
  fireEvent.doubleClick(stage.querySelector('img')!)
  expect(scale()).toBe(1)
})

test('확대한 동안에는 손가락으로 밀어도 넘어가지 않고, 1배면 넘어간다', () => {
  const { dialog, stage } = open()
  fireEvent.doubleClick(stage.querySelector('img')!)

  fireEvent.touchStart(stage, { touches: [touch(200, 100)], changedTouches: [touch(200, 100)] })
  fireEvent.touchMove(stage, { touches: [touch(80, 100)], changedTouches: [touch(80, 100)] })
  fireEvent.touchEnd(stage, { touches: [], changedTouches: [touch(80, 100)] })
  expect(dialog.getByText('1 / 3')).toBeInTheDocument()

  fireEvent.doubleClick(stage.querySelector('img')!)
  fireEvent.touchStart(stage, { touches: [touch(200, 100)], changedTouches: [touch(200, 100)] })
  fireEvent.touchEnd(stage, { touches: [], changedTouches: [touch(80, 100)] })
  expect(dialog.getByText('2 / 3')).toBeInTheDocument()
})

test('두 손가락으로 벌리면 커지되 4배를 넘지 않는다', () => {
  const { stage, scale } = open()

  fireEvent.touchStart(stage, { touches: [touch(100, 100), touch(120, 100)], changedTouches: [touch(120, 100)] })
  fireEvent.touchMove(stage, { touches: [touch(60, 100), touch(160, 100)], changedTouches: [touch(160, 100)] })
  expect(scale()).toBe(4)
  fireEvent.touchEnd(stage, { touches: [], changedTouches: [touch(160, 100)] })
  expect(screen.getByText('1 / 3')).toBeInTheDocument()           // 벌리기는 넘기기가 아니다
})

test('넘기면 1배로 돌아오고 영상은 확대하지 않는다', () => {
  const { dialog, stage, scale } = open(1)
  fireEvent.doubleClick(stage.querySelector('img')!)
  expect(scale()).toBe(2.5)

  fireEvent.click(dialog.getByRole('button', { name: '다음' }))
  expect(scale()).toBe(1)
  fireEvent.doubleClick(stage.querySelector('video')!)
  expect(scale()).toBe(1)
})

test('아래에 덧붙일 줄을 받는다 — 지금 보는 미디어로 만든다', () => {
  render(<Lightbox media={media} start={1} onClose={() => {}} footer={(index) => <a href={`/r${index}`}>알림장 보기</a>} />)

  expect(screen.getByRole('link', { name: '알림장 보기' })).toHaveAttribute('href', '/r1')
})

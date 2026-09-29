import { fireEvent, render, screen, within } from '@testing-library/react'
import { StrictMode } from 'react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { MediaGallery } from '../components/MediaGallery'
import { makeMedia, makeReport, makeVideo } from './report-fixture'

// jsdom 은 영상의 pause 를 구현하지 않는다.
let pause: ReturnType<typeof vi.spyOn>
// 방문 기록은 세기만 한다 — jsdom 의 history.back 은 뒤늦게 popstate 를 보내 다음 테스트의 크게 보기를 닫을 수 있다.
let pushState: ReturnType<typeof vi.spyOn>
let back: ReturnType<typeof vi.spyOn>

beforeEach(() => {
  pause = vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {})
  pushState = vi.spyOn(window.history, 'pushState').mockImplementation(() => {})
  back = vi.spyOn(window.history, 'back').mockImplementation(() => {})
})

afterEach(() => {
  vi.restoreAllMocks()
})

const media = makeReport().media // 후 사진 2 · 후 영상 1 · 전 사진 2

function openAt(name: string) {
  render(<MediaGallery media={media} />)
  fireEvent.click(screen.getByRole('button', { name }))
  return within(screen.getByRole('dialog'))
}

test('누르기 전에는 크게 보기가 없다', () => {
  render(<MediaGallery media={media} />)

  expect(screen.queryByRole('dialog')).toBeNull()
})

test('썸네일 셋째를 누르면 3 / 5 로 열리고 영상이 그 자리에서 재생된다', () => {
  const dialog = openAt('3번째 미용 후 영상 크게 보기')

  expect(dialog.getByText('3 / 5')).toBeInTheDocument()
  const video = screen.getByRole('dialog').querySelector('video')!
  expect(video).toHaveAttribute('src', 'https://media.test/video.mp4')
  expect(video).toHaveAttribute('poster', 'https://media.test/poster.jpg')
  expect(video).toHaveAttribute('controls')
  expect(video).toHaveAttribute('playsinline')
})

test('대표를 누르면 1 / 5 로 열리고 표시용 사진이 보인다', () => {
  const dialog = openAt('미용 후 사진 크게 보기')

  expect(dialog.getByText('1 / 5')).toBeInTheDocument()
  expect(dialog.getByRole('img', { name: '미용 후 사진' })).toHaveAttribute('src', 'https://media.test/display.jpg')
})

test('다음과 이전으로 넘긴다', () => {
  const dialog = openAt('3번째 미용 후 영상 크게 보기')

  fireEvent.click(dialog.getByRole('button', { name: '다음' }))
  expect(dialog.getByText('4 / 5')).toBeInTheDocument()
  expect(dialog.getByRole('img', { name: '미용 전 사진' })).toBeInTheDocument()

  fireEvent.click(dialog.getByRole('button', { name: '이전' }))
  fireEvent.click(dialog.getByRole('button', { name: '이전' }))
  expect(dialog.getByText('2 / 5')).toBeInTheDocument()
})

test('화살표 키로 넘긴다', () => {
  const dialog = openAt('3번째 미용 후 영상 크게 보기')

  fireEvent.keyDown(document, { key: 'ArrowRight' })
  expect(dialog.getByText('4 / 5')).toBeInTheDocument()

  fireEvent.keyDown(document, { key: 'ArrowLeft' })
  fireEvent.keyDown(document, { key: 'ArrowLeft' })
  expect(dialog.getByText('2 / 5')).toBeInTheDocument()
})

test('손가락으로 왼쪽으로 밀면 다음, 오른쪽으로 밀면 이전이다', () => {
  const dialog = openAt('2번째 미용 후 사진 크게 보기')
  const stage = screen.getByRole('dialog').querySelector('[data-stage]')!

  fireEvent.touchStart(stage, { changedTouches: [{ clientX: 300, clientY: 400 }] })
  fireEvent.touchEnd(stage, { changedTouches: [{ clientX: 100, clientY: 410 }] })
  expect(dialog.getByText('3 / 5')).toBeInTheDocument()

  fireEvent.touchStart(stage, { changedTouches: [{ clientX: 100, clientY: 400 }] })
  fireEvent.touchEnd(stage, { changedTouches: [{ clientX: 300, clientY: 410 }] })
  expect(dialog.getByText('2 / 5')).toBeInTheDocument()
})

test('위아래로 밀거나 조금만 밀면 넘어가지 않는다', () => {
  const dialog = openAt('2번째 미용 후 사진 크게 보기')
  const stage = screen.getByRole('dialog').querySelector('[data-stage]')!

  fireEvent.touchStart(stage, { changedTouches: [{ clientX: 200, clientY: 100 }] })
  fireEvent.touchEnd(stage, { changedTouches: [{ clientX: 140, clientY: 400 }] })
  fireEvent.touchStart(stage, { changedTouches: [{ clientX: 200, clientY: 100 }] })
  fireEvent.touchEnd(stage, { changedTouches: [{ clientX: 180, clientY: 100 }] })

  expect(dialog.getByText('2 / 5')).toBeInTheDocument()
})

test('처음에서 이전, 끝에서 다음은 눌리지 않는다', () => {
  const dialog = openAt('미용 후 사진 크게 보기')

  expect(dialog.getByRole('button', { name: '이전' })).toBeDisabled()
  fireEvent.keyDown(document, { key: 'ArrowLeft' })
  expect(dialog.getByText('1 / 5')).toBeInTheDocument()

  for (let i = 0; i < 4; i += 1) fireEvent.click(dialog.getByRole('button', { name: '다음' }))
  expect(dialog.getByText('5 / 5')).toBeInTheDocument()
  expect(dialog.getByRole('button', { name: '다음' })).toBeDisabled()
  fireEvent.keyDown(document, { key: 'ArrowRight' })
  expect(dialog.getByText('5 / 5')).toBeInTheDocument()
})

test('Esc 로 닫힌다', () => {
  openAt('3번째 미용 후 영상 크게 보기')

  fireEvent.keyDown(document, { key: 'Escape' })

  expect(screen.queryByRole('dialog')).toBeNull()
})

test('닫기 버튼으로 닫힌다', () => {
  const dialog = openAt('3번째 미용 후 영상 크게 보기')

  fireEvent.click(dialog.getByRole('button', { name: '닫기' }))

  expect(screen.queryByRole('dialog')).toBeNull()
})

test('크게 보기를 열면 방문 기록에 한 칸을 쌓되 주소는 바꾸지 않는다', () => {
  openAt('3번째 미용 후 영상 크게 보기')

  expect(pushState).toHaveBeenCalledTimes(1)
  // URL 인자가 없다 — 토큰이 든 주소를 더 만들지 않는다.
  expect(pushState.mock.calls[0]).toHaveLength(2)
})

test('개발 모드(StrictMode)에서도 칸은 한 번만 쌓는다', () => {
  render(
    <StrictMode>
      <MediaGallery media={media} />
    </StrictMode>,
  )
  fireEvent.click(screen.getByRole('button', { name: '미용 후 사진 크게 보기' }))

  expect(pushState).toHaveBeenCalledTimes(1)
})

test('뒤로 가기(popstate)가 오면 크게 보기가 닫히고 history.back 은 부르지 않는다', () => {
  openAt('3번째 미용 후 영상 크게 보기')

  fireEvent.popState(window)

  expect(screen.queryByRole('dialog')).toBeNull()
  expect(back).not.toHaveBeenCalled()
})

test.each([
  ['닫기 버튼으로', () => fireEvent.click(screen.getByRole('button', { name: '닫기' }))],
  ['Esc 로', () => fireEvent.keyDown(document, { key: 'Escape' })],
])('%s 닫으면 쌓은 칸을 history.back 으로 한 번 치운다', (_, close) => {
  openAt('3번째 미용 후 영상 크게 보기')

  close()

  expect(screen.queryByRole('dialog')).toBeNull()
  expect(back).toHaveBeenCalledTimes(1)
})

test('넘겨도 칸을 더 쌓지 않는다', () => {
  const dialog = openAt('미용 후 사진 크게 보기')

  fireEvent.click(dialog.getByRole('button', { name: '다음' }))
  fireEvent.keyDown(document, { key: 'ArrowRight' })

  expect(dialog.getByText('3 / 5')).toBeInTheDocument()
  expect(pushState).toHaveBeenCalledTimes(1)
})

test('영상에서 넘기면 pause 가 불린다', () => {
  const dialog = openAt('3번째 미용 후 영상 크게 보기')
  expect(pause).not.toHaveBeenCalled()

  fireEvent.click(dialog.getByRole('button', { name: '다음' }))

  expect(pause).toHaveBeenCalledTimes(1)
})

test('열려 있는 동안 뒤 화면이 스크롤되지 않고 닫으면 돌아온다', () => {
  openAt('미용 후 사진 크게 보기')
  expect(document.body.style.overflow).toBe('hidden')

  fireEvent.keyDown(document, { key: 'Escape' })

  expect(document.body.style.overflow).toBe('')
})

test('하나 저장의 href 가 download_url 이고 새 창을 열지 않는다', () => {
  const first = makeMedia({ download_url: 'https://media.test/first-download.jpg' })
  const video = makeVideo({ download_url: 'https://media.test/second-download.mp4' })
  render(<MediaGallery media={[first, video]} />)

  const save = screen.getByRole('link', { name: '저장' })
  expect(save).toHaveAttribute('href', 'https://media.test/first-download.jpg')
  expect(save).not.toHaveAttribute('target')

  fireEvent.click(screen.getByRole('button', { name: '2번째 미용 후 영상 크게 보기' }))
  const inDialog = within(screen.getByRole('dialog')).getByRole('link', { name: '저장' })
  expect(inDialog).toHaveAttribute('href', 'https://media.test/second-download.mp4')
  expect(inDialog).not.toHaveAttribute('target')
})

test('대표 칸은 미디어의 비율을 따르되 세로가 가로의 4/3배를 넘지 않는다 — 3:4 사진은 잘리지 않는다', () => {
  const ratioOf = (width: number, height: number) => {
    const { container, unmount } = render(<MediaGallery media={[makeMedia({ width, height })]} />)
    const ratio = container.querySelector<HTMLElement>('[data-section="hero"] img')!.style.aspectRatio
    unmount()
    return ratio
  }

  expect(ratioOf(1200, 900)).toBe('1200 / 900')
  expect(ratioOf(1200, 1600)).toBe('1200 / 1600')
  expect(ratioOf(1080, 1920)).toBe('1080 / 1440')
})

test('미디어가 하나뿐이면 미디어 줄이 없고 대표로 크게 본다', () => {
  const { container } = render(<MediaGallery media={[makeMedia()]} />)

  expect(container.querySelector('[data-section="strip"]')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '미용 후 사진 크게 보기' }))
  expect(within(screen.getByRole('dialog')).getByText('1 / 1')).toBeInTheDocument()
})

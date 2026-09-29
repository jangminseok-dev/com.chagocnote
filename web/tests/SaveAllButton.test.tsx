import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { SaveAllButton } from '../components/SaveAllButton'
import { makeMedia, makeVideo } from './report-fixture'

const media = [
  makeMedia({ download_url: 'https://media.test/a.jpg?sig=1' }),
  makeVideo({ download_url: 'https://media.test/b.mp4?sig=2' }),
  makeMedia({ download_url: 'https://media.test/c.jpg?sig=3' }),
]
const URLS = media.map((item) => item.download_url)

let clicked: string[]

beforeEach(() => {
  vi.useFakeTimers()
  clicked = []
  // 숨은 링크를 누르는 것을 가로챈다 — jsdom 은 이동하지 않는다.
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
    clicked.push(this.href)
  })
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

function stubNavigator(extra: object, userAgent = 'Mozilla/5.0 (iPhone) Safari/604.1') {
  vi.stubGlobal('navigator', { userAgent, ...extra })
}

function stubFetch(headers: Record<string, string> = {}) {
  const fetchMock = vi.fn(async () => new Response('file', { headers: { 'Content-Type': 'image/jpeg', ...headers } }))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function pressAndFinish() {
  fireEvent.click(screen.getByRole('button', { name: '사진 · 영상 모두 저장' }))
  await act(() => vi.runAllTimersAsync())
}

test('공유할 수 있으면 내려받기용 주소를 받아 파일 수만큼 든 목록으로 한 번 공유한다', async () => {
  const share = vi.fn(async (_data: { files: File[] }) => {})
  stubNavigator({ canShare: () => true, share })
  const fetchMock = stubFetch()
  render(<SaveAllButton media={media} />)

  await pressAndFinish()

  expect(fetchMock.mock.calls.map((call) => (call as unknown[])[0])).toEqual(URLS)
  expect(share).toHaveBeenCalledTimes(1)
  const { files } = share.mock.calls[0][0]
  expect(files.map((file) => file.name)).toEqual(['chagocnote-1.jpg', 'chagocnote-2.mp4', 'chagocnote-3.jpg'])
  expect(files.every((file) => file instanceof File)).toBe(true)
  expect(clicked).toEqual([])
  expect(screen.getByRole('button', { name: '사진 · 영상 모두 저장' })).toBeEnabled()
})

test('응답의 Content-Disposition 을 읽을 수 있으면 그 이름을 쓴다', async () => {
  const share = vi.fn(async (_data: { files: File[] }) => {})
  stubNavigator({ canShare: () => true, share })
  stubFetch({ 'Content-Disposition': 'attachment; filename="chagocnote-812.jpg"' })
  render(<SaveAllButton media={[media[0]]} />)

  await pressAndFinish()

  expect(share.mock.calls[0][0].files.map((file) => file.name)).toEqual(['chagocnote-812.jpg'])
})

test('canShare 가 없으면 받지 않고 차례로 내려받는다', async () => {
  stubNavigator({})
  const fetchMock = stubFetch()
  render(<SaveAllButton media={media} />)

  await pressAndFinish()

  expect(fetchMock).not.toHaveBeenCalled()
  expect(clicked).toEqual(URLS)
  expect(document.querySelectorAll('a')).toHaveLength(0)
})

test('파일 공유를 못 하는 브라우저면 받지 않고 차례로 내려받는다', async () => {
  const share = vi.fn()
  stubNavigator({ canShare: () => false, share })
  const fetchMock = stubFetch()
  render(<SaveAllButton media={media} />)

  await pressAndFinish()

  expect(fetchMock).not.toHaveBeenCalled()
  expect(share).not.toHaveBeenCalled()
  expect(clicked).toEqual(URLS)
})

test('차례로 내려받을 때 사이에 간격을 둔다', async () => {
  stubNavigator({})
  render(<SaveAllButton media={media} />)

  fireEvent.click(screen.getByRole('button', { name: '사진 · 영상 모두 저장' }))
  await act(() => vi.advanceTimersByTimeAsync(0))
  expect(clicked).toEqual(URLS.slice(0, 1))

  await act(() => vi.advanceTimersByTimeAsync(700))
  expect(clicked).toEqual(URLS.slice(0, 2))

  await act(() => vi.runAllTimersAsync())
  expect(clicked).toEqual(URLS)
})

test('fetch 가 실패하면 차례로 내려받기로 넘어간다', async () => {
  const share = vi.fn()
  stubNavigator({ canShare: () => true, share })
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
  render(<SaveAllButton media={media} />)

  await pressAndFinish()

  expect(share).not.toHaveBeenCalled()
  expect(clicked).toEqual(URLS)
})

test('받은 응답이 200 대가 아니면 차례로 내려받기로 넘어간다', async () => {
  const share = vi.fn()
  stubNavigator({ canShare: () => true, share })
  vi.stubGlobal('fetch', vi.fn(async () => new Response('', { status: 403 })))
  render(<SaveAllButton media={media} />)

  await pressAndFinish()

  expect(share).not.toHaveBeenCalled()
  expect(clicked).toEqual(URLS)
})

test('공유가 실패하면 차례로 내려받기로 넘어간다', async () => {
  const share = vi.fn().mockRejectedValue(new DOMException('not allowed', 'NotAllowedError'))
  stubNavigator({ canShare: () => true, share })
  stubFetch()
  render(<SaveAllButton media={media} />)

  await pressAndFinish()

  expect(share).toHaveBeenCalledTimes(1)
  expect(clicked).toEqual(URLS)
})

test('사용자가 공유를 취소하면 내려받기로 넘어가지 않는다', async () => {
  const share = vi.fn().mockRejectedValue(new DOMException('취소', 'AbortError'))
  stubNavigator({ canShare: () => true, share })
  stubFetch()
  render(<SaveAllButton media={media} />)

  await pressAndFinish()

  expect(share).toHaveBeenCalledTimes(1)
  expect(clicked).toEqual([])
  expect(screen.getByRole('button', { name: '사진 · 영상 모두 저장' })).toBeEnabled()
})

test('진행 중에는 버튼이 저장하는 중이고 다시 눌리지 않는다', async () => {
  const share = vi.fn(async (_data: { files: File[] }) => {})
  stubNavigator({ canShare: () => true, share })
  let finish = (_response: Response) => {}
  const fetchMock = vi.fn(() => new Promise<Response>((resolve) => (finish = resolve)))
  vi.stubGlobal('fetch', fetchMock)
  render(<SaveAllButton media={[media[0]]} />)

  fireEvent.click(screen.getByRole('button', { name: '사진 · 영상 모두 저장' }))
  await act(() => vi.advanceTimersByTimeAsync(0))

  const busy = screen.getByRole('button', { name: '저장하는 중…' })
  expect(busy).toBeDisabled()
  fireEvent.click(busy)
  expect(fetchMock).toHaveBeenCalledTimes(1)

  finish(new Response('file'))
  await act(() => vi.runAllTimersAsync())

  expect(share).toHaveBeenCalledTimes(1)
  expect(screen.getByRole('button', { name: '사진 · 영상 모두 저장' })).toBeEnabled()
})

const NOTICE = '저장이 안 되면 ⋯ → 다른 브라우저로 열기'

test('카카오톡 내장 브라우저면 저장 버튼 아래에 안내가 있다', () => {
  stubNavigator({}, 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Mobile/15E148 KAKAOTALK/25.8.0')
  const { container } = render(<SaveAllButton media={media} />)

  const notice = screen.getByText(NOTICE)
  const button = screen.getByRole('button', { name: '사진 · 영상 모두 저장' })
  expect(button.compareDocumentPosition(notice) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(container.querySelector('[data-section="save-all"]')).toContainElement(notice)
})

test('카카오톡이 아니면 안내가 없다', () => {
  stubNavigator({})
  render(<SaveAllButton media={media} />)

  expect(screen.queryByText(NOTICE)).toBeNull()
})

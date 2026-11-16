import { act, fireEvent, render, screen } from '@testing-library/react'
import { renderToString } from 'react-dom/server'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { ConsentSubmit } from '../components/ConsentSubmit'

const refresh = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh }) }))

// 서명 칸은 따로 본다(SignaturePad.test.tsx). 여기서는 버튼 둘로 갈아 끼운다 — 서명하기와 지우기.
vi.mock('../components/SignaturePad', () => ({
  SignaturePad: ({ onChange, resetKey }: { onChange: (png: string | null) => void; resetKey: number }) => (
    <div data-testid="pad" data-reset={resetKey}>
      <button type="button" onClick={() => onChange('UE5H')}>
        서명하기
      </button>
    </div>
  ),
}))

const TOKEN = 'ok'.padEnd(43, 'A')
const DIGEST = 'd'.repeat(64)
const fetchMock = vi.fn<typeof fetch>()

function respondWith(status: number) {
  fetchMock.mockResolvedValue(new Response(null, { status }))
}

function fill({ name = '김민지', sign = true, agree = true } = {}) {
  if (name) fireEvent.change(screen.getByLabelText('이름'), { target: { value: name } })
  if (sign) fireEvent.click(screen.getByText('서명하기'))
  if (agree) fireEvent.click(screen.getByLabelText('위 내용을 읽었고 동의해요'))
}

async function send() {
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: /동의하고 보내기|보내는 중/ }))
  })
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
  refresh.mockReset()
})

test('글자를 치는 칸은 이름 하나뿐이다', () => {
  const { container } = render(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />)

  expect(container.querySelectorAll('input[type="text"], textarea')).toHaveLength(1)
  expect(screen.getByLabelText('이름')).toHaveAttribute('maxlength', '50')
})

test.each([
  [{ name: '' }, '이름을 적어 주세요'],
  [{ name: '   ' }, '이름을 적어 주세요'],
  [{ sign: false }, '서명해 주세요'],
  [{ agree: false }, '동의에 체크해 주세요'],
])('빠진 것이 있으면(%o) 보내지 않고 말한다', async (missing, message) => {
  render(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />)
  fill(missing)

  await send()

  expect(screen.getByRole('alert')).toHaveTextContent(message)
  expect(fetchMock).not.toHaveBeenCalled()
})

test('이름·서명·지문을 웹의 제출 경로로 보낸다', async () => {
  respondWith(204)
  render(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />)
  fill({ name: '  김민지 ' })

  await send()

  expect(fetchMock).toHaveBeenCalledTimes(1)
  const [url, init] = fetchMock.mock.calls[0]
  expect(url).toBe(`/f/${TOKEN}/submit`)
  expect(init?.method).toBe('POST')
  expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json')
  expect(JSON.parse(String(init?.body))).toEqual({ doc_digest: DIGEST, signer_name: '김민지', signature_png: 'UE5H' })
})

test.each([204, 410])('상태 코드 %i 는 다시 읽기를 기다리지 않고 곧바로 보냈어요를 보인다', async (status) => {
  respondWith(status)
  const { container } = render(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />)
  fill()

  await send()

  // 느린 망에서 "안 눌렸다"로 보이지 않게 — 화면을 다시 읽는 동안에도 보냈다는 것이 보인다.
  const status_ = screen.getByRole('status')
  expect(status_).toHaveTextContent('보냈어요. Hiss Haus에서 확인할게요.')
  expect(status_).toHaveFocus()
  expect(container.querySelector('input')).toBeNull()
  expect(screen.queryByRole('button')).toBeNull()
  expect(refresh).toHaveBeenCalledTimes(1)
})

test('없는 서류(404)는 화면을 다시 읽는다', async () => {
  respondWith(404)
  render(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />)
  fill()

  await send()

  expect(refresh).toHaveBeenCalledTimes(1)
  expect(screen.queryByRole('status')).toBeNull()
})

test('서버가 그린 첫 화면의 버튼은 잠겨 있다 — 스크립트가 오기 전에는 낼 수 없다', () => {
  // 스크립트가 없거나 아직 오지 않았을 때 누르면 브라우저가 폼을 그대로 내, 적은 이름이 주소에 실린다.
  const html = renderToString(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />)

  expect(html).toMatch(/<button[^>]*disabled/)
  expect(html).toMatch(/<form[^>]*method="post"/)
})

test('스크립트가 온 뒤에는 버튼이 열린다', () => {
  render(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />)

  expect(screen.getByRole('button', { name: '동의하고 보내기' })).toBeEnabled()
})

test('스크립트가 오기 전에 친 이름도 보낸다', async () => {
  respondWith(204)
  // 서버가 그린 화면에 보호자가 먼저 이름을 친다 — 그 뒤에 스크립트가 온다(하이드레이션).
  const container = document.createElement('div')
  document.body.appendChild(container)
  container.innerHTML = renderToString(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />)
  ;(container.querySelector('input[name="signer_name"]') as HTMLInputElement).value = '김민지'
  render(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />, { container, hydrate: true })
  fill({ name: '' })

  await send()

  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body)).signer_name).toBe('김민지')
  container.remove()
})

test('빠진 것을 채우면 안내가 사라진다', async () => {
  render(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />)
  await send()
  expect(screen.getByRole('alert')).toHaveTextContent('이름을 적어 주세요')

  fireEvent.change(screen.getByLabelText('이름'), { target: { value: '김' } })

  expect(screen.queryByRole('alert')).toBeNull()
})

test('내용이 바뀌었으면 알리고 다시 읽고, 이름은 남기고 서명은 비운다', async () => {
  respondWith(409)
  render(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />)
  fill()

  await send()

  expect(screen.getByRole('alert')).toHaveTextContent('내용이 바뀌었어요. 다시 읽어 주세요')
  expect(refresh).toHaveBeenCalledTimes(1)
  expect(screen.getByLabelText('이름')).toHaveValue('김민지')
  expect(screen.getByTestId('pad').dataset.reset).toBe('1')
  expect(screen.getByLabelText('위 내용을 읽었고 동의해요')).not.toBeChecked()

  // 서명을 다시 하지 않고 보내면 보내지 않는다.
  fetchMock.mockClear()
  await send()
  expect(fetchMock).not.toHaveBeenCalled()
})

test.each([
  [413, '서명을 조금 간단하게 다시 적어 주세요'],
  [422, '서명을 조금 간단하게 다시 적어 주세요'],
  [429, '잠시 후 다시 보내 주세요'],
  [503, '잠시 후 다시 보내 주세요'],
])('상태 코드 %i 는 그 자리에서 알린다', async (status, message) => {
  respondWith(status)
  render(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />)
  fill()

  await send()

  expect(screen.getByRole('alert')).toHaveTextContent(message)
  expect(refresh).not.toHaveBeenCalled()
})

test('연결이 끊겨도 잠시 후 다시 보내라고 알린다', async () => {
  fetchMock.mockRejectedValue(new TypeError('fetch failed'))
  render(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />)
  fill()

  await send()

  expect(screen.getByRole('alert')).toHaveTextContent('잠시 후 다시 보내 주세요')
})

test('보내는 동안 버튼은 잠기고 두 번 보내지 않는다', async () => {
  let finish: (response: Response) => void = () => {}
  fetchMock.mockReturnValue(new Promise((resolve) => (finish = resolve)))
  render(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />)
  fill()

  await send()
  const button = screen.getByRole('button', { name: '보내는 중…' })
  expect(button).toBeDisabled()
  fireEvent.click(button)
  expect(fetchMock).toHaveBeenCalledTimes(1)

  await act(async () => finish(new Response(null, { status: 503 })))
  expect(screen.getByRole('button', { name: '동의하고 보내기' })).toBeEnabled()
})

test('스크립트가 꺼져 있을 때의 안내가 있다', () => {
  const { container } = render(<ConsentSubmit token={TOKEN} digest={DIGEST} shopName="Hiss Haus" />)

  expect(container.querySelector('noscript')).not.toBeNull()
})

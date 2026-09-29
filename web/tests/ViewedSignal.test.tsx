import { act, render } from '@testing-library/react'
import { StrictMode } from 'react'
import { afterEach, expect, test, vi } from 'vitest'

import { ErrorScreen } from '../components/ErrorScreen'
import { ReportView } from '../components/ReportView'
import { ViewedSignal } from '../components/ViewedSignal'
import { makeFullReport } from './report-fixture'

const TOKEN = 'tokentokentokentokentokentokentokentokentok'

afterEach(() => {
  vi.unstubAllGlobals()
})

function stubFetch(implementation: () => Promise<Response> = async () => new Response(null, { status: 204 })) {
  const fetchMock = vi.fn(implementation)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

test('마운트되면 열람 신호를 POST 로 한 번 보낸다', async () => {
  const fetchMock = stubFetch()

  const { container, rerender } = render(<ViewedSignal token={TOKEN} />)
  rerender(<ViewedSignal token={TOKEN} />)
  await act(async () => {})

  expect(fetchMock.mock.calls).toEqual([[`/r/${TOKEN}/viewed`, { method: 'POST', keepalive: true }]])
  expect(container.innerHTML).toBe('')
})

test('StrictMode 로 감싸도 한 번만 보낸다', async () => {
  const fetchMock = stubFetch()

  render(
    <StrictMode>
      <ViewedSignal token={TOKEN} />
    </StrictMode>,
  )
  await act(async () => {})

  expect(fetchMock).toHaveBeenCalledTimes(1)
})

test('fetch 가 던져도 화면이 그대로이고 다시 보내지 않는다', async () => {
  stubFetch()
  const sent = render(<ReportView report={makeFullReport()} token={TOKEN} />)
  await act(async () => {})
  const expected = sent.container.innerHTML
  sent.unmount()
  const fetchMock = stubFetch(() => Promise.reject(new TypeError('Failed to fetch')))
  const unhandled = vi.fn()
  process.on('unhandledRejection', unhandled)

  const { container } = render(<ReportView report={makeFullReport()} token={TOKEN} />)
  await act(async () => {})
  await new Promise((resolve) => setTimeout(resolve, 0))
  process.off('unhandledRejection', unhandled)

  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(unhandled).not.toHaveBeenCalled()
  expect(container.innerHTML).toBe(expected)
})

test('응답이 410 이나 429 여도 화면이 그대로이고 다시 보내지 않는다', async () => {
  const fetchMock = stubFetch(async () => new Response(null, { status: 429 }))

  const { container } = render(<ViewedSignal token={TOKEN} />)
  await act(async () => {})

  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(container.innerHTML).toBe('')
})

test('알림장 화면은 열람 신호를 보내고 오류 화면은 보내지 않는다', async () => {
  const fetchMock = stubFetch()

  const error = render(<ErrorScreen kind="closed" />)
  await act(async () => {})
  expect(fetchMock).not.toHaveBeenCalled()
  error.unmount()

  render(<ReportView report={makeFullReport()} token={TOKEN} />)
  await act(async () => {})
  expect(fetchMock.mock.calls).toEqual([[`/r/${TOKEN}/viewed`, { method: 'POST', keepalive: true }]])
})

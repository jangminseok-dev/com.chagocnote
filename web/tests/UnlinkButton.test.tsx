import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { UnlinkButton } from '../components/UnlinkButton'

const QUESTION = 'Hiss Haus의 지난 기록을 더는 볼 수 없어요. 알림장을 다시 받으면 다시 이을 수 있어요. 연결을 끊을까요?'

afterEach(() => {
  vi.restoreAllMocks()
})

/** 제출 이벤트를 보내고 기본 동작(제출)이 막혔는지를 준다. */
function submit(container: HTMLElement): boolean {
  // fireEvent 는 preventDefault 가 불리면 false 를 돌려준다.
  return !fireEvent.submit(container.querySelector('form')!)
}

test('폼은 /me/<연결>/unlink 로 가는 POST 이고 버튼은 "연결 끊기" 다', () => {
  const { container } = render(<UnlinkButton linkId={11} shopName="Hiss Haus" />)

  const form = container.querySelector('form')!
  expect(form.getAttribute('action')).toBe('/me/11/unlink')
  expect(form.getAttribute('method')).toBe('post')
  expect(screen.getByRole('button', { name: '연결 끊기' })).toHaveAttribute('type', 'submit')
})

test('확인을 거절하면 제출되지 않는다', () => {
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
  const { container } = render(<UnlinkButton linkId={11} shopName="Hiss Haus" />)

  expect(submit(container)).toBe(true)
  expect(confirm).toHaveBeenCalledTimes(1)
})

test('확인하면 제출되고 확인 글에 매장 이름이 있다', () => {
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
  const { container } = render(<UnlinkButton linkId={11} shopName="Hiss Haus" />)

  expect(submit(container)).toBe(false)
  expect(confirm).toHaveBeenCalledWith(QUESTION)
})

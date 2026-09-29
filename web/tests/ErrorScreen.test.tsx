import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import { ErrorScreen } from '../components/ErrorScreen'

const CLOSED_TEXT = '기간이 지났거나 매장에서 닫은 알림장이에요. 매장에 다시 요청해 주세요.'

test('없는 알림장은 제목만 있다', () => {
  const { container } = render(<ErrorScreen kind="not_found" />)

  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('알림장을 찾을 수 없어요')
  expect(container.querySelector('p')).toBeNull()
})

test('닫힌 알림장은 제목과 매장에 다시 요청하라는 설명이 있다', () => {
  const { container } = render(<ErrorScreen kind="closed" />)

  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('닫힌 알림장이에요')
  expect(container.querySelector('p')).toHaveTextContent(CLOSED_TEXT)
})

test('횟수 제한에 걸리면 잠시 후 다시 열라는 제목만 있다', () => {
  const { container } = render(<ErrorScreen kind="busy" />)

  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('잠시 후 다시 열어 주세요')
  expect(container.querySelector('p')).toBeNull()
})

test('백엔드에 닿지 못하면 잠시 후 다시 열라는 제목만 있다', () => {
  const { container } = render(<ErrorScreen kind="unavailable" />)

  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('잠시 후 다시 열어 주세요')
  expect(container.querySelector('p')).toBeNull()
})

test('닫힌 화면에 매장 정보와 전화 링크가 없다', () => {
  const { container } = render(<ErrorScreen kind="closed" />)

  expect(container.querySelector('a')).toBeNull()
  expect(container.querySelector('button')).toBeNull()
  expect(container.textContent).toBe(`Closed닫힌 알림장이에요${CLOSED_TEXT}`)
})

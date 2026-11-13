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

test('로그인 수단이 없으면 닫힌 화면에 링크가 없다', () => {
  const { container } = render(<ErrorScreen kind="closed" />)

  expect(container.querySelector('a')).toBeNull()
  expect(container.textContent).toBe(`Closed닫힌 알림장이에요${CLOSED_TEXT}`)
})

test('닫힌 화면에 매장 정보와 전화 링크가 없고 링크는 내 기록으로 가는 하나뿐이다', () => {
  const { container } = render(<ErrorScreen kind="closed" login />)

  expect(container.querySelectorAll('a')).toHaveLength(1)
  expect(container.querySelector('button')).toBeNull()
  expect(container.querySelector('form')).toBeNull()
  expect(container.textContent).toBe(`Closed닫힌 알림장이에요${CLOSED_TEXT}로그인하고 지난 기록 보기`)
})

test('닫힌 화면에 /me 로 가는 링크 "로그인하고 지난 기록 보기" 가 있다', () => {
  render(<ErrorScreen kind="closed" login />)

  expect(screen.getByRole('link', { name: '로그인하고 지난 기록 보기' })).toHaveAttribute('href', '/me')
})

test.each(['not_found', 'busy', 'unavailable', 'forbidden'] as const)('%s 화면에는 그 링크가 없다', (kind) => {
  const { container } = render(<ErrorScreen kind={kind} login />)

  expect(container.querySelector('a')).toBeNull()
})

test('볼 수 없는 계정의 화면은 제목만 있다', () => {
  const { container } = render(<ErrorScreen kind="forbidden" />)

  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('이 계정으로는 볼 수 없어요')
  expect(container.querySelector('p')).toBeNull()
  expect(container.textContent).toBe('Closed이 계정으로는 볼 수 없어요')
})

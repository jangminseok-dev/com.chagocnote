import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import { LoginScreen } from '../components/LoginScreen'

const FAILED = '로그인하지 못했어요. 다시 시도해 주세요.'

test('제목과 설명이 있다', () => {
  render(<LoginScreen dev next="/me" failed={false} />)

  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('로그인')
  expect(screen.getByText('로그인하면 우리 아이의 지난 미용 알림장을 모아 볼 수 있어요.')).toBeInTheDocument()
})

test('개발용 로그인이 켜져 있으면 이름 칸과 /login/dev 로 가는 폼이 있다', () => {
  const { container } = render(<LoginScreen dev next="/me" failed={false} />)

  const form = container.querySelector('form')!
  expect(form.getAttribute('action')).toBe('/login/dev')
  expect(form.getAttribute('method')).toBe('post')
  const name = screen.getByLabelText('개발용 로그인 이름')
  expect(name).toHaveAttribute('name', 'name')
  expect(name).toBeRequired()
  expect(name).toHaveAttribute('maxlength', '50')
  expect(screen.getByRole('button', { name: '로그인' })).toHaveAttribute('type', 'submit')
})

test('꺼져 있으면 폼이 없고 "로그인은 준비 중이에요." 가 보인다', () => {
  const { container } = render(<LoginScreen dev={false} next="/me" failed={false} />)

  expect(container.querySelector('form')).toBeNull()
  expect(screen.getByText('로그인은 준비 중이에요.')).toBeInTheDocument()
})

test('실패했으면 알림으로 실패 문구가 보이고, 아니면 없다', () => {
  const { unmount } = render(<LoginScreen dev next="/me" failed />)
  expect(screen.getByRole('alert')).toHaveTextContent(FAILED)
  unmount()

  render(<LoginScreen dev next="/me" failed={false} />)
  expect(screen.queryByRole('alert')).toBeNull()
})

test('돌아갈 경로가 숨은 칸에 담긴다', () => {
  const { container } = render(<LoginScreen dev next="/me/12?pet=7" failed={false} />)

  const hidden = container.querySelector('input[type="hidden"][name="next"]')
  expect(hidden).toHaveAttribute('value', '/me/12?pet=7')
})

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test } from 'vitest'

import { BackToList, RememberList } from '../components/BackToList'

// 보던 자리(⑫ 설계 3.2) — 목록(지난 알림장·사진)의 주소를 sessionStorage 에 적고, 한 장의 [지난 알림장]이 그리로 간다.
beforeEach(() => sessionStorage.clear())
afterEach(() => cleanup())

function visit(path: string) {
  window.history.replaceState(null, '', path)
}

test('목록을 열면 그 주소(쪽 표시 포함)를 적어 두고, 한 장의 돌아가기가 그 주소의 그 줄로 간다', () => {
  visit('/me/11?pet=7&cursor=c2')
  render(<RememberList linkId={11} />)
  cleanup()

  render(<BackToList linkId={11} reportId={503} />)

  expect(screen.getByRole('link', { name: '지난 알림장' })).toHaveAttribute('href', '/me/11?pet=7&cursor=c2#r503')
})

test('사진 모아 보기에서 왔으면 사진으로 돌아간다', () => {
  visit('/me/11/photos?pet=7&year=2026')
  render(<RememberList linkId={11} />)
  cleanup()

  render(<BackToList linkId={11} reportId={501} />)

  expect(screen.getByRole('link', { name: '사진 모아 보기' })).toHaveAttribute('href', '/me/11/photos?pet=7&year=2026#r501')
})

test('적어 둔 것이 없거나 다른 연결의 목록이면 첫 쪽이다', () => {
  render(<BackToList linkId={11} reportId={501} />)
  expect(screen.getByRole('link', { name: '지난 알림장' })).toHaveAttribute('href', '/me/11')
  cleanup()

  sessionStorage.setItem('cn-list:11', '/me/12?pet=1')        // 다른 연결 — 따라가지 않는다
  render(<BackToList linkId={11} reportId={501} />)
  expect(screen.getByRole('link', { name: '지난 알림장' })).toHaveAttribute('href', '/me/11')
  cleanup()

  sessionStorage.setItem('cn-list:11', 'https://evil.example/me/11')
  render(<BackToList linkId={11} reportId={501} />)
  expect(screen.getByRole('link', { name: '지난 알림장' })).toHaveAttribute('href', '/me/11')
})

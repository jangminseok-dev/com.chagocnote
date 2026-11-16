import { render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import { ConsentView } from '../components/ConsentView'
import { FormSubmitted } from '../components/FormSubmitted'
import type { OpenForm } from '../lib/form'

// 서명 구역은 따로 본다(ConsentSubmit.test.tsx) — 여기서는 자리만 확인한다.
vi.mock('../components/ConsentSubmit', () => ({
  ConsentSubmit: ({ token, digest, shopName }: { token: string; digest: string; shopName: string }) => (
    <div data-testid="submit" data-token={token} data-digest={digest} data-shop={shopName} />
  ),
}))

const TOKEN = 'ok'.padEnd(43, 'A')

function form(over: Partial<OpenForm> = {}): OpenForm {
  return {
    kind: 'consent',
    state: 'open',
    shop: { name: 'Hiss Haus' },
    previous_consent_on: null,
    pets: [{ name: '두부', conditions: ['심장 질환', '피부'], parts: ['basic', 'senior', 'condition'] }],
    texts: {
      basic: { body: '미용 중 작은 상처가 생길 수 있어요.\n많이 힘들어하면 멈출게요.' },
      senior: { body: '나이가 많은 아이는 부담이 될 수 있어요.' },
      condition: { body: '지병 때문에 상태가 나빠질 수 있어요.' },
    },
    doc_digest: 'd'.repeat(64),
    ...over,
  }
}

const section = (container: HTMLElement, name: string) => [...container.querySelectorAll(`[data-section="${name}"]`)]

test('머리에 제목과 매장 이름이 있다', () => {
  const { container } = render(<ConsentView form={form()} token={TOKEN} />)

  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('미용 동의서')
  expect(section(container, 'head')[0]).toHaveTextContent('Hiss Haus')
})

test('토막은 미용 안내·나이가 많은 아이·지병이 있는 아이의 순서다', () => {
  const { container } = render(<ConsentView form={form()} token={TOKEN} />)

  expect(section(container, 'part').map((part) => part.querySelector('h2')?.textContent)).toEqual([
    '미용 안내',
    '나이가 많은 아이',
    '지병이 있는 아이',
  ])
})

test('온 토막만 그린다', () => {
  const only = form({ pets: [{ name: '두부', conditions: [], parts: ['basic'] }], texts: { basic: { body: '안내' } } })
  const { container } = render(<ConsentView form={only} token={TOKEN} />)

  expect(section(container, 'part')).toHaveLength(1)
  expect(container.textContent).not.toContain('알려 주신 지병')
})

test('글의 줄바꿈은 문단이 된다', () => {
  const { container } = render(<ConsentView form={form()} token={TOKEN} />)

  const basic = section(container, 'part')[0]
  expect([...basic.querySelectorAll('p')].map((p) => p.textContent)).toEqual([
    '미용 중 작은 상처가 생길 수 있어요.',
    '많이 힘들어하면 멈출게요.',
  ])
})

test('아이의 이름과 알려 준 지병의 이름이 보인다', () => {
  const { container } = render(<ConsentView form={form()} token={TOKEN} />)

  const pets = section(container, 'pets')[0]
  expect(pets).toHaveTextContent('두부')
  expect(pets).toHaveTextContent('알려 주신 지병: 심장 질환 · 피부')
})

test('가족이 둘이면 토막마다 누구에게 해당하는지 적는다', () => {
  const family = form({
    pets: [
      { name: '콩이', conditions: [], parts: ['basic', 'senior'] },
      { name: '보리', conditions: ['심장 질환'], parts: ['basic', 'condition'] },
    ],
  })
  const { container } = render(<ConsentView form={family} token={TOKEN} />)

  const [basic, senior, condition] = section(container, 'part')
  expect(basic).toHaveTextContent('해당: 콩이 · 보리')
  expect(senior).toHaveTextContent('해당: 콩이')
  expect(senior).not.toHaveTextContent('보리')
  expect(condition).toHaveTextContent('해당: 보리')
})

test('아이가 하나면 해당 줄이 없다', () => {
  const { container } = render(<ConsentView form={form()} token={TOKEN} />)

  expect(container.textContent).not.toContain('해당:')
})

test('바뀐 부분만 받을 때는 지난 동의의 날을 알린다', () => {
  const partial = form({ previous_consent_on: '2026-03-02', pets: [{ name: '두부', conditions: ['피부'], parts: ['condition'] }] })
  const { container, rerender } = render(<ConsentView form={partial} token={TOKEN} />)

  expect(section(container, 'partial')[0]).toHaveTextContent(
    '지난번(2026년 3월 2일)에 동의하신 내용에 더해 바뀐 부분만 확인해 주세요',
  )

  rerender(<ConsentView form={form()} token={TOKEN} />)
  expect(section(container, 'partial')).toHaveLength(0)
})

test('서명 구역에 토큰과 지문을 넘긴다', () => {
  render(<ConsentView form={form()} token={TOKEN} />)

  const submit = screen.getByTestId('submit')
  expect(submit.dataset.token).toBe(TOKEN)
  expect(submit.dataset.digest).toBe('d'.repeat(64))
  expect(submit.dataset.shop).toBe('Hiss Haus')
})

test('화면에 효력을 말하는 글이 없다', () => {
  const { container } = render(<ConsentView form={form()} token={TOKEN} />)

  expect(container.textContent).not.toMatch(/법적|효력|AI/)
})

test('보낸 뒤에는 매장 이름과 보낸 날을 말한다', () => {
  const { container, rerender } = render(<FormSubmitted shopName="Hiss Haus" submittedOn="2026-11-16" />)

  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('보냈어요')
  expect(container).toHaveTextContent('Hiss Haus에서 확인할게요.')
  expect(container).toHaveTextContent('2026년 11월 16일에 보냈어요')

  // 그 사이 매장에서 받았으면 보낸 날이 없다.
  rerender(<FormSubmitted shopName="Hiss Haus" submittedOn={null} />)
  expect(container.textContent).not.toContain('에 보냈어요')
})

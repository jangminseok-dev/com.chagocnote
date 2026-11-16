import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { IntakeForm } from '../components/IntakeForm'
import type { OpenIntake } from '../lib/form'

const refresh = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh }) }))

const TOKEN = 'ok'.padEnd(43, 'A')
const FORM: OpenIntake = {
  kind: 'intake',
  state: 'open',
  shop: { name: 'Hiss Haus' },
  mode: 'new',
  pet_name: null,
  fields: ['species', 'breed', 'sex', 'neutered', 'birth', 'weight', 'dislikes', 'style'],
  questions: [],
  condition_types: [
    { code: 'heart_disease', label: '심장 질환' },
    { code: 'other', label: '기타' },
  ],
  answered: 0,
  guardian_needed: true,
  keep_days: 30,
}
const fetchMock = vi.fn<typeof fetch>()

function respondWith(status: number) {
  fetchMock.mockResolvedValue(new Response(null, { status }))
}

function type(label: string | RegExp, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
}

function pick(name: string) {
  fireEvent.click(screen.getByRole('button', { name }))
}

/** 새 손님이 꼭 채워야 하는 것을 채운다 — 글자를 치는 것은 셋(보호자 이름·번호·아이 이름)이다. */
function fill() {
  type('보호자 이름', '김민지')
  type('전화번호', '010-1234-5678')
  type('아이 이름', '콩이')
  pick('강아지')
  pick('말티즈')
  pick('여아')
  pick('했어요')
  pick('몰라요')
  pick('모르겠어요')
  pick('없어요')
  fireEvent.click(screen.getByLabelText(/개인정보 수집·이용에 동의해요/))
}

async function press(name: RegExp) {
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name }))
  })
}

function sentBody() {
  const [url, init] = fetchMock.mock.calls.at(-1)!
  return { url, body: JSON.parse(String(init?.body)) }
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
  refresh.mockReset()
})

test('켜진 칸만 그리고 보호자 칸은 물을 때만 있다', () => {
  const { rerender } = render(<IntakeForm form={FORM} token={TOKEN} />)
  expect(screen.getByLabelText('보호자 이름')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '강아지' })).toBeInTheDocument()
  expect(screen.getByLabelText('몸무게(kg)')).toBeInTheDocument()

  rerender(<IntakeForm form={{ ...FORM, fields: ['species'], guardian_needed: false }} token={TOKEN} />)
  expect(screen.queryByLabelText('보호자 이름')).toBeNull()
  expect(screen.queryByLabelText('몸무게(kg)')).toBeNull()
  expect(screen.queryByLabelText(/싫어하는 것/)).toBeNull()
  expect(screen.getByRole('button', { name: '강아지' })).toBeInTheDocument()
})

test('필수로 글자를 치는 칸은 넷 이하다 — 보호자 이름·번호·아이 이름(품종은 고르면 치지 않는다)', () => {
  const { container } = render(<IntakeForm form={FORM} token={TOKEN} />)
  const required = container.querySelectorAll('input[data-required-text="true"]')
  expect(required.length).toBeLessThanOrEqual(4)
  expect([...required].map((input) => input.getAttribute('name'))).toEqual(['guardian_name', 'guardian_phone', 'pet_name'])
})

test('빠진 칸이 있으면 보내지 않고 그 칸의 이름으로 말한다', async () => {
  render(<IntakeForm form={FORM} token={TOKEN} />)
  type('보호자 이름', '김민지')

  await press(/^보내기$/)

  expect(screen.getByRole('alert')).toHaveTextContent('전화번호를 적어 주세요')
  expect(fetchMock).not.toHaveBeenCalled()
})

test('보내기는 웹 자신의 경로로 다 적었다고 보내고, 보냈다고 알린 뒤 화면을 다시 읽는다', async () => {
  respondWith(204)
  render(<IntakeForm form={FORM} token={TOKEN} />)
  fill()

  await press(/^보내기$/)

  const { url, body } = sentBody()
  expect(url).toBe(`/f/${TOKEN}/intake`)
  expect(body.done).toBe(true)
  expect(body.guardian).toEqual({ name: '김민지', phone: '010-1234-5678' })
  expect(body.pet).toMatchObject({ name: '콩이', species: 'dog', breed: '말티즈', sex: 'female', neutered: true,
    birth_unknown: true, weight_unknown: true, no_known_conditions: true })
  expect(screen.getByRole('status')).toHaveTextContent('보냈어요. Hiss Haus에서 확인할게요.')
  expect(refresh).toHaveBeenCalledTimes(1)
})

test('보내고 다른 아이도 적기 — 아이 칸이 비워지고 방금 낸 아이를 알려 준다', async () => {
  respondWith(204)
  render(<IntakeForm form={FORM} token={TOKEN} />)
  fill()

  await press(/보내고 다른 아이도 적기/)

  expect(sentBody().body.done).toBe(false)
  expect(screen.getByRole('status')).toHaveTextContent('콩이의 문진표를 보냈어요. 다음 아이를 적어 주세요.')
  expect(screen.getByLabelText('아이 이름')).toHaveValue('')
  expect(refresh).toHaveBeenCalledTimes(1)
})

test('지병을 고르면 한 줄 칸이 생기고 없어요를 누르면 고른 것이 풀린다', async () => {
  respondWith(204)
  render(<IntakeForm form={FORM} token={TOKEN} />)
  fill()
  pick('심장 질환')
  type('심장 질환 — 알려 주실 것', '약 복용 중')
  pick('기타')
  type('기타 — 어떤 지병인가요', '슬개골')

  await press(/^보내기$/)
  expect(sentBody().body.pet).toMatchObject({
    no_known_conditions: false,
    conditions: [
      { type_code: 'heart_disease', custom_label: null, note: '약 복용 중' },
      { type_code: 'other', custom_label: '슬개골', note: null },
    ],
  })
})

test('없어요를 누르면 고른 지병이 풀린다', () => {
  render(<IntakeForm form={FORM} token={TOKEN} />)
  pick('심장 질환')
  expect(screen.getByLabelText('심장 질환 — 알려 주실 것')).toBeInTheDocument()

  pick('없어요')

  expect(screen.queryByLabelText('심장 질환 — 알려 주실 것')).toBeNull()
  expect(screen.getByRole('button', { name: '없어요' })).toHaveAttribute('aria-pressed', 'true')
})

test('품종은 목록에 없으면 직접 적는다', async () => {
  respondWith(204)
  render(<IntakeForm form={FORM} token={TOKEN} />)
  fill()
  pick('직접 적기')
  type('품종', '꼬똥 드 툴레아')

  await press(/^보내기$/)
  expect(sentBody().body.pet.breed).toBe('꼬똥 드 툴레아')
})

test('매장이 더한 질문은 답 칸이 있고 필수 질문이 비면 보내지 않는다', async () => {
  respondWith(204)
  const form = { ...FORM, questions: [{ question_id: 7, label: '산책은 얼마나 하나요?', required: true }] }
  render(<IntakeForm form={form} token={TOKEN} />)
  fill()

  await press(/^보내기$/)
  expect(screen.getByRole('alert')).toHaveTextContent('꼭 답해야 하는 질문이 남아 있어요')

  type(/산책은 얼마나 하나요\?/, '하루 한 번')
  await press(/^보내기$/)
  expect(sentBody().body.extras).toEqual([{ question_id: 7, body: '하루 한 번' }])
})

test('다시 받기는 아이 이름을 보이고 바뀐 것만 적어 보낸다 — 다른 아이도 적기는 없다', async () => {
  respondWith(204)
  const form: OpenIntake = { ...FORM, mode: 'update', pet_name: '콩이', guardian_needed: false }
  render(<IntakeForm form={form} token={TOKEN} />)

  expect(screen.getByText('바뀐 것만 적어 주세요. 적지 않은 것은 그대로 둘게요.')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /다른 아이도 적기/ })).toBeNull()
  type('몸무게(kg)', '5.1')
  fireEvent.click(screen.getByLabelText(/개인정보 수집·이용에 동의해요/))
  await press(/^보내기$/)

  expect(sentBody().body.pet).toEqual({ weight_kg: 5.1 })
})

test('빠진 칸을 표시하고 그 칸으로 포커스를 옮긴다', async () => {
  render(<IntakeForm form={FORM} token={TOKEN} />)
  type('보호자 이름', '김민지')

  await press(/^보내기$/)

  const phone = screen.getByLabelText('전화번호')
  expect(phone).toHaveAttribute('aria-invalid', 'true')
  expect(phone).toHaveFocus()
  type('전화번호', '010-1234-5678')
  expect(phone).not.toHaveAttribute('aria-invalid', 'true')
  expect(screen.queryByRole('alert')).toBeNull()
})

test('422 면 화면을 다시 읽는다 — 매장이 그 사이 더한 필수 질문을 다시 그린 뒤에 짚는다', async () => {
  respondWith(422)
  const { rerender } = render(<IntakeForm form={FORM} token={TOKEN} />)
  fill()

  await press(/^보내기$/)
  expect(refresh).toHaveBeenCalledTimes(1)
  expect(screen.getByRole('alert')).toHaveTextContent('적은 내용을 다시 확인해 주세요')

  // 다시 읽은 구성이 props 로 온다 — 적은 것은 남고 새 칸이 생긴다.
  rerender(<IntakeForm form={{ ...FORM, questions: [{ question_id: 9, label: '새 질문', required: true }] }} token={TOKEN} />)
  expect(screen.getByLabelText('아이 이름')).toHaveValue('콩이')
  await press(/^보내기$/)
  expect(screen.getByRole('alert')).toHaveTextContent('꼭 답해야 하는 질문이 남아 있어요')
  expect(fetchMock).toHaveBeenCalledTimes(1)
})

test('보내면 링크가 닫힌다고 버튼 곁에 적혀 있고, 글자 칸의 엔터는 보내지 않는다', async () => {
  respondWith(204)
  const { rerender } = render(<IntakeForm form={FORM} token={TOKEN} />)
  expect(screen.getByText('보내면 이 링크는 닫혀요. 아이가 더 있으면 아래 버튼을 눌러 주세요.')).toBeInTheDocument()
  fill()

  fireEvent.keyDown(screen.getByLabelText('아이 이름'), { key: 'Enter' })
  const allowed = fireEvent.keyDown(screen.getByLabelText('아이 이름'), { key: 'Enter' })
  expect(allowed).toBe(false)                    // 기본 동작(폼 제출)을 막았다
  expect(fetchMock).not.toHaveBeenCalled()

  rerender(<IntakeForm form={{ ...FORM, mode: 'update', pet_name: '콩이', guardian_needed: false }} token={TOKEN} />)
  expect(screen.queryByText(/보내면 이 링크는 닫혀요/)).toBeNull()     // 다시 받기는 한 번뿐이라 말이 필요 없다
})

test('열 마리째에는 다른 아이도 적기가 없다', () => {
  render(<IntakeForm form={{ ...FORM, answered: 9, guardian_needed: false }} token={TOKEN} />)
  expect(screen.queryByRole('button', { name: /다른 아이도 적기/ })).toBeNull()
  expect(screen.queryByText(/보내면 이 링크는 닫혀요/)).toBeNull()
})

test.each([
  [410, null],
  [404, null],
  [422, '적은 내용을 다시 확인해 주세요'],
  [413, '적은 내용을 다시 확인해 주세요'],
  [429, '잠시 후 다시 보내 주세요'],
  [503, '잠시 후 다시 보내 주세요'],
])('상태 코드 %i', async (status, notice) => {
  respondWith(status)
  render(<IntakeForm form={FORM} token={TOKEN} />)
  fill()

  await press(/^보내기$/)

  if (notice === null) {
    // 그 사이 닫혔거나 끊겼다 — 오류 글이 아니라 화면을 다시 읽는다.
    expect(refresh).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('alert')).toBeNull()
  } else {
    expect(screen.getByRole('alert')).toHaveTextContent(notice)
    expect(screen.getByLabelText('아이 이름')).toHaveValue('콩이')      // 적은 것은 남는다
  }
})

test('보내는 동안 두 번 누르면 한 번만 나간다', async () => {
  let release: (value: Response) => void = () => {}
  fetchMock.mockReturnValue(new Promise<Response>((resolve) => (release = resolve)))
  render(<IntakeForm form={FORM} token={TOKEN} />)
  fill()

  await press(/^보내기$/)
  await press(/보내는 중/)

  expect(fetchMock).toHaveBeenCalledTimes(1)
  await act(async () => release(new Response(null, { status: 204 })))
})

test('개인정보 안내에 무엇을 왜 받고 언제 지우는지가 적혀 있다', () => {
  render(<IntakeForm form={{ ...FORM, keep_days: 14 }} token={TOKEN} />)
  const notice = screen.getByTestId('privacy')
  expect(notice).toHaveTextContent('보호자 이름·전화번호')
  expect(notice).toHaveTextContent('Hiss Haus')
  expect(notice).toHaveTextContent('14일')
})

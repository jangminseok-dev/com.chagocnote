import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { SignaturePad } from '../components/SignaturePad'

// jsdom 에는 캔버스가 없다 — 그리는 호출을 세는 가짜와, 캔버스 폭에 따라 다른 값을 주는 toDataURL 을 둔다.
const strokes: string[] = []
let big = false

beforeEach(() => {
  strokes.length = 0
  big = false
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(function (this: HTMLCanvasElement) {
    const record = (name: string) => () => strokes.push(`${name}@${this.width}`)
    return {
      beginPath: record('begin'), moveTo: record('move'), lineTo: record('line'), stroke: record('stroke'),
      arc: record('arc'), fill: record('fill'), clearRect: record('clear'), fillRect: record('paper'), drawImage: record('draw'),
      lineWidth: 0, lineCap: '', lineJoin: '', strokeStyle: '', fillStyle: '',
    } as unknown as CanvasRenderingContext2D
  } as never)
  vi.spyOn(HTMLCanvasElement.prototype, 'toDataURL').mockImplementation(function (this: HTMLCanvasElement) {
    const data = this.width === 600 && big ? 'B'.repeat(90_000) : `PNG${this.width}`
    return `data:image/png;base64,${data}`
  })
})

afterEach(() => vi.restoreAllMocks())

function draw(canvas: Element) {
  fireEvent.pointerDown(canvas, { clientX: 10, clientY: 10, pointerId: 1 })
  fireEvent.pointerMove(canvas, { clientX: 60, clientY: 40, pointerId: 1 })
  fireEvent.pointerUp(canvas, { clientX: 60, clientY: 40, pointerId: 1 })
}

test('캔버스는 600×240 이고 서명하는 곳이라고 읽힌다', () => {
  render(<SignaturePad onChange={() => {}} resetKey={0} />)

  const canvas = screen.getByLabelText('서명하는 곳') as HTMLCanvasElement
  expect([canvas.width, canvas.height]).toEqual([600, 240])
})

test('그리기 전에는 아무것도 알리지 않고, 선을 떼면 그림을 준다', () => {
  const onChange = vi.fn()
  render(<SignaturePad onChange={onChange} resetKey={0} />)
  expect(onChange).not.toHaveBeenCalled()

  draw(screen.getByLabelText('서명하는 곳'))

  expect(onChange).toHaveBeenLastCalledWith('PNG600')
  expect(strokes.some((s) => s.startsWith('stroke'))).toBe(true)
})

test('누르지 않고 움직이면 그리지 않는다', () => {
  const onChange = vi.fn()
  render(<SignaturePad onChange={onChange} resetKey={0} />)

  fireEvent.pointerMove(screen.getByLabelText('서명하는 곳'), { clientX: 60, clientY: 40, pointerId: 1 })

  expect(onChange).not.toHaveBeenCalled()
  expect(strokes.filter((s) => s.startsWith('line'))).toEqual([])
})

test('다시 쓰기는 지우고 비었다고 알린다', () => {
  const onChange = vi.fn()
  render(<SignaturePad onChange={onChange} resetKey={0} />)
  draw(screen.getByLabelText('서명하는 곳'))

  fireEvent.click(screen.getByRole('button', { name: '다시 쓰기' }))

  expect(onChange).toHaveBeenLastCalledWith(null)
  // 지운 자리에 흰 바탕을 다시 깐다 — 어두운 화면에서도 검은 선이 보이게 그림의 바탕은 늘 희다.
  expect(strokes.slice(-2)).toEqual(['clear@600', 'paper@600'])
})

test('밖에서 비우라고 하면(resetKey) 지우고 비었다고 알린다', () => {
  const onChange = vi.fn()
  const { rerender } = render(<SignaturePad onChange={onChange} resetKey={0} />)
  draw(screen.getByLabelText('서명하는 곳'))

  rerender(<SignaturePad onChange={onChange} resetKey={1} />)

  expect(onChange).toHaveBeenLastCalledWith(null)
})

test('그림이 크면 300×120 으로 줄여 그린 것을 준다', () => {
  big = true
  const onChange = vi.fn()
  render(<SignaturePad onChange={onChange} resetKey={0} />)

  draw(screen.getByLabelText('서명하는 곳'))

  expect(onChange).toHaveBeenLastCalledWith('PNG300')
  expect(strokes).toContain('draw@300')
})

test('그리는 중에 닿은 둘째 손가락은 선을 긋지 않는다', () => {
  const onChange = vi.fn()
  render(<SignaturePad onChange={onChange} resetKey={0} />)
  const canvas = screen.getByLabelText('서명하는 곳')
  const lines = () => strokes.filter((s) => s.startsWith('line')).length

  fireEvent.pointerDown(canvas, { clientX: 10, clientY: 10, pointerId: 1 })
  fireEvent.pointerMove(canvas, { clientX: 30, clientY: 20, pointerId: 1 })
  const before = lines()
  fireEvent.pointerDown(canvas, { clientX: 300, clientY: 100, pointerId: 2 })
  fireEvent.pointerMove(canvas, { clientX: 320, clientY: 120, pointerId: 2 })
  expect(lines()).toBe(before)

  // 둘째 손가락을 떼어도 서명은 이어진다.
  fireEvent.pointerUp(canvas, { clientX: 320, clientY: 120, pointerId: 2 })
  expect(onChange).not.toHaveBeenCalled()
  fireEvent.pointerMove(canvas, { clientX: 60, clientY: 40, pointerId: 1 })
  expect(lines()).toBe(before + 1)
  fireEvent.pointerUp(canvas, { clientX: 60, clientY: 40, pointerId: 1 })
  expect(onChange).toHaveBeenCalledTimes(1)
})

test('마우스의 오른쪽 단추로는 긋지 않는다', () => {
  const onChange = vi.fn()
  render(<SignaturePad onChange={onChange} resetKey={0} />)
  const canvas = screen.getByLabelText('서명하는 곳')

  fireEvent.pointerDown(canvas, { clientX: 10, clientY: 10, pointerId: 1, button: 2 })
  fireEvent.pointerMove(canvas, { clientX: 60, clientY: 40, pointerId: 1 })
  fireEvent.pointerUp(canvas, { clientX: 60, clientY: 40, pointerId: 1 })

  expect(onChange).not.toHaveBeenCalled()
})

test('포인터를 빼앗겨도 그리기가 끝나고 그림을 알린다', () => {
  const onChange = vi.fn()
  render(<SignaturePad onChange={onChange} resetKey={0} />)
  const canvas = screen.getByLabelText('서명하는 곳')
  fireEvent.pointerDown(canvas, { clientX: 10, clientY: 10, pointerId: 1 })
  fireEvent.pointerMove(canvas, { clientX: 60, clientY: 40, pointerId: 1 })

  fireEvent.lostPointerCapture(canvas, { pointerId: 1 })

  expect(onChange).toHaveBeenLastCalledWith('PNG600')
  // 끝난 뒤에는 누르지 않고 지나가도 긋지 않는다.
  const lines = strokes.filter((s) => s.startsWith('line')).length
  fireEvent.pointerMove(canvas, { clientX: 90, clientY: 60, pointerId: 1 })
  expect(strokes.filter((s) => s.startsWith('line')).length).toBe(lines)
})

test('비어 있을 때만 여기에 서명하라는 글이 보인다', () => {
  render(<SignaturePad onChange={() => {}} resetKey={0} />)
  expect(screen.getByText('여기에 서명해 주세요')).toBeInTheDocument()

  draw(screen.getByLabelText('서명하는 곳'))
  expect(screen.queryByText('여기에 서명해 주세요')).toBeNull()

  fireEvent.click(screen.getByRole('button', { name: '다시 쓰기' }))
  expect(screen.getByText('여기에 서명해 주세요')).toBeInTheDocument()
})

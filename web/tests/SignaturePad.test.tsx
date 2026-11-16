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
      arc: record('arc'), fill: record('fill'), clearRect: record('clear'), drawImage: record('draw'),
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
  expect(strokes.at(-1)).toBe('clear@600')
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

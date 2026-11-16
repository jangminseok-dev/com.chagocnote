'use client'

import { type PointerEvent, useEffect, useRef, useState } from 'react'
import styles from './Consent.module.css'

// 서명 그림의 논리 크기. 화면 배율을 곱하지 않는다 — 검은 선의 PNG 가 작게 유지된다(백엔드의 상한 600×240·65,536바이트).
const WIDTH = 600
const HEIGHT = 240
const SMALL_WIDTH = 300
const SMALL_HEIGHT = 120
// 65,536바이트의 base64 는 87,384글자다. 넘기 전에 줄인다.
const MAX_BASE64 = 87_380
const INK = '#161616'

function base64Of(canvas: HTMLCanvasElement): string {
  return canvas.toDataURL('image/png').split(',')[1] ?? ''
}

/** 캔버스의 그림을 base64 PNG 로. 크면 절반 크기로 다시 그린 것을 준다. */
function exportPng(canvas: HTMLCanvasElement): string {
  const full = base64Of(canvas)
  if (full.length <= MAX_BASE64) return full
  const small = document.createElement('canvas')
  small.width = SMALL_WIDTH
  small.height = SMALL_HEIGHT
  small.getContext('2d')?.drawImage(canvas, 0, 0, SMALL_WIDTH, SMALL_HEIGHT)
  return base64Of(small)
}

/**
 * 손가락·마우스로 서명하는 칸. 선을 뗄 때마다 그림을 알리고, 비우면 null 을 알린다.
 * resetKey 가 바뀌면 비운다(내용이 바뀌어 다시 서명받을 때).
 *
 * 한 번에 포인터 하나만 받는다 — 서명하는 동안 닿은 다른 손가락이나 손바닥은 선을 긋지 않는다.
 * 그림의 바탕은 늘 희다 — 매장 앱이 어두운 바탕에 그려도 검은 선이 보인다.
 */
export function SignaturePad({ onChange, resetKey }: { onChange: (png: string | null) => void; resetKey: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  /** 지금 그리는 포인터와 직전 점. 그리는 중이 아니면 null. */
  const stroke = useRef<{ id: number; x: number; y: number } | null>(null)
  const firstKey = useRef(resetKey)
  const [empty, setEmpty] = useState(true)

  const context = () => canvasRef.current?.getContext('2d') ?? null

  /** 지우고 흰 바탕을 깐다. */
  const paper = () => {
    const ctx = context()
    if (ctx === null) return
    ctx.clearRect(0, 0, WIDTH, HEIGHT)
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, WIDTH, HEIGHT)
  }

  /** 화면의 좌표를 캔버스의 좌표로. 캔버스는 CSS 로 늘어나 있다. */
  const point = (event: PointerEvent<HTMLCanvasElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    return {
      x: ((event.clientX - rect.left) * WIDTH) / (rect.width || WIDTH),
      y: ((event.clientY - rect.top) * HEIGHT) / (rect.height || HEIGHT),
    }
  }

  const clear = () => {
    stroke.current = null
    paper()
    setEmpty(true)
    onChange(null)
  }

  // 처음에 흰 바탕을 깐다.
  useEffect(paper, [])

  useEffect(() => {
    // 처음 그릴 때는 알리지 않는다 — 밖에서 비우라고 했을 때만 비운다.
    if (firstKey.current === resetKey) return
    firstKey.current = resetKey
    clear()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey])

  const start = (event: PointerEvent<HTMLCanvasElement>) => {
    // 이미 그리는 중이면 다른 포인터(둘째 손가락·손바닥)는 받지 않는다. 마우스는 왼쪽 단추만.
    if (stroke.current !== null || (event.pointerType === 'mouse' && event.button !== 0) || event.button > 0) return
    const ctx = context()
    if (ctx === null) return
    event.currentTarget.setPointerCapture?.(event.pointerId)
    const { x, y } = point(event)
    stroke.current = { id: event.pointerId, x, y }
    ctx.lineWidth = 3
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.strokeStyle = INK
    ctx.fillStyle = INK
    // 점만 찍고 떼어도 남게 한다.
    ctx.beginPath()
    ctx.arc(x, y, 1.5, 0, Math.PI * 2)
    ctx.fill()
    setEmpty(false)
  }

  const move = (event: PointerEvent<HTMLCanvasElement>) => {
    const from = stroke.current
    if (from === null || from.id !== event.pointerId) return
    const ctx = context()
    if (ctx === null) return
    const { x, y } = point(event)
    // 토막마다 따로 긋는다 — 선 전체를 다시 칠하면 가장자리가 겹쳐 진해지고 긴 선이 느려진다.
    ctx.beginPath()
    ctx.moveTo(from.x, from.y)
    ctx.lineTo(x, y)
    ctx.stroke()
    stroke.current = { id: from.id, x, y }
  }

  const end = (event: PointerEvent<HTMLCanvasElement>) => {
    if (stroke.current === null || stroke.current.id !== event.pointerId) return
    stroke.current = null
    if (canvasRef.current !== null) onChange(exportPng(canvasRef.current))
  }

  return (
    <div className={styles.pad}>
      <canvas
        ref={canvasRef}
        className={styles.canvas}
        width={WIDTH}
        height={HEIGHT}
        aria-label="서명하는 곳"
        role="img"
        onPointerDown={start}
        onPointerMove={move}
        onPointerUp={end}
        onPointerCancel={end}
        onLostPointerCapture={end}
      />
      {empty && (
        <span className={styles.hint} aria-hidden="true">
          여기에 서명해 주세요
        </span>
      )}
      <button type="button" className={styles.again} onClick={clear}>
        다시 쓰기
      </button>
    </div>
  )
}

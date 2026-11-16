'use client'

import { type PointerEvent, useEffect, useRef } from 'react'
import styles from './Consent.module.css'

// 서명 그림의 논리 크기. 화면 배율을 곱하지 않는다 — 검은 선의 PNG 가 작게 유지된다(백엔드의 상한 600×240·65,536바이트).
const WIDTH = 600
const HEIGHT = 240
const SMALL_WIDTH = 300
const SMALL_HEIGHT = 120
// 65,536바이트의 base64 는 87,384글자다. 넘기 전에 줄인다.
const MAX_BASE64 = 87_380

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
 */
export function SignaturePad({ onChange, resetKey }: { onChange: (png: string | null) => void; resetKey: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const drawing = useRef(false)
  const firstKey = useRef(resetKey)

  const context = () => canvasRef.current?.getContext('2d') ?? null

  /** 화면의 좌표를 캔버스의 좌표로. 캔버스는 CSS 로 늘어나 있다. */
  const point = (event: PointerEvent<HTMLCanvasElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    return {
      x: ((event.clientX - rect.left) * WIDTH) / (rect.width || WIDTH),
      y: ((event.clientY - rect.top) * HEIGHT) / (rect.height || HEIGHT),
    }
  }

  const clear = () => {
    context()?.clearRect(0, 0, WIDTH, HEIGHT)
    onChange(null)
  }

  useEffect(() => {
    // 처음 그릴 때는 알리지 않는다 — 밖에서 비우라고 했을 때만 비운다.
    if (firstKey.current === resetKey) return
    firstKey.current = resetKey
    clear()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey])

  const start = (event: PointerEvent<HTMLCanvasElement>) => {
    const ctx = context()
    if (ctx === null) return
    event.currentTarget.setPointerCapture?.(event.pointerId)
    drawing.current = true
    const { x, y } = point(event)
    ctx.lineWidth = 3
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.strokeStyle = '#161616'
    ctx.fillStyle = '#161616'
    // 점만 찍고 떼어도 남게 한다.
    ctx.beginPath()
    ctx.arc(x, y, 1.5, 0, Math.PI * 2)
    ctx.fill()
    ctx.beginPath()
    ctx.moveTo(x, y)
  }

  const move = (event: PointerEvent<HTMLCanvasElement>) => {
    if (!drawing.current) return
    const ctx = context()
    if (ctx === null) return
    const { x, y } = point(event)
    ctx.lineTo(x, y)
    ctx.stroke()
  }

  const end = () => {
    if (!drawing.current) return
    drawing.current = false
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
      />
      <button type="button" className={styles.again} onClick={clear}>
        다시 쓰기
      </button>
    </div>
  )
}

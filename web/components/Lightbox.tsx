'use client'

import { type ReactNode, type TouchEvent, useEffect, useRef, useState } from 'react'

import { mediaLabel } from '../lib/format'
import type { Media } from '../lib/report'
import styles from './Lightbox.module.css'

/** 이만큼(px) 넘게 옆으로 밀어야 넘긴다. */
const SWIPE = 40
/** 확대(⑫ 설계 3.2) — 두 번 누르면 이만큼, 두 손가락으로는 이만큼까지. */
const TAP_ZOOM = 2.5
const MAX_ZOOM = 4
const DOUBLE_TAP_MS = 300

type Props = { media: Media[]; start: number; onClose: () => void; footer?: (index: number) => ReactNode }
type Zoom = { scale: number; x: number; y: number }
const FIT: Zoom = { scale: 1, x: 0, y: 0 }

const distance = (touches: TouchEvent['touches']) =>
  Math.hypot(touches[0].clientX - touches[1].clientX, touches[0].clientY - touches[1].clientY)

/**
 * 크게 보기. 좌우로 넘기고(버튼·화살표 키·손가락), Esc·닫기 버튼·뒤로 가기로 닫는다.
 * 사진은 두 번 누르거나 두 손가락으로 벌려 확대하고, 확대 중에는 끌어 옮긴다 — 넘기기는 1배일 때만이다. 영상은 확대하지 않는다.
 * footer 는 지금 보는 미디어로 만든 한 줄이다(사진 모아 보기의 "그 알림장 보기").
 */
export function Lightbox({ media, start, onClose, footer }: Props) {
  const [index, setIndex] = useState(start)
  const [zoom, setZoom] = useState<Zoom>(FIT)
  const video = useRef<HTMLVideoElement>(null)
  const touch = useRef({ x: 0, y: 0, panX: 0, panY: 0 })
  const pinch = useRef<{ distance: number; scale: number } | null>(null)
  const gesture = useRef<'none' | 'pinch' | 'pan'>('none')
  const lastTap = useRef(0)
  const item = media[index]
  const label = mediaLabel(item)
  const photo = item.kind === 'photo'

  function go(step: number) {
    const next = index + step
    if (next < 0 || next >= media.length) return
    video.current?.pause()
    setZoom(FIT)
    setIndex(next)
  }

  function toggleZoom() {
    if (!photo) return
    setZoom((now) => (now.scale > 1 ? FIT : { scale: TAP_ZOOM, x: 0, y: 0 }))
  }

  function onTouchStart(event: TouchEvent) {
    const first = event.touches[0] ?? event.changedTouches[0]
    touch.current = { x: first.clientX, y: first.clientY, panX: zoom.x, panY: zoom.y }
    if (photo && event.touches.length >= 2) {
      gesture.current = 'pinch'
      pinch.current = { distance: distance(event.touches), scale: zoom.scale }
    } else {
      gesture.current = zoom.scale > 1 ? 'pan' : 'none'
    }
  }

  function onTouchMove(event: TouchEvent) {
    if (gesture.current === 'pinch' && pinch.current !== null && event.touches.length >= 2) {
      const scale = Math.min(MAX_ZOOM, Math.max(1, (pinch.current.scale * distance(event.touches)) / pinch.current.distance))
      setZoom((now) => (scale === 1 ? FIT : { ...now, scale }))
    } else if (gesture.current === 'pan' && event.touches.length === 1) {
      const { clientX, clientY } = event.touches[0]
      setZoom((now) => ({ ...now, x: touch.current.panX + clientX - touch.current.x, y: touch.current.panY + clientY - touch.current.y }))
    }
  }

  function onTouchEnd(event: TouchEvent) {
    if (event.touches.length > 0) return
    const { clientX, clientY } = event.changedTouches[0]
    const dx = clientX - touch.current.x
    const dy = clientY - touch.current.y
    const kind = gesture.current
    gesture.current = 'none'
    pinch.current = null
    if (kind !== 'none') return
    // 1배일 때만 넘긴다. 거의 움직이지 않은 두 번의 누름은 확대다.
    if (zoom.scale === 1 && Math.abs(dx) > SWIPE && Math.abs(dx) > Math.abs(dy)) {
      go(dx < 0 ? 1 : -1)
      return
    }
    if (Math.abs(dx) < 10 && Math.abs(dy) < 10) {
      const now = Date.now()
      if (now - lastTap.current < DOUBLE_TAP_MS) {
        lastTap.current = 0
        toggleZoom()
      } else {
        lastTap.current = now
      }
    }
  }

  // 뒤로 가기(안드로이드의 버튼·몸짓)가 알림장을 떠나지 않고 크게 보기만 닫게 방문 기록에 한 칸을 쌓는다.
  // 주소는 바꾸지 않는다(URL 인자가 없다). 개발 모드는 이펙트를 두 번 돌리므로 한 번만 쌓는다.
  const pushed = useRef(false)
  useEffect(() => {
    if (!pushed.current) {
      pushed.current = true
      history.pushState(null, '')
    }
    window.addEventListener('popstate', onClose)
    return () => window.removeEventListener('popstate', onClose)
  }, [onClose])

  /** 닫기 버튼·Esc — 쌓은 칸을 치운다. 두면 뒤로 가기를 두 번 눌러야 알림장을 떠난다. */
  function close() {
    onClose()
    history.back()
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') close()
      if (event.key === 'ArrowLeft') go(-1)
      if (event.key === 'ArrowRight') go(1)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  })

  // 열려 있는 동안 뒤 화면이 스크롤되지 않는다.
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  return (
    <div className={styles.box} role="dialog" aria-modal="true" aria-label="크게 보기">
      <div className={styles.bar}>
        <span>
          {index + 1} / {media.length}
        </span>
        <button type="button" className={styles.close} onClick={close} aria-label="닫기" autoFocus>
          ✕
        </button>
      </div>
      <div
        className={styles.stage}
        data-stage
        data-scale={zoom.scale}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        {item.kind === 'video' ? (
          <video key={index} ref={video} controls playsInline poster={item.thumb_url} src={item.display_url} />
        ) : (
          <img
            key={index}
            src={item.display_url}
            alt={label}
            onDoubleClick={toggleZoom}
            draggable={false}
            style={zoom.scale > 1 ? { transform: `translate(${zoom.x}px, ${zoom.y}px) scale(${zoom.scale})` } : undefined}
          />
        )}
      </div>
      <div className={styles.bar}>
        <button type="button" className={styles.move} onClick={() => go(-1)} disabled={index === 0} aria-label="이전">
          ‹
        </button>
        <a className={styles.save} href={item.download_url}>
          저장
        </a>
        <button
          type="button"
          className={styles.move}
          onClick={() => go(1)}
          disabled={index === media.length - 1}
          aria-label="다음"
        >
          ›
        </button>
      </div>
      {footer && <div className={styles.footer}>{footer(index)}</div>}
    </div>
  )
}

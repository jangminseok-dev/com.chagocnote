'use client'

import { useEffect, useRef, useState } from 'react'

import { mediaLabel } from '../lib/format'
import type { Media } from '../lib/report'
import styles from './Lightbox.module.css'

/** 이만큼(px) 넘게 옆으로 밀어야 넘긴다. */
const SWIPE = 40

type Props = { media: Media[]; start: number; onClose: () => void }

/** 크게 보기. 좌우로 넘기고(버튼·화살표 키·손가락), Esc·닫기 버튼·뒤로 가기로 닫는다. */
export function Lightbox({ media, start, onClose }: Props) {
  const [index, setIndex] = useState(start)
  const video = useRef<HTMLVideoElement>(null)
  const touch = useRef({ x: 0, y: 0 })
  const item = media[index]
  const label = mediaLabel(item)

  function go(step: number) {
    const next = index + step
    if (next < 0 || next >= media.length) return
    video.current?.pause()
    setIndex(next)
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
        onTouchStart={(event) => {
          const { clientX, clientY } = event.changedTouches[0]
          touch.current = { x: clientX, y: clientY }
        }}
        onTouchEnd={(event) => {
          const { clientX, clientY } = event.changedTouches[0]
          const dx = clientX - touch.current.x
          const dy = clientY - touch.current.y
          if (Math.abs(dx) > SWIPE && Math.abs(dx) > Math.abs(dy)) go(dx < 0 ? 1 : -1)
        }}
      >
        {item.kind === 'video' ? (
          <video key={index} ref={video} controls playsInline poster={item.thumb_url} src={item.display_url} />
        ) : (
          <img key={index} src={item.display_url} alt={label} />
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
    </div>
  )
}

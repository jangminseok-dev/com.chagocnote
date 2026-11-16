'use client'

import { useState } from 'react'
import type { Media } from '../lib/report'
import { KakaoNotice } from './KakaoNotice'
import styles from './ReportView.module.css'

/** 차례로 내려받을 때 두는 간격(ms). 붙여서 누르면 브라우저가 뒤의 것을 버린다. */
const GAP = 600
/** 공유 시트는 파일을 전부 메모리에 올린다 — 사진만이고 이만큼 이하일 때만 쓴다(⑫ 설계 3.1). */
const SHARE_MAX = 10
/** 서명 주소는 24~48시간 산다 — 화면을 연 지 이만큼이 지났으면 받기 전에 새로 고치라고 한다. */
const STALE_MS = 24 * 60 * 60 * 1000

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

function canShareFiles(): boolean {
  const probe = new File([], 'chagocnote-1.jpg', { type: 'image/jpeg' })
  return navigator.canShare?.({ files: [probe] }) === true
}

/** 내려받기용 주소를 받아 파일로 만든다. 이름을 읽을 수 없으면(CORS) 순번으로 짓는다. */
async function toFile(item: Media, index: number): Promise<File> {
  const response = await fetch(item.download_url)
  if (!response.ok) throw new Error('미디어를 받지 못했다.')
  const named = /filename="?([^";]+)/.exec(response.headers.get('Content-Disposition') ?? '')
  const name = named?.[1] ?? `chagocnote-${index + 1}.${item.kind === 'video' ? 'mp4' : 'jpg'}`
  const blob = await response.blob()
  return new File([blob], name, { type: blob.type })
}

async function downloadEach(media: Media[], onStep: (done: number) => void) {
  for (const [index, item] of media.entries()) {
    if (index > 0) await wait(GAP)
    onStep(index + 1)
    const link = document.createElement('a')
    link.href = item.download_url
    link.hidden = true
    document.body.append(link)
    link.click()
    link.remove()
  }
}

/**
 * 모두 저장. 사진만이고 열 장 이하이며 파일 공유가 되면 공유 시트로 한 번에 넘기고(받지 못한 것은 건너뛰고 수를 알린다),
 * 그 밖에는 원본 주소를 차례로 내려받는다(몇 번째인지 보인다). 다시 인코딩하지 않는다 — 화질이 그대로다.
 * label·note 로 글자와 버튼 아래의 한 줄을 바꾼다(사진 모아 보기의 한 쪽 저장). openedAt 은 화면을 그린 시각이다.
 */
export function SaveAllButton({
  media, label = '사진 · 영상 모두 저장', note, openedAt,
}: { media: Media[]; label?: string; note?: string; openedAt?: number }) {
  const [saving, setSaving] = useState(false)
  const [step, setStep] = useState<number | null>(null)
  const [missed, setMissed] = useState<Media[]>([])
  const [stale, setStale] = useState(false)

  async function save(items: Media[]) {
    setSaving(true)
    setMissed([])
    try {
      const shareable = items.length <= SHARE_MAX && items.every((item) => item.kind === 'photo') && canShareFiles()
      if (shareable) {
        const settled = await Promise.allSettled(items.map(toFile))
        const files = settled.flatMap((r) => (r.status === 'fulfilled' ? [r.value] : []))
        const failed = items.filter((_, i) => settled[i].status === 'rejected')
        if (files.length > 0) {
          try {
            await navigator.share({ files })
            setMissed(failed)
            return
          } catch (error) {
            // 사용자가 공유 시트를 닫은 것은 실패가 아니다.
            if (error instanceof DOMException && error.name === 'AbortError') return
          }
        }
      }
      await downloadEach(items, setStep)
    } finally {
      setSaving(false)
      setStep(null)
    }
  }

  function onClick() {
    if (openedAt !== undefined && Date.now() - openedAt > STALE_MS) {
      setStale(true)
      return
    }
    void save(media)
  }

  return (
    <div data-section="save-all">
      <button type="button" className={styles.pill} disabled={saving} onClick={onClick}>
        {saving ? (step === null ? '저장하는 중…' : `저장하는 중… ${step} / ${media.length}`) : label}
      </button>
      {note !== undefined && <p className={styles.notice}>{note}</p>}
      {stale && (
        <p className={styles.notice} role="status">
          화면을 연 지 하루가 지났어요. 새로 고친 뒤 다시 눌러 주세요
        </p>
      )}
      {missed.length > 0 && (
        <p className={styles.notice} role="status">
          {missed.length}개를 받지 못했어요{' '}
          <button type="button" className={styles.pill} disabled={saving} onClick={() => void save(missed)}>
            다시 받기
          </button>
        </p>
      )}
      <KakaoNotice />
    </div>
  )
}

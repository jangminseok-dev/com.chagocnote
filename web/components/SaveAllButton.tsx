'use client'

import { useState } from 'react'

import type { Media } from '../lib/report'
import { KakaoNotice } from './KakaoNotice'
import styles from './ReportView.module.css'

/** 차례로 내려받을 때 두는 간격(ms). 붙여서 누르면 브라우저가 뒤의 것을 버린다. */
const GAP = 600

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

async function downloadEach(media: Media[]) {
  for (const [index, item] of media.entries()) {
    if (index > 0) await wait(GAP)
    const link = document.createElement('a')
    link.href = item.download_url
    link.hidden = true
    document.body.append(link)
    link.click()
    link.remove()
  }
}

async function saveAll(media: Media[]) {
  if (canShareFiles()) {
    try {
      const files = await Promise.all(media.map(toFile))
      await navigator.share({ files })
      return
    } catch (error) {
      // 사용자가 공유 시트를 닫은 것은 실패가 아니다.
      if (error instanceof DOMException && error.name === 'AbortError') return
    }
  }
  await downloadEach(media)
}

/** 모두 저장. 공유 시트로 넘기고, 안 되면 하나씩 차례로 내려받는다. */
export function SaveAllButton({ media }: { media: Media[] }) {
  const [saving, setSaving] = useState(false)

  async function onClick() {
    setSaving(true)
    try {
      await saveAll(media)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div data-section="save-all">
      <button type="button" className={styles.pill} disabled={saving} onClick={onClick}>
        {saving ? '저장하는 중…' : '사진 · 영상 모두 저장'}
      </button>
      <KakaoNotice />
    </div>
  )
}

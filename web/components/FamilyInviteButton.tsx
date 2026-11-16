'use client'

import { useState } from 'react'
import styles from './Member.module.css'

type Status = 'idle' | 'busy' | 'shared' | 'copied' | 'shown' | 'full' | 'failed'

/**
 * [가족과 함께 보기](⑫ 설계 3.5) — 웹 서버가 초대를 만들어 주소(`/j/<코드>`)만 돌려주고, 이 버튼이 공유 시트나 복사로 넘긴다.
 * 주소는 페이지 주소·쿠키에 싣지 않고 기록하지 않는다. 공유도 복사도 안 되는 브라우저에만 화면에 보인다.
 */
export function FamilyInviteButton({ linkId }: { linkId: number }) {
  const [status, setStatus] = useState<Status>('idle')
  const [shown, setShown] = useState<string | null>(null)

  async function invite() {
    setStatus('busy')
    let res: Response
    try {
      res = await fetch(`/me/${linkId}/family-invite`, { method: 'POST' })
    } catch {
      setStatus('failed')
      return
    }
    if (res.status === 401) {
      window.location.assign('/login?next=%2Fme')
      return
    }
    if (res.status === 409) return setStatus('full')
    if (res.status !== 200) return setStatus('failed')
    const { path } = (await res.json()) as { path: string }
    const url = `${window.location.origin}${path}`
    try {
      if (navigator.share) {
        await navigator.share({ title: '차곡노트 — 함께 보기', url })
        return setStatus('shared')
      }
      await navigator.clipboard.writeText(url)
      setStatus('copied')
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return setStatus('idle')
      setShown(url)
      setStatus('shown')
    }
  }

  return (
    <div className={styles.invite}>
      <button type="button" className={styles.primary} disabled={status === 'busy'} onClick={() => void invite()}>
        가족과 함께 보기
      </button>
      {status === 'shared' && <p role="status">초대를 보냈어요. 가족이 열고 로그인하면 함께 봐요.</p>}
      {status === 'copied' && <p role="status">초대 주소를 복사했어요. 가족에게 보내 주세요.</p>}
      {status === 'shown' && shown !== null && (
        <p role="status">
          이 주소를 가족에게 보내 주세요 <input className={styles.input} readOnly value={shown} aria-label="초대 주소" />
        </p>
      )}
      {status === 'full' && <p role="status">함께 볼 수 있는 가족이 다 찼어요.</p>}
      {status === 'failed' && <p role="status">초대를 만들지 못했어요. 잠시 후 다시 눌러 주세요.</p>}
    </div>
  )
}

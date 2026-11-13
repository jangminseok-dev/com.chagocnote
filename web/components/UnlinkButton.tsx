'use client'

import type { FormEvent } from 'react'
import styles from './Member.module.css'

/** 연결 끊기. 누르면 한 번 묻는다 — 스크립트가 꺼져 있으면 묻지 않고 끊는다(알림장을 다시 받으면 다시 이을 수 있다). */
export function UnlinkButton({ linkId, shopName }: { linkId: number; shopName: string }) {
  const ask = (event: FormEvent) => {
    const question = `${shopName}의 지난 기록을 더는 볼 수 없어요. 알림장을 다시 받으면 다시 이을 수 있어요. 연결을 끊을까요?`
    if (!window.confirm(question)) event.preventDefault()
  }
  return (
    <form method="post" action={`/me/${linkId}/unlink`} onSubmit={ask}>
      <button className={styles.plain} type="submit">
        연결 끊기
      </button>
    </form>
  )
}

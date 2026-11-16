'use client'

import type { FormEvent } from 'react'
import styles from './Member.module.css'

type Props = {
  linkId: number
  shopName: string
  /** 기본 연결인지 가족 연결인지(⑫). 예전 백엔드면 없다 — 기본 연결로 본다. */
  role?: 'primary' | 'family'
  /** 함께 보는 가족의 수(기본 연결만). */
  familyCount?: number
}

/** 확인 글 — 끊으면 함께 사라지는 것과 다시 잇는 길을 연결마다 맞게 말한다. */
function questionOf({ shopName, role, familyCount = 0 }: Props): string {
  const lost = `${shopName}의 지난 기록을 더는 볼 수 없어요.`
  // 가족 연결은 받은 알림장으로 잇지 않았다 — 다시 보려면 새 초대다.
  if (role === 'family') return `${lost} 다시 보려면 가족에게 새 초대를 받아야 해요. 연결을 끊을까요?`
  // 기본 연결이 끝나면 함께 보던 가족도 끝난다(⑫ 설계 3.5).
  const family = familyCount > 0 ? ' 함께 보던 가족도 볼 수 없어요.' : ''
  return `${lost}${family} 알림장을 다시 받으면 다시 이을 수 있어요. 연결을 끊을까요?`
}

/** 연결 끊기. 누르면 한 번 묻는다 — 스크립트가 꺼져 있으면 묻지 않고 끊는다. */
export function UnlinkButton(props: Props) {
  const ask = (event: FormEvent) => {
    if (!window.confirm(questionOf(props))) event.preventDefault()
  }
  return (
    <form method="post" action={`/me/${props.linkId}/unlink`} onSubmit={ask}>
      <button className={styles.plain} type="submit">
        연결 끊기
      </button>
    </form>
  )
}

'use client'

import { useSyncExternalStore } from 'react'

import styles from './ReportView.module.css'

const subscribe = () => () => {}
const inKakaoTalk = () => navigator.userAgent.includes('KAKAOTALK')
const onServer = () => false

/** 카카오톡 내장 브라우저에서만 보이는 안내. 서버는 그리지 않고 브라우저가 붙은 뒤에 판단한다. */
export function KakaoNotice() {
  const show = useSyncExternalStore(subscribe, inKakaoTalk, onServer)
  if (!show) return null
  return <p className={styles.notice}>저장이 안 되면 ⋯ → 다른 브라우저로 열기</p>
}

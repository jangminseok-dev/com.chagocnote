'use client'

import { useEffect, useRef } from 'react'

/** 열람 신호. 브라우저에서 열렸을 때 한 번 보낸다 — 실패해도 알리지 않고 다시 보내지 않는다. */
export function ViewedSignal({ token }: { token: string }) {
  // 개발 모드는 이펙트를 두 번 돌린다.
  const sent = useRef(false)
  useEffect(() => {
    if (sent.current) return
    sent.current = true
    fetch(`/r/${token}/viewed`, { method: 'POST', keepalive: true }).catch(() => {})
  }, [token])
  return null
}

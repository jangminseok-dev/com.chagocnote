'use client'

import { useEffect, useState } from 'react'

/**
 * 보던 자리(⑫ 설계 3.2). 목록(지난 알림장·사진 모아 보기)을 열면 그 주소를 sessionStorage 에 적고(경로와 질의뿐 —
 * 토큰·서명 주소는 적지 않는다), 한 장의 돌아가기가 그 주소의 그 줄(`#r<report_id>`)로 간다. 스크립트가 없으면 첫 쪽이다.
 * 같은 연결의 목록만 따라간다.
 */
const key = (linkId: number) => `cn-list:${linkId}`

function sameLink(path: string | null, linkId: number): path is string {
  return path !== null && new RegExp(`^/me/${linkId}(/photos)?(\\?[A-Za-z0-9_=&%.-]*)?$`).test(path)
}

function read(linkId: number): string | null {
  try {
    const path = sessionStorage.getItem(key(linkId))
    return sameLink(path, linkId) ? path : null
  } catch {
    return null
  }
}

/** 목록 화면에 둔다 — 그리는 것은 없다. */
export function RememberList({ linkId }: { linkId: number }) {
  useEffect(() => {
    const path = window.location.pathname + window.location.search
    if (!sameLink(path, linkId)) return
    try {
      sessionStorage.setItem(key(linkId), path)
    } catch {
      // 저장이 막힌 브라우저 — 첫 쪽으로 돌아간다.
    }
  }, [linkId])
  return null
}

/** 한 장의 돌아가기. 서버는 첫 쪽으로 그리고, 스크립트가 적어 둔 목록으로 바꾼다. */
export function BackToList({ linkId, reportId, className }: { linkId: number; reportId: number; className?: string }) {
  const [path, setPath] = useState<string | null>(null)
  useEffect(() => setPath(read(linkId)), [linkId])
  const photos = path?.includes('/photos') === true
  return (
    <a className={className} href={path === null ? `/me/${linkId}` : `${path}#r${reportId}`}>
      {photos ? '사진 모아 보기' : '지난 알림장'}
    </a>
  )
}

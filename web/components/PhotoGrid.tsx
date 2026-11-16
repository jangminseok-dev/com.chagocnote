'use client'

import { useState } from 'react'
import { koreanDate, koreanFullDate, mediaLabel } from '../lib/format'
import type { MediaItem } from '../lib/guardian'
import { Lightbox } from './Lightbox'
import styles from './Member.module.css'

/** 사진 모아 보기의 격자 — 날짜(알림장)마다 묶고, 누르면 크게 보기. 묶음의 id 는 한 장에서 돌아올 자리다. */
export function PhotoGrid({ linkId, items }: { linkId: number; items: MediaItem[] }) {
  const [opened, setOpened] = useState<number | null>(null)
  const groups: { reportId: number; date: string; entries: { item: MediaItem; index: number }[] }[] = []
  items.forEach((item, index) => {
    const last = groups.at(-1)
    if (last && last.reportId === item.report_id) last.entries.push({ item, index })
    else groups.push({ reportId: item.report_id, date: item.visit_date, entries: [{ item, index }] })
  })
  return (
    <div data-section="grid">
      {groups.map((group) => (
        <section key={group.reportId} id={`r${group.reportId}`} className={styles.day}>
          <h2>{koreanFullDate(group.date)}</h2>
          <ul className={styles.grid}>
            {group.entries.map(({ item, index }) => (
              <li key={index}>
                <button type="button" onClick={() => setOpened(index)} aria-label={`${koreanDate(item.visit_date)} ${mediaLabel(item)} 크게 보기`}>
                  <img src={item.thumb_url} width={item.width} height={item.height} alt="" loading="lazy" />
                  {item.kind === 'video' && <span className={styles.play} aria-hidden="true">▶</span>}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
      {opened !== null && (
        <Lightbox
          media={items}
          start={opened}
          onClose={() => setOpened(null)}
          footer={(index) => <a href={`/me/${linkId}/${items[index].report_id}`}>{koreanDate(items[index].visit_date)} 알림장 보기</a>}
        />
      )}
    </div>
  )
}

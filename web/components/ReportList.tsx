import { koreanFullDate } from '../lib/format'
import type { ReportPage } from '../lib/guardian'
import { RememberList } from './BackToList'
import styles from './Member.module.css'

/** 지난 알림장 한 쪽(최신순). petId 가 있으면 그 아이의 알림장만 거른 목록이다. */
export function ReportList({ linkId, petId, page }: { linkId: number; petId: number | null; page: ReportPage }) {
  const { items, next_cursor: nextCursor } = page
  // 다음 쪽으로 넘어가는 링크다. 쌓아 붙이지 않는다 — 대표 사진의 서명 주소가 짧게 살아 쪽마다 새로 받는다.
  const more = nextCursor === null ? null : `/me/${linkId}?${petId === null ? '' : `pet=${petId}&`}cursor=${encodeURIComponent(nextCursor)}`
  return (
    <main className={styles.page}>
      <RememberList linkId={linkId} />
      <header data-section="list-head">
        <a className={styles.back} href="/me">
          내 기록
        </a>
        <div className={styles.mark} aria-hidden="true">
          Notes
        </div>
        <h1 className={styles.title}>지난 알림장</h1>
      </header>
      <nav className={styles.tabs} data-section="tabs">
        <a href={petId === null ? `/me/${linkId}` : `/me/${linkId}?pet=${petId}`} aria-current="page">
          알림장
        </a>
        <a href={petId === null ? `/me/${linkId}/photos` : `/me/${linkId}/photos?pet=${petId}`}>사진</a>
      </nav>
      {items.length === 0 ? (
        <p className={styles.text} data-section="empty">
          아직 받은 알림장이 없어요
        </p>
      ) : (
        <ul className={styles.reports}>
          {items.map((item) => (
            <li key={item.report_id} id={`r${item.report_id}`} data-section="item">
              <a href={`/me/${linkId}/${item.report_id}`}>
                <span className={styles.cover}>
                  {item.cover && (
                    <img src={item.cover.url} width={item.cover.width} height={item.cover.height} alt="" loading="lazy" />
                  )}
                </span>
                <b>{koreanFullDate(item.visit_date)}</b>
                {item.pet_name !== null && <span>{item.pet_name}</span>}
                {item.media_count > 0 && <small>사진·영상 {item.media_count}</small>}
              </a>
            </li>
          ))}
        </ul>
      )}
      {more !== null && (
        <nav className={styles.more} data-section="more">
          <a className={styles.primary} href={more}>
            더 보기
          </a>
        </nav>
      )}
    </main>
  )
}

import { safeReviewUrl } from '../lib/report'
import styles from './ReportView.module.css'

/**
 * 알림장 끝의 리뷰 남기기 줄(⑫ 설계 3.6) — 매장 카드 아래, 꼬리 위. 주소가 https 가 아니면 그리지 않는다.
 * 알림장에서 밖으로 나가는 링크다 — `noreferrer` 와 응답 헤더 `Referrer-Policy: no-referrer` 가 알림장 주소(토큰)를 넘기지 않는다.
 * 문구는 글자로만 그린다.
 */
export function ReviewLine({ url, text }: { url?: string; text?: string }) {
  const href = safeReviewUrl(url)
  if (href === null || !text) return null
  return (
    <section className={styles.review} data-section="review">
      <a className={styles.pill} href={href} target="_blank" rel="noopener noreferrer nofollow">
        {text}
      </a>
    </section>
  )
}

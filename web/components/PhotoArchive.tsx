import type { MediaPage, WeightItem } from '../lib/guardian'
import { RememberList } from './BackToList'
import styles from './Member.module.css'
import { PhotoGrid } from './PhotoGrid'
import { SaveAllButton } from './SaveAllButton'
import { WeightChart } from './WeightChart'

type Phase = 'after' | 'before'
type Props = {
  linkId: number
  petId: number | null
  filter: { year: number | null; phase: Phase | null }
  page: MediaPage
  weights: WeightItem[] | null // 아이를 골랐을 때만 — 매장이 몸무게를 껐으면 빈 목록
  openedAt: number // 화면을 그린 시각 — 서명 주소가 끝났을 화면에서 받지 않게
}

/** 거르기를 지키는 주소. 질의의 순서는 pet·year·phase 다(safeNext 가 이 모양만 받는다). */
function photosPath(linkId: number, petId: number | null, year: number | null, phase: Phase | null, cursor?: string) {
  const params = new URLSearchParams()
  if (petId !== null) params.set('pet', String(petId))
  if (year !== null) params.set('year', String(year))
  if (phase !== null) params.set('phase', phase)
  if (cursor !== undefined) params.set('cursor', cursor)
  return `/me/${linkId}/photos${params.size > 0 ? `?${params}` : ''}`
}

/**
 * 아이의 사진·영상 모아 보기(⑫ 설계 3.4) — 최신순 60개, 날짜마다 묶은 격자, 연도·전후 거르기, 이 쪽 모두 저장, 몸무게.
 * 나오는 것은 받은 알림장 한 장들에 나오는 것과 같다(백엔드가 같은 조건으로 고른다).
 */
export function PhotoArchive({ linkId, petId, filter, page, weights, openedAt }: Props) {
  const { items, next_cursor: nextCursor, years } = page
  const filtered = filter.year !== null || filter.phase !== null
  const reportsHref = petId === null ? `/me/${linkId}` : `/me/${linkId}?pet=${petId}`
  const choice = (label: string, href: string, current: boolean) => (
    <a key={label} href={href} aria-current={current ? 'true' : undefined} className={current ? styles.chosen : undefined}>
      {label}
    </a>
  )
  return (
    <main className={styles.page}>
      <RememberList linkId={linkId} />
      <header data-section="photos-head">
        <a className={styles.back} href="/me">
          내 기록
        </a>
        <div className={styles.mark} aria-hidden="true">
          Photos
        </div>
        <h1 className={styles.title}>사진 모아 보기</h1>
      </header>
      <nav className={styles.tabs} data-section="tabs">
        <a href={reportsHref}>알림장</a>
        <a href={photosPath(linkId, petId, null, null)} aria-current="page">
          사진
        </a>
      </nav>
      {/* 거르기는 거른 결과가 비어도 남는다 — 다른 조건으로 빠져나올 길이다. */}
      {(items.length > 0 || filtered || years.length > 0) && (
        <nav className={styles.filter} data-section="filter" aria-label="거르기">
          <div>
            {choice('전체 연도', photosPath(linkId, petId, null, filter.phase), filter.year === null)}
            {years.map((year) => choice(`${year}년`, photosPath(linkId, petId, year, filter.phase), filter.year === year))}
          </div>
          <div>
            {choice('전체', photosPath(linkId, petId, filter.year, null), filter.phase === null)}
            {choice('후', photosPath(linkId, petId, filter.year, 'after'), filter.phase === 'after')}
            {choice('전', photosPath(linkId, petId, filter.year, 'before'), filter.phase === 'before')}
          </div>
        </nav>
      )}
      {items.length === 0 ? (
        <p className={styles.text} data-section="empty">
          {filtered ? '이 조건의 사진이 없어요' : '아직 받은 사진이 없어요'}
        </p>
      ) : (
        <SaveAllButton
          media={items}
          label="이 화면의 사진 · 영상 모두 저장"
          note={`이 쪽의 ${items.length}개를 받아요.${nextCursor === null ? '' : ' 다음 쪽은 넘어가서 한 번 더 눌러 주세요'}`}
          openedAt={openedAt}
        />
      )}
      {/* 몸무게는 사진과 따로다 — 사진 없이 몸무게만 받은 아이도 본다. */}
      {weights !== null && <WeightChart items={weights} />}
      {items.length > 0 && (
        <>
          <PhotoGrid linkId={linkId} items={items} />
          {nextCursor !== null && (
            <nav className={styles.more} data-section="more">
              <a className={styles.primary} href={photosPath(linkId, petId, filter.year, filter.phase, nextCursor)}>
                더 보기
              </a>
            </nav>
          )}
        </>
      )}
    </main>
  )
}

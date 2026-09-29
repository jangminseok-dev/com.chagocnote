import { mediaLabel, phaseLabel } from '../lib/format'
import type { Media } from '../lib/report'
import styles from './ReportView.module.css'
import { SaveButton } from './SaveButton'

type Props = { media: Media; index: number; total: number; onOpen: () => void }

/** 칸의 세로는 가로의 이 배수를 넘지 않는다 — 세로로 긴 미디어가 첫 화면을 다 차지하지 않게 한다. */
const TALLEST = 1.25

/** 대표 미디어. 사진은 표시용, 영상은 포스터와 재생 표시다. */
export function HeroMedia({ media, index, total, onOpen }: Props) {
  const label = mediaLabel(media)
  const height = Math.min(media.height, media.width * TALLEST)
  return (
    <div className={styles.hero} data-section="hero">
      <button type="button" className={styles.open} aria-label={`${label} 크게 보기`} onClick={onOpen}>
        {/* 비율을 먼저 정해 그림이 오기 전에도 자리가 밀리지 않는다. 한도를 넘는 그림은 가운데가 보인다. */}
        <img
          src={media.kind === 'video' ? media.thumb_url : media.display_url}
          width={media.width}
          height={media.height}
          alt={label}
          style={{ aspectRatio: `${media.width} / ${height}` }}
        />
        {media.kind === 'video' && <span className={styles.play} data-play aria-hidden="true" />}
      </button>
      <span className={styles.count}>
        {index + 1} / {total}
      </span>
      <span className={styles.tag}>{phaseLabel(media.phase)}</span>
      <SaveButton media={media} />
    </div>
  )
}

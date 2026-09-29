import { mediaLabel, phaseLabel } from '../lib/format'
import type { Media } from '../lib/report'
import styles from './ReportView.module.css'
import { SaveButton } from './SaveButton'

type Props = { media: Media; index: number; total: number }

/** 대표 미디어. 사진은 표시용, 영상은 포스터와 재생 표시다. */
export function HeroMedia({ media, index, total }: Props) {
  const label = mediaLabel(media)
  return (
    <div className={styles.hero} data-section="hero">
      <button type="button" className={styles.open} aria-label={`${label} 크게 보기`}>
        {/* width·height 가 비율을 잡아 그림이 오기 전에도 자리가 밀리지 않는다. */}
        <img
          src={media.kind === 'video' ? media.thumb_url : media.display_url}
          width={media.width}
          height={media.height}
          alt={label}
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

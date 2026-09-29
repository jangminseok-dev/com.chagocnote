import { duration, mediaLabel } from '../lib/format'
import type { Media } from '../lib/report'
import styles from './ReportView.module.css'

/** 미디어 줄. 넷이 한 줄에 보이고 더 있으면 가로로 넘겨 본다. */
export function MediaStrip({ media }: { media: Media[] }) {
  return (
    <section data-section="strip">
      <div className={styles.label}>
        <span>사진 · 영상 {media.length}</span>
        <span>눌러서 크게 보기</span>
      </div>
      <ul className={styles.strip}>
        {media.map((item, index) => (
          <li key={index}>
            <button
              type="button"
              className={styles.thumb}
              aria-label={`${index + 1}번째 ${mediaLabel(item)} 크게 보기`}
            >
              <img src={item.thumb_url} alt="" loading="lazy" />
              {item.kind === 'video' && <span className={styles.play} data-play aria-hidden="true" />}
              {item.duration_seconds !== null && (
                <span className={styles.duration}>{duration(item.duration_seconds)}</span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

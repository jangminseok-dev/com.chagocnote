import type { Media } from '../lib/report'
import styles from './ReportView.module.css'

/** 모두 저장하는 버튼의 자리. */
export function SaveAllButton({}: { media: Media[] }) {
  return (
    <div data-section="save-all">
      <button type="button" className={styles.pill}>
        사진 · 영상 모두 저장
      </button>
    </div>
  )
}

import type { Media } from '../lib/report'
import styles from './ReportView.module.css'

/** 미디어 하나를 저장하는 버튼의 자리. */
export function SaveButton({}: { media: Media }) {
  return (
    <button type="button" className={styles.save} aria-label="저장">
      ↓
    </button>
  )
}

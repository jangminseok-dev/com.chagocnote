import type { Media } from '../lib/report'
import styles from './ReportView.module.css'

/** 미디어 하나 저장. 내려받기용 주소는 서명에 attachment 가 들어 있어 화면을 떠나지 않는다. */
export function SaveButton({ media }: { media: Media }) {
  return (
    <a className={styles.save} href={media.download_url} aria-label="저장">
      ↓
    </a>
  )
}

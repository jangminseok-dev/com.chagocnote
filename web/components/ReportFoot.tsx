import { koreanDate } from '../lib/format'
import styles from './ReportView.module.css'

/** 꼬리. 기간이 없는 알림장에는 기간 문구가 없다. */
export function ReportFoot({ expiresAt }: { expiresAt: string | null }) {
  return (
    <footer className={styles.foot} data-section="foot">
      {expiresAt !== null && <div>이 알림장은 {koreanDate(expiresAt)}까지 열려요</div>}
      <i>차곡노트</i>
    </footer>
  )
}

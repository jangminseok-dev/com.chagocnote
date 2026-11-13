import { koreanDate } from '../lib/format'
import styles from './ReportView.module.css'

/**
 * 꼬리. 기간이 없는 알림장에는 기간 문구가 없다.
 * claimAction 이 있으면(받은 링크로 연 알림장) 꼬리 앞에 로그인해 지난 기록을 잇는 버튼을 둔다.
 */
export function ReportFoot({ expiresAt, claimAction }: { expiresAt: string | null; claimAction?: string }) {
  return (
    <>
      {claimAction !== undefined && (
        <section className={styles.claim} data-section="claim">
          <form method="post" action={claimAction}>
            <button type="submit">로그인하고 지난 기록 보기</button>
          </form>
        </section>
      )}
      <footer className={styles.foot} data-section="foot">
        {expiresAt !== null && <div>이 알림장은 {koreanDate(expiresAt)}까지 열려요</div>}
        <i>차곡노트</i>
      </footer>
    </>
  )
}

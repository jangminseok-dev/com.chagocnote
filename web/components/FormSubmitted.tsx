import { koreanFullDate } from '../lib/format'
import styles from './ErrorScreen.module.css'

/** 낸 뒤의 화면. 낸 내용은 다시 보이지 않는다 — 매장 이름과 낸 날뿐이다. */
export function FormSubmitted({ shopName, submittedOn }: { shopName: string; submittedOn: string | null }) {
  return (
    <main className={styles.screen} data-section="submitted">
      <div className={styles.mark} aria-hidden="true">
        Thank you
      </div>
      <h1 className={styles.title}>보냈어요</h1>
      <p className={styles.text}>{shopName}에서 확인할게요.</p>
      {submittedOn !== null && <p className={styles.text}>{koreanFullDate(submittedOn)}에 보냈어요</p>}
    </main>
  )
}

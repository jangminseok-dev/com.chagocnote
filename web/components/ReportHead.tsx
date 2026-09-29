import { dayNumber, monthAndWeekday, reportTitle } from '../lib/format'
import styles from './ReportView.module.css'

type Props = { petName: string | null; visitDate: string; shopName?: string }

/** 머리·날짜·제목. 매장 이름은 매장 정보를 켰을 때만 온다. */
export function ReportHead({ petName, visitDate, shopName }: Props) {
  const [month, weekday] = monthAndWeekday(visitDate)
  return (
    <>
      <header className={styles.brand} data-section="head">
        <i className={styles.serif}>Grooming Note</i>
        {shopName !== undefined && <span>{shopName}</span>}
      </header>
      <div className={styles.date} data-section="date">
        <span className={styles.day}>{dayNumber(visitDate)}</span>
        <span className={styles.month}>
          {month}
          <br />
          {weekday}
        </span>
      </div>
      <h1 className={styles.title} data-section="title">
        {reportTitle(petName)}
      </h1>
    </>
  )
}

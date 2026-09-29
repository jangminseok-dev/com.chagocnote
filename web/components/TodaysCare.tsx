import { weight, won } from '../lib/format'
import type { Menu } from '../lib/report'
import styles from './ReportView.module.css'

type Props = { menus?: Menu[] | null; totalAmount?: number | null; weightKg?: number | null }

/** 오늘의 케어. 끈 항목(칸 없음)과 값이 없는 항목(null)의 줄은 없다. 줄이 하나도 없으면 구역도 없다. */
export function TodaysCare({ menus, totalAmount, weightKg }: Props) {
  const hasMenus = menus != null && menus.length > 0
  if (!hasMenus && totalAmount == null && weightKg == null) return null
  return (
    <section data-section="care">
      <div className={styles.label}>
        <i className={styles.serif}>Today&apos;s care</i>
        <span>오늘의 케어</span>
      </div>
      <ul className={`${styles.card} ${styles.rows}`}>
        {menus?.map((menu, index) => (
          <li key={index}>
            <span>{menu.name}</span>
            {menu.amount != null && <span className={styles.serif}>{won(menu.amount)}</span>}
          </li>
        ))}
        {totalAmount != null && (
          <li className={styles.sum}>
            <span>합계</span>
            <span className={styles.serif}>{won(totalAmount)}</span>
          </li>
        )}
        {weightKg != null && (
          <li>
            <span>몸무게</span>
            <span className={styles.serif}>{weight(weightKg)}</span>
          </li>
        )}
      </ul>
    </section>
  )
}

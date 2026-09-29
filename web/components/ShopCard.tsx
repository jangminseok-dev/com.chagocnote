import type { Shop } from '../lib/report'
import styles from './ReportView.module.css'

/** 매장 정보. 전화가 없으면 전화 버튼이 없다. */
export function ShopCard({ shop }: { shop: Shop }) {
  return (
    <section data-section="shop">
      <div className={styles.label}>
        <i className={styles.serif}>Shop</i>
      </div>
      <div className={`${styles.card} ${styles.shop}`}>
        <b>{shop.name}</b>
        {shop.phone !== null && <small>{shop.phone}</small>}
        {shop.address !== null && <small>{shop.address}</small>}
        {shop.phone !== null && (
          <a className={`${styles.pill} ${styles.light}`} href={`tel:${shop.phone}`}>
            매장에 전화하기
          </a>
        )}
      </div>
    </section>
  )
}

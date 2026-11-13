import type { Report } from '../lib/report'
import { CareNote } from './CareNote'
import { MediaGallery } from './MediaGallery'
import { ReportFoot } from './ReportFoot'
import { ReportHead } from './ReportHead'
import styles from './ReportView.module.css'
import { SaveAllButton } from './SaveAllButton'
import { ShopCard } from './ShopCard'
import { TodaysCare } from './TodaysCare'
import { ViewedSignal } from './ViewedSignal'

/**
 * 알림장 화면. 온 것만 그린다 — 매장이 끈 항목은 칸이 없고, 값이 없는 항목은 null 이다.
 * token 은 받은 링크로 열었을 때만 있다. 로그인한 보호자의 한 장에는 없고, 그때는 열람 신호와 로그인 버튼이 없다.
 */
export function ReportView({ report, token }: { report: Report; token?: string }) {
  const { media } = report
  return (
    <main className={styles.page}>
      <ReportHead petName={report.pet_name} visitDate={report.visit_date} shopName={report.shop?.name} />
      {media.length > 0 && <MediaGallery media={media} />}
      {report.care_note !== null && <CareNote text={report.care_note} />}
      <TodaysCare menus={report.menus} totalAmount={report.total_amount} weightKg={report.weight_kg} />
      {media.length > 0 && <SaveAllButton media={media} />}
      {report.shop && <ShopCard shop={report.shop} />}
      <ReportFoot expiresAt={report.expires_at} claimAction={token === undefined ? undefined : `/r/${token}/claim`} />
      {token !== undefined && <ViewedSignal token={token} />}
    </main>
  )
}

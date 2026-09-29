import type { Report } from '../lib/report'
import { CareNote } from './CareNote'
import { HeroMedia } from './HeroMedia'
import { MediaStrip } from './MediaStrip'
import { ReportFoot } from './ReportFoot'
import { ReportHead } from './ReportHead'
import styles from './ReportView.module.css'
import { SaveAllButton } from './SaveAllButton'
import { ShopCard } from './ShopCard'
import { TodaysCare } from './TodaysCare'

/** 알림장 화면. 온 것만 그린다 — 매장이 끈 항목은 칸이 없고, 값이 없는 항목은 null 이다. */
export function ReportView({ report }: { report: Report; token: string }) {
  const { media } = report
  return (
    <main className={styles.page}>
      <ReportHead petName={report.pet_name} visitDate={report.visit_date} shopName={report.shop?.name} />
      {media.length > 0 && <HeroMedia media={media[0]} index={0} total={media.length} />}
      {media.length > 1 && <MediaStrip media={media} />}
      {report.care_note !== null && <CareNote text={report.care_note} />}
      <TodaysCare menus={report.menus} totalAmount={report.total_amount} weightKg={report.weight_kg} />
      {media.length > 0 && <SaveAllButton media={media} />}
      {report.shop && <ShopCard shop={report.shop} />}
      <ReportFoot expiresAt={report.expires_at} />
    </main>
  )
}

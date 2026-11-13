import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { cache } from 'react'
import { ErrorScreen } from '../../../../components/ErrorScreen'
import styles from '../../../../components/Member.module.css'
import { ReportView } from '../../../../components/ReportView'
import { reportTitle } from '../../../../lib/format'
import { getGuardianReport } from '../../../../lib/guardian'
import { requireSession, screenFor } from '../../../../lib/me'
import { idFrom } from '../../../../lib/next-path'

type Props = { params: Promise<{ linkId: string; reportId: string }> }

// generateMetadata 와 본문이 같은 요청 안에서 부른다. cache 라 백엔드 조회는 한 번이다.
const getReport = cache(getGuardianReport)

async function load({ params }: Props) {
  const { linkId: rawLink, reportId: rawReport } = await params
  const linkId = idFrom(rawLink)
  const reportId = idFrom(rawReport)
  if (linkId === null || reportId === null) notFound()
  const here = `/me/${linkId}/${reportId}`
  const { accessToken } = await requireSession(here)
  return { linkId, here, result: await getReport(accessToken, linkId, reportId) }
}

export async function generateMetadata(props: Props): Promise<Metadata> {
  const { result } = await load(props)
  // 미리보기(og) 정보는 넣지 않는다 — 로그인한 사람만 보는 화면이다.
  return result.kind === 'ok' ? { title: reportTitle(result.report.pet_name) } : {}
}

/** 로그인한 보호자의 알림장 한 장. 받은 링크의 화면과 같되 열람 신호·로그인 버튼·기간 문구가 없다. */
export default async function GuardianReportPage(props: Props) {
  const { linkId, here, result } = await load(props)
  if (result.kind !== 'ok') return <ErrorScreen kind={screenFor(result, here)} />
  return (
    <>
      <nav className={styles.bar} data-section="back">
        <a className={styles.back} href={`/me/${linkId}`}>
          지난 알림장
        </a>
      </nav>
      <ReportView report={result.report} />
    </>
  )
}

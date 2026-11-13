import type { Metadata } from 'next'
import { headers } from 'next/headers'
import { notFound } from 'next/navigation'
import { ErrorScreen } from '../../../components/ErrorScreen'
import { ReportView } from '../../../components/ReportView'
import { clientIpFrom } from '../../../lib/client-ip'
import { devLogin } from '../../../lib/config'
import { koreanDate, reportTitle } from '../../../lib/format'
import { getReport } from '../../../lib/report'

type Props = { params: Promise<{ token: string }> }

// generateMetadata 와 본문이 같은 요청 안에서 부른다. getReport 는 React cache 라 백엔드 조회는 한 번이다.
async function load({ params }: Props) {
  const { token } = await params
  return { token, result: await getReport(token, clientIpFrom(await headers())) }
}

export async function generateMetadata(props: Props): Promise<Metadata> {
  const { result } = await load(props)
  // 오류 화면은 레이아웃의 제목("차곡노트 미용 알림장") 그대로이고 미리보기 그림이 없다.
  if (result.kind !== 'ok') return {}

  const { report } = result
  const title = reportTitle(report.pet_name)
  const date = koreanDate(report.visit_date)
  // og:url·canonical 은 넣지 않는다 — 토큰이 든 주소를 더 퍼뜨리지 않는다.
  return {
    title,
    openGraph: {
      type: 'website',
      title,
      description: report.shop ? `${date} · ${report.shop.name}` : date,
      images: [report.cover ?? (await defaultImage())],
    },
  }
}

/** 대표가 없을 때의 미리보기 그림. 미리보기 로봇이 받을 수 있게 요청의 주소로 절대 주소를 만든다. */
async function defaultImage() {
  const requestHeaders = await headers()
  const proto = requestHeaders.get('x-forwarded-proto') ?? 'https'
  return { url: `${proto}://${requestHeaders.get('host')}/og-default.png`, width: 1200, height: 630 }
}

export default async function ReportPage(props: Props) {
  const { token, result } = await load(props)
  if (result.kind === 'not_found') notFound()
  // 지금 로그인 수단은 개발용 하나다. 없으면 [로그인하고 지난 기록 보기]를 그리지 않는다.
  const login = devLogin()
  if (result.kind !== 'ok') return <ErrorScreen kind={result.kind} login={login} />
  return <ReportView report={result.report} token={token} login={login} />
}

import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { ErrorScreen } from '../../../components/ErrorScreen'
import { ReportList } from '../../../components/ReportList'
import { getReports } from '../../../lib/guardian'
import { requireSession, screenFor } from '../../../lib/me'
import { cursorFrom, idFrom } from '../../../lib/next-path'

export const metadata: Metadata = { title: '지난 알림장 — 차곡노트' }

type Props = {
  params: Promise<{ linkId: string }>
  searchParams: Promise<{ pet?: string | string[]; cursor?: string | string[] }>
}

const one = (value: string | string[] | undefined) => (typeof value === 'string' ? value : undefined)

/** 지난 알림장 — 최신순 한 쪽. ?pet= 이면 그 아이의 것만. */
export default async function ReportsPage({ params, searchParams }: Props) {
  const linkId = idFrom((await params).linkId)
  if (linkId === null) notFound()
  const query = await searchParams
  // 모양이 틀린 인자는 없는 것으로 친다.
  const petId = idFrom(one(query.pet))
  const cursor = cursorFrom(one(query.cursor))

  // 다시 로그인하면 첫 쪽으로 돌아온다(쪽 표시는 싣지 않는다).
  const here = petId === null ? `/me/${linkId}` : `/me/${linkId}?pet=${petId}`
  const { accessToken } = await requireSession(here)

  const result = await getReports(accessToken, linkId, { petId, cursor })
  if (result.kind !== 'ok') return <ErrorScreen kind={screenFor(result, here)} />
  return <ReportList linkId={linkId} petId={petId} page={result.page} />
}

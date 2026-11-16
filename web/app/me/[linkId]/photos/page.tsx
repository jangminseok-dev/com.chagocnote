import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { ErrorScreen } from '../../../../components/ErrorScreen'
import { PhotoArchive } from '../../../../components/PhotoArchive'
import { getMedia, getWeights } from '../../../../lib/guardian'
import { requireSession, screenFor } from '../../../../lib/me'
import { cursorFrom, idFrom } from '../../../../lib/next-path'

export const metadata: Metadata = { title: '사진 모아 보기 — 차곡노트' }

type Props = {
  params: Promise<{ linkId: string }>
  searchParams: Promise<Record<string, string | string[] | undefined>>
}

const one = (value: string | string[] | undefined) => (typeof value === 'string' ? value : undefined)
const yearFrom = (value: string | undefined) => (value !== undefined && /^(19[9]\d|20\d\d|2100)$/.test(value) ? Number(value) : null)
const phaseFrom = (value: string | undefined) => (value === 'after' || value === 'before' ? value : null)

/** 아이의 사진·영상 모아 보기(⑫). ?pet=&year=&phase=&cursor= — 모양이 틀린 인자는 없는 것으로 친다. */
export default async function PhotosPage({ params, searchParams }: Props) {
  const linkId = idFrom((await params).linkId)
  if (linkId === null) notFound()
  const query = await searchParams
  const petId = idFrom(one(query.pet))
  const year = yearFrom(one(query.year))
  const phase = phaseFrom(one(query.phase))
  const cursor = cursorFrom(one(query.cursor))
  // 다시 로그인하면 첫 쪽으로 돌아온다(쪽 표시는 싣지 않는다). 질의의 순서는 safeNext 가 받는 모양이다.
  const params_ = new URLSearchParams()
  if (petId !== null) params_.set('pet', String(petId))
  if (year !== null) params_.set('year', String(year))
  if (phase !== null) params_.set('phase', phase)
  const here = `/me/${linkId}/photos${params_.size > 0 ? `?${params_}` : ''}`
  const { accessToken } = await requireSession(here)
  const [media, weights] = await Promise.all([
    getMedia(accessToken, linkId, { petId, year, phase, cursor }),
    petId === null ? null : getWeights(accessToken, linkId, petId),
  ])
  if (media.kind !== 'ok') return <ErrorScreen kind={screenFor(media, here)} />
  return (
    <PhotoArchive
      linkId={linkId}
      petId={petId}
      filter={{ year, phase }}
      page={media.page}
      // 몸무게를 읽지 못하면 구역만 없다(본문이 아니다).
      weights={weights !== null && weights.kind === 'ok' ? weights.weights : null}
      openedAt={Date.now()}
    />
  )
}

import type { Metadata } from 'next'
import { ErrorScreen } from '../../components/ErrorScreen'
import { MyPets } from '../../components/MyPets'
import { getFamily, getLinks, getPets } from '../../lib/guardian'
import { requireSession, screenFor } from '../../lib/me'

export const metadata: Metadata = { title: '내 기록 — 차곡노트' }

type Props = { searchParams: Promise<{ notice?: string | string[] }> }

const HERE = '/me'

/** 내 기록 — 이어진 매장마다 알림장을 받은 적 있는 아이들. */
export default async function MePage({ searchParams }: Props) {
  const { accessToken } = await requireSession(HERE)

  const links = await getLinks(accessToken)
  if (links.kind !== 'ok') return <ErrorScreen kind={screenFor(links, HERE)} />

  const pets = await Promise.all(links.links.map((link) => getPets(accessToken, link.link_id)))
  // 기본 연결이고 매장이 가족을 허락했으면 함께 보는 가족(⑫). 읽지 못하면 그 구역만 없다(본문이 아니다).
  const families = await Promise.all(links.links.map((link) =>
    link.role !== 'family' && ((link.family_max ?? 0) > 0 || (link.family_count ?? 0) > 0)
      ? getFamily(accessToken, link.link_id) : null))
  const shops = []
  for (const [index, link] of links.links.entries()) {
    const result = pets[index]
    // 목록을 읽은 직후 끊긴 연결(404)은 빼고 그린다.
    if (result.kind === 'not_found') continue
    if (result.kind !== 'ok') return <ErrorScreen kind={screenFor(result, HERE)} />
    const family = families[index]
    shops.push({ link, pets: result.pets, family: family !== null && family.kind === 'ok' ? family.family : undefined })
  }

  const { notice } = await searchParams
  return <MyPets shops={shops} notice={notice === 'taken' || notice === 'invite' ? notice : null} />
}

import type { Metadata } from 'next'
import { ErrorScreen } from '../../components/ErrorScreen'
import { MyPets } from '../../components/MyPets'
import { getLinks, getPets } from '../../lib/guardian'
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
  const shops = []
  for (const [index, link] of links.links.entries()) {
    const result = pets[index]
    // 목록을 읽은 직후 끊긴 연결(404)은 빼고 그린다.
    if (result.kind === 'not_found') continue
    if (result.kind !== 'ok') return <ErrorScreen kind={screenFor(result, HERE)} />
    shops.push({ link, pets: result.pets })
  }

  const { notice } = await searchParams
  return <MyPets shops={shops} notice={notice === 'taken' ? 'taken' : null} />
}

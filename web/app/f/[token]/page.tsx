import type { Metadata } from 'next'
import { headers } from 'next/headers'
import { notFound } from 'next/navigation'
import { ErrorScreen } from '../../../components/ErrorScreen'
import { clientIpFrom } from '../../../lib/client-ip'
import { getForm } from '../../../lib/form'

type Props = { params: Promise<{ token: string }> }

const TITLE = '미용 동의서'

// generateMetadata 와 본문이 같은 요청 안에서 부른다. getForm 은 React cache 라 백엔드 조회는 한 번이다.
async function load({ params }: Props) {
  const { token } = await params
  return { token, result: await getForm(token, clientIpFrom(await headers())) }
}

export async function generateMetadata(props: Props): Promise<Metadata> {
  const { result } = await load(props)
  if (result.kind !== 'ok') return {}
  const requestHeaders = await headers()
  const proto = requestHeaders.get('x-forwarded-proto') ?? 'https'
  // 미리보기에는 매장 이름과 "미용 동의서"뿐이다 — 아이 이름·지병을 싣지 않는다. og:url·canonical 도 넣지 않는다.
  return {
    title: TITLE,
    openGraph: {
      type: 'website',
      title: TITLE,
      description: result.form.shop.name,
      images: [{ url: `${proto}://${requestHeaders.get('host')}/og-default.png`, width: 1200, height: 630 }],
    },
  }
}

export default async function FormPage(props: Props) {
  const { result } = await load(props)
  if (result.kind === 'not_found') notFound()
  if (result.kind !== 'ok') return <ErrorScreen kind={result.kind} what="form" />
  // 화면은 다음 작업에서 그린다.
  return <main>{result.form.shop.name}</main>
}

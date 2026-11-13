import type { Metadata } from 'next'
import { LoginScreen } from '../../components/LoginScreen'
import { devLogin } from '../../lib/config'
import { safeNext } from '../../lib/next-path'

export const metadata: Metadata = { title: '로그인 — 차곡노트' }

type Props = { searchParams: Promise<{ next?: string | string[]; error?: string | string[] }> }

/** 로그인. 세션이 있어도 다른 곳으로 보내지 않는다 — 끝난 세션으로 /me 와 서로 돌지 않게. */
export default async function LoginPage({ searchParams }: Props) {
  const { next, error } = await searchParams
  return <LoginScreen dev={devLogin()} next={safeNext(typeof next === 'string' ? next : null)} failed={error === '1'} />
}

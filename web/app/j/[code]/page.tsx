import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import styles from '../../../components/Member.module.css'
import { devLogin } from '../../../lib/config'
import { isTokenShaped } from '../../../lib/token'

// 미리보기(og) 정보는 넣지 않는다 — 초대 주소가 어디로 퍼지든 무엇의 초대인지 드러나지 않게.
export const metadata: Metadata = { title: '함께 보기 — 차곡노트' }

/**
 * 가족 초대를 받은 화면(⑫ 설계 5.3). 백엔드를 부르지 않는다 — 코드의 모양만 보고 아니면 404. 열어 본 것만으로는 아무것도
 * 드러나지 않는다. 로그인할 수단이 없으면 버튼이 없다.
 */
export default async function JoinPage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params
  if (!isTokenShaped(code)) notFound()
  return (
    <main className={styles.page} data-section="join">
      <div className={styles.mark} aria-hidden="true">
        Together
      </div>
      <h1 className={styles.title}>가족의 미용 기록을 함께 볼 수 있어요</h1>
      <p className={styles.text}>로그인하면 초대한 가족과 같은 알림장·사진을 볼 수 있어요. 초대는 하루 동안, 한 사람만 쓸 수 있어요.</p>
      {devLogin() && (
        <form method="post" action={`/j/${code}/join`}>
          <button className={styles.primary} type="submit">
            로그인하고 함께 보기
          </button>
        </form>
      )}
    </main>
  )
}

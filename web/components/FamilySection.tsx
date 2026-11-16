import { koreanDate } from '../lib/format'
import type { FamilyMember } from '../lib/guardian'
import { FamilyInviteButton } from './FamilyInviteButton'
import styles from './Member.module.css'

/**
 * 함께 보는 가족(⑫ 설계 3.5) — 기본 보호자에게만. 한 사람에 한 줄(`가족 N · 이은 날`)과 [끊기], [가족 모두 끊기],
 * 초대 단추와 한 줄 설명. 이름·계정은 없다 — 이은 날이 단서다(모르는 날에 이어진 줄이면 그 줄만 끊고 새 초대를 보낸다).
 * 매장이 가족 수를 0 으로 정했으면 그리지 않는다.
 */
export function FamilySection({ linkId, members, count, max }: { linkId: number; members: FamilyMember[]; count: number; max: number }) {
  if (max <= 0 && members.length === 0) return null
  const unseen = members.filter((member) => member.unseen)
  return (
    <section className={styles.family} data-section="family">
      <h3>함께 보는 가족</h3>
      {unseen.map((member) => (
        <p key={member.family_id} className={styles.alert} role="status">
          {koreanDate(member.linked_at.slice(0, 10))}에 가족 한 명이 함께 보기 시작했어요
        </p>
      ))}
      {members.length > 0 && (
        <ul>
          {members.map((member, index) => (
            <li key={member.family_id}>
              가족 {index + 1} · {koreanDate(member.linked_at.slice(0, 10))}에 이음
              <form method="post" action={`/me/${linkId}/family-unlink`}>
                <input type="hidden" name="family_id" value={member.family_id} />
                <button className={styles.plain} type="submit">
                  끊기
                </button>
              </form>
            </li>
          ))}
        </ul>
      )}
      {members.length > 0 && (
        <form method="post" action={`/me/${linkId}/family-unlink`}>
          <button className={styles.plain} type="submit">
            가족 모두 끊기
          </button>
        </form>
      )}
      {Math.max(count, members.length) < max ? (
        <FamilyInviteButton linkId={linkId} />
      ) : (
        <p className={styles.text}>함께 볼 수 있는 가족이 다 찼어요(최대 {max}명)</p>
      )}
      <p className={styles.text}>초대를 받은 가족이 로그인하면 같은 기록을 함께 봐요. 초대는 하루 동안, 한 사람만 쓸 수 있어요.</p>
    </section>
  )
}

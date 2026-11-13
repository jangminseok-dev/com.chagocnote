import type { GuardianLink, GuardianPet } from '../lib/guardian'
import { koreanFullDate } from '../lib/format'
import styles from './Member.module.css'
import { UnlinkButton } from './UnlinkButton'

/** 연결 하나 — 매장과 그 매장에서 알림장을 받은 적 있는 아이들. */
export type ShopPets = { link: GuardianLink; pets: GuardianPet[] }

/** 내 기록. 매장별로 아이들을 보여 준다. notice 는 방금 잇기가 되지 않은 까닭이다. */
export function MyPets({ shops, notice }: { shops: ShopPets[]; notice: 'taken' | null }) {
  return (
    <main className={styles.page}>
      <header data-section="me-head">
        <div className={styles.mark} aria-hidden="true">
          My notes
        </div>
        <h1 className={styles.title}>내 기록</h1>
      </header>
      {notice === 'taken' && (
        <p className={styles.alert} role="status" data-section="notice">
          이 알림장은 이미 다른 계정에 이어져 있어요. 매장에 문의해 주세요.
        </p>
      )}
      {shops.length === 0 && (
        <section className={styles.empty} data-section="empty">
          <h2>아직 이어진 기록이 없어요</h2>
          <p className={styles.text}>
            매장에서 받은 미용 알림장을 열고 [로그인하고 지난 기록 보기]를 눌러 주세요. 알림장이 닫혔다면 매장에 다시 보내
            달라고 요청해 주세요.
          </p>
        </section>
      )}
      {shops.map(({ link, pets }) => (
        <section className={styles.shop} key={link.link_id} data-section="shop">
          <h2>{link.shop_name}</h2>
          <small>{koreanFullDate(link.linked_at)}부터</small>
          {pets.length === 0 ? (
            <p className={styles.text}>아직 받은 알림장이 없어요</p>
          ) : (
            <ul className={styles.pets}>
              {pets.map((pet) => (
                <li key={pet.pet_id}>
                  <a href={`/me/${link.link_id}?pet=${pet.pet_id}`}>{pet.name ?? '우리 아이'}</a>
                </li>
              ))}
            </ul>
          )}
          <div className={styles.row}>
            <a href={`/me/${link.link_id}`}>전체 기록 보기</a>
            <UnlinkButton linkId={link.link_id} shopName={link.shop_name} />
          </div>
        </section>
      ))}
      <footer className={styles.logout} data-section="logout">
        <form method="post" action="/logout">
          <button className={styles.plain} type="submit">
            로그아웃
          </button>
        </form>
      </footer>
    </main>
  )
}

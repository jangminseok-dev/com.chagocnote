import { koreanFullDate } from '../lib/format'
import { CONSENT_PART_TITLES, CONSENT_PARTS, type OpenForm } from '../lib/form'
import styles from './Consent.module.css'
import { ConsentSubmit } from './ConsentSubmit'

/**
 * 미용 동의서 화면. 온 것만 그린다 — 문안은 백엔드가 아이의 지금 사실로 조립한 것이다.
 * 아이의 이름과 지병의 이름은 문안 밖에서 늘 따로 그린다(매장이 글을 고쳐도 무엇에 동의하는지가 빠지지 않는다).
 */
export function ConsentView({ form, token }: { form: OpenForm; token: string }) {
  const family = form.pets.length > 1
  const parts = CONSENT_PARTS.filter((part) => form.texts[part] !== undefined)
  return (
    <main className={styles.page}>
      <header className={styles.brand} data-section="head">
        <i className={styles.serif}>Consent</i>
        <span>{form.shop.name}</span>
      </header>
      <h1 className={styles.title}>미용 동의서</h1>
      {form.previous_consent_on !== null && (
        <p className={styles.partial} data-section="partial">
          지난번({koreanFullDate(form.previous_consent_on)})에 동의하신 내용에 더해 바뀐 부분만 확인해 주세요
        </p>
      )}
      <section className={styles.card} data-section="pets">
        <ul>
          {form.pets.map((pet, index) => (
            <li key={index} className={styles.pet}>
              <b>{pet.name}</b>
              {pet.conditions.length > 0 && <small>알려 주신 지병: {pet.conditions.join(' · ')}</small>}
            </li>
          ))}
        </ul>
      </section>
      {parts.map((part) => (
        <section key={part} className={styles.part} data-section="part">
          <h2>{CONSENT_PART_TITLES[part]}</h2>
          {family && (
            <div className={styles.whom}>
              해당: {form.pets.filter((pet) => pet.parts.includes(part)).map((pet) => pet.name).join(' · ')}
            </div>
          )}
          {(form.texts[part]?.body ?? '')
            .split('\n')
            .filter((line) => line.trim() !== '')
            .map((line, index) => (
              <p key={index}>{line}</p>
            ))}
        </section>
      ))}
      <section data-section="sign">
        <ConsentSubmit token={token} digest={form.doc_digest} shopName={form.shop.name} />
      </section>
      <footer className={styles.foot} data-section="foot">
        <i>차곡노트</i>
      </footer>
    </main>
  )
}

import type { OpenIntake } from '../lib/form'
import consent from './Consent.module.css'
import { IntakeForm } from './IntakeForm'

/**
 * 문진표 화면(⑪-C). 온 구성만 그린다 — 매장이 켠 칸과 더한 질문. 지금 값(품종·몸무게·지병)은 화면에 없다:
 * 이미 있는 아이의 정보를 다시 받을 때도 아이 이름뿐이다(링크를 주운 사람이 본다).
 */
export function IntakeView({ form, token }: { form: OpenIntake; token: string }) {
  return (
    <main className={consent.page}>
      <header className={consent.brand} data-section="head">
        <i className={consent.serif}>Intake</i>
        <span>{form.shop.name}</span>
      </header>
      <h1 className={consent.title}>{form.mode === 'update' && form.pet_name !== null ? `${form.pet_name}의 문진표` : '문진표'}</h1>
      {/* 다시 읽을 때(다음 아이) 폼의 상태는 남긴다 — 방금 낸 아이를 알려 주는 글이 여기 산다. */}
      <IntakeForm form={form} token={token} />
      <footer className={consent.foot} data-section="foot">
        <i>차곡노트</i>
      </footer>
    </main>
  )
}

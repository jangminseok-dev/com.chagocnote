'use client'

import { useRouter } from 'next/navigation'
import { type FormEvent, useEffect, useId, useRef, useState } from 'react'
import { CONSENT_PART_TITLES, type OpenIntake } from '../lib/form'
import { BREEDS, bodyOf, consentPartsOf, emptyDraft, type IntakeDraft, localDay, problemOf } from '../lib/intake'
import styles from './Intake.module.css'
import { SignaturePad } from './SignaturePad'

const NOTICE_CHECK = '적은 내용을 다시 확인해 주세요'
const NOTICE_LATER = '잠시 후 다시 보내 주세요'
const NOTICE_CHANGED = '내용이 바뀌었어요. 다시 읽어 주세요'
const OTHER = 'other'

type ChoiceProps<T extends string> = {
  label: string
  options: [T, string][]
  value: T | ''
  onPick: (value: T) => void
  field: string
}

/** 하나를 고르는 칩 묶음. 고른 칩을 다시 눌러도 풀리지 않는다 — 다른 칩을 누른다. */
function Choice<T extends string>({ label, options, value, onPick, field }: ChoiceProps<T>) {
  return (
    <div className={styles.group} role="group" aria-label={label} data-field={field}>
      <div className={styles.label}>{label}</div>
      <div className={styles.chips}>
        {options.map(([option, text]) => (
          <button key={option} type="button" className={styles.chip} aria-pressed={value === option} onClick={() => onPick(option)}>
            {text}
          </button>
        ))}
      </div>
    </div>
  )
}

/**
 * 문진표를 적는 폼(⑪-C). 고르는 칸이 대부분이고, 꼭 글자를 쳐야 하는 칸은 보호자 이름·번호·아이 이름뿐이다
 * (품종은 목록에서 고르면 치지 않는다). 온 구성만 그린다 — 매장이 끈 칸은 없고, 다시 받기는 전부 선택이다.
 * 보호자의 브라우저는 웹 자신의 경로에만 보낸다. 적은 것을 기록에 남기지 않는다.
 */
export function IntakeForm({ form, token }: { form: OpenIntake; token: string }) {
  const router = useRouter()
  const id = useId()
  const formRef = useRef<HTMLFormElement>(null)
  const statusRef = useRef<HTMLParagraphElement>(null)
  const [draft, setDraft] = useState<IntakeDraft>(emptyDraft)
  const [customBreed, setCustomBreed] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [bad, setBad] = useState<string | null>(null) // 걸린 칸 — 표시하고 포커스를 옮긴다
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState<string | null>(null) // 방금 낸 아이의 이름 — 다음 아이를 적을 때 알려 준다
  const [done, setDone] = useState(false)
  // 끝의 동의서(⑪-C1b) — 서명하는 분의 이름은 고치기 전까지 보호자 이름을 따라간다. resetKey 가 바뀌면 서명 칸을 비운다.
  const [signerEdited, setSignerEdited] = useState(false)
  const [resetKey, setResetKey] = useState(0)
  // 스크립트가 오기 전에는 버튼을 잠근다 — 그때 누르면 브라우저가 폼을 그대로 내, 적은 것이 주소에 실린다.
  const [ready, setReady] = useState(false)

  useEffect(() => setReady(true), [])
  useEffect(() => {
    if (done || sent !== null) statusRef.current?.focus()
  }, [done, sent])

  const update = form.mode === 'update'
  const shown = (code: string) => form.fields.includes(code)
  const set = (change: Partial<IntakeDraft>) => {
    setDraft((now) => ({ ...now, ...change }))
    setNotice(null)
    setBad(null)
  }
  const breeds = draft.species === '' ? [] : BREEDS[draft.species]
  // 다른 아이를 이어 적을 수 있나 — 다시 받기는 한 번뿐이고, 한 링크에 열 마리까지다.
  const more = !update && form.answered < 9
  /** 걸린 칸의 표시. */
  const invalid = (field: string) => (bad === field ? { 'aria-invalid': true as const } : {})

  const consentParts = consentPartsOf(form, draft)
  const shownConditions = draft.conditions.map((c) =>
    c.code === OTHER && c.customLabel.trim() !== '' ? c.customLabel.trim() : (form.condition_types.find((t) => t.code === c.code)?.label ?? c.code))
  /** 서명을 다시 받는다 — 서명 칸과 동의 체크를 비운다. 적은 답과 이름은 남는다. */
  const resetSignature = () => {
    setDraft((now) => ({ ...now, signature: null, consentAgreed: false }))
    setResetKey((key) => key + 1)
  }

  const toggleCondition = (code: string) => {
    const picked = draft.conditions.some((c) => c.code === code)
    set({
      noConditions: false,
      conditions: picked ? draft.conditions.filter((c) => c.code !== code) : [...draft.conditions, { code, customLabel: '', note: '' }],
    })
  }
  const setCondition = (code: string, change: { customLabel?: string; note?: string }) =>
    set({ conditions: draft.conditions.map((c) => (c.code === code ? { ...c, ...change } : c)) })

  const send = async (more: boolean) => {
    if (sending) return
    const problem = problemOf(form, draft)
    if (problem !== null) {
      setNotice(problem.message)
      setBad(problem.field)
      // 그 칸으로 올라가 포커스를 준다. 안내 글은 화면 아래에 붙어 따라온다(.notice 가 sticky 다).
      const field = formRef.current?.querySelector<HTMLElement>(`[data-field="${problem.field}"]`)
      field?.scrollIntoView?.({ block: 'center' })
      const target = field?.matches('input, select, textarea, button') ? field : field?.querySelector<HTMLElement>('input, select, textarea, button')
      target?.focus({ preventScroll: true })
      return
    }
    setSending(true)
    setNotice(null)
    let status: number
    try {
      const res = await fetch(`/f/${token}/intake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bodyOf(form, draft, !more)),
      })
      status = res.status
    } catch {
      status = 503
    }
    setSending(false)
    if (status === 204) {
      if (more) {
        // 다음 아이를 적는다 — 아이의 칸만 비운다. 다시 읽으면 보호자 칸이 사라진다(둘째부터는 묻지 않는다).
        setSent(draft.petName.trim())
        // 서명하는 분은 같은 보호자다 — 이름은 남기고 서명은 아이마다 새로 받는다.
        setDraft({ ...emptyDraft(), signerName: draft.signerName })
        setResetKey((key) => key + 1)
        setCustomBreed(false)
      } else {
        setDone(true)
      }
      router.refresh()
    } else if (status === 409) {
      // 연 뒤 매장이 동의서의 글이나 기준을 바꿨다 — 새 글을 읽고 다시 서명한다. 적은 답은 남긴다.
      setNotice(NOTICE_CHANGED)
      resetSignature()
      router.refresh()
    } else if (status === 410 || status === 404) {
      // 그 사이 닫혔거나 끊겼다 — 오류 글이 아니라 다시 읽은 화면(보냈어요·닫힘)이 말한다.
      router.refresh()
    } else if (status === 413 || status === 422) {
      // 낡은 화면일 수 있다(매장이 그 사이 칸을 켜거나 꼭 답할 질문을 더했다) — 다시 읽어 새 구성을 그린다. 적은 것은 남는다.
      setNotice(NOTICE_CHECK)
      router.refresh()
    } else {
      setNotice(NOTICE_LATER)
    }
  }

  if (done) {
    return (
      <p ref={statusRef} className={styles.done} role="status" tabIndex={-1}>
        보냈어요. {form.shop.name}에서 확인할게요.
      </p>
    )
  }

  return (
    // method 는 스크립트 없이 나갈 때를 위한 것이다 — GET 이면 칸의 값이 주소에 실린다.
    <form ref={formRef} className={styles.form} method="post" noValidate data-bad={bad ?? undefined}
      onSubmit={(event: FormEvent) => { event.preventDefault(); void send(false) }}
      // 글자 칸의 엔터는 보내지 않는다 — [보내기]는 링크를 닫는다. 버튼으로만 보낸다.
      onKeyDown={(event) => { if (event.key === 'Enter' && event.target instanceof HTMLInputElement) event.preventDefault() }}>
      <noscript>
        <p className={styles.notice}>문진표를 적으려면 자바스크립트를 켜 주세요</p>
      </noscript>
      {sent !== null && (
        <p ref={statusRef} className={styles.sent} role="status" tabIndex={-1}>
          {sent}의 문진표를 보냈어요. 다음 아이를 적어 주세요.
        </p>
      )}
      {update && <p className={styles.lead}>바뀐 것만 적어 주세요. 적지 않은 것은 그대로 둘게요.</p>}

      {form.guardian_needed && (
        <section className={styles.section} data-section="guardian">
          <h2>보호자</h2>
          <label className={styles.label} htmlFor={`${id}-gn`}>보호자 이름</label>
          <input id={`${id}-gn`} className={styles.input} type="text" name="guardian_name" data-field="guardianName" data-required-text="true" {...invalid('guardianName')}
            value={draft.guardianName} maxLength={50} autoComplete="name"
            onChange={(e) => set({ guardianName: e.target.value, ...(signerEdited ? {} : { signerName: e.target.value }) })} />
          <label className={styles.label} htmlFor={`${id}-gp`}>전화번호</label>
          <input id={`${id}-gp`} className={styles.input} type="tel" name="guardian_phone" data-field="guardianPhone" data-required-text="true" {...invalid('guardianPhone')}
            value={draft.guardianPhone} maxLength={20} inputMode="tel" autoComplete="tel" onChange={(e) => set({ guardianPhone: e.target.value })} />
        </section>
      )}

      <section className={styles.section} data-section="pet">
        <h2>아이</h2>
        <label className={styles.label} htmlFor={`${id}-pn`}>아이 이름</label>
        <input id={`${id}-pn`} className={styles.input} type="text" name="pet_name" data-field="petName" data-required-text={update ? undefined : 'true'} {...invalid('petName')}
          value={draft.petName} maxLength={50} placeholder={update ? (form.pet_name ?? '') : undefined} onChange={(e) => set({ petName: e.target.value })} />
        {shown('species') && (
          <Choice label="종" field="species" options={[['dog', '강아지'], ['cat', '고양이']]} value={draft.species}
            onPick={(species) => { set({ species, breed: '' }); setCustomBreed(false) }} />
        )}
        {shown('breed') && (
          <div className={styles.group} data-field="breed">
            <div className={styles.label}>품종</div>
            {draft.species === '' && !shown('species') ? null : draft.species === '' ? (
              <p className={styles.hint}>강아지인지 고양이인지 먼저 골라 주세요</p>
            ) : (
              <div className={styles.chips}>
                {breeds.map((breed) => (
                  <button key={breed} type="button" className={styles.chip} aria-pressed={!customBreed && draft.breed === breed}
                    onClick={() => { set({ breed }); setCustomBreed(false) }}>
                    {breed}
                  </button>
                ))}
                <button type="button" className={styles.chip} aria-pressed={customBreed} onClick={() => { set({ breed: '' }); setCustomBreed(true) }}>
                  직접 적기
                </button>
              </div>
            )}
            {(customBreed || !shown('species')) && (
              <input className={styles.input} type="text" name="breed" aria-label="품종" value={draft.breed} maxLength={50}
                onChange={(e) => set({ breed: e.target.value })} />
            )}
          </div>
        )}
        {shown('sex') && (
          <Choice label="성별" field="sex" options={[['female', '여아'], ['male', '남아']]} value={draft.sex} onPick={(sex) => set({ sex })} />
        )}
        {shown('neutered') && (
          <Choice label="중성화" field="neutered" options={[['yes', '했어요'], ['no', '안 했어요']]} value={draft.neutered} onPick={(neutered) => set({ neutered })} />
        )}
        {shown('birth') && (
          <div className={styles.group} data-field="birth">
            <Choice label="나이" field="birth-kind" options={[['date', '생일을 알아요'], ['year', '태어난 해만 알아요'], ['unknown', '몰라요']]}
              value={draft.birthKind} onPick={(birthKind) => set({ birthKind })} />
            {draft.birthKind === 'date' && (
              <input className={styles.input} type="date" name="birth_date" aria-label="생일" value={draft.birthDate}
                min="1990-01-01" max={localDay(new Date())} onChange={(e) => set({ birthDate: e.target.value })} />
            )}
            {draft.birthKind === 'year' && (
              <select className={styles.input} name="birth_year" aria-label="태어난 해" value={draft.birthYear} onChange={(e) => set({ birthYear: e.target.value })}>
                <option value="">골라 주세요</option>
                {Array.from({ length: 30 }, (_, n) => new Date().getFullYear() - n).map((year) => (
                  <option key={year} value={year}>{year}년</option>
                ))}
              </select>
            )}
          </div>
        )}
        {shown('weight') && (
          <div className={styles.group} data-field="weight">
            <label className={styles.label} htmlFor={`${id}-w`}>몸무게(kg)</label>
            <div className={styles.row}>
              <input id={`${id}-w`} className={styles.input} type="text" name="weight_kg" inputMode="decimal" value={draft.weight} maxLength={5}
                disabled={draft.weightUnknown} onChange={(e) => set({ weight: e.target.value })} />
              <button type="button" className={styles.chip} aria-pressed={draft.weightUnknown}
                onClick={() => set({ weightUnknown: !draft.weightUnknown, weight: '' })}>
                모르겠어요
              </button>
            </div>
          </div>
        )}
      </section>

      <section className={styles.section} data-section="health">
        <h2>건강</h2>
        <div className={styles.group} role="group" aria-label="지병" data-field="conditions">
          <div className={styles.label}>앓고 있는 병이 있나요?</div>
          <div className={styles.chips}>
            <button type="button" className={styles.chip} aria-pressed={draft.noConditions} onClick={() => set({ noConditions: true, conditions: [] })}>
              없어요
            </button>
            {form.condition_types.map((type) => (
              <button key={type.code} type="button" className={styles.chip} aria-pressed={draft.conditions.some((c) => c.code === type.code)}
                onClick={() => toggleCondition(type.code)}>
                {type.label}
              </button>
            ))}
          </div>
          {draft.conditions.map((picked) => {
            const label = form.condition_types.find((type) => type.code === picked.code)?.label ?? picked.code
            return (
              <div key={picked.code} className={styles.detail}>
                {picked.code === OTHER && (
                  <input className={styles.input} type="text" aria-label={`${label} — 어떤 지병인가요`} placeholder="어떤 지병인가요" maxLength={30}
                    value={picked.customLabel} onChange={(e) => setCondition(picked.code, { customLabel: e.target.value })} />
                )}
                <input className={styles.input} type="text" aria-label={`${label} — 알려 주실 것`} placeholder={`${label} — 알려 주실 것 (예: 약 복용 중)`} maxLength={100}
                  value={picked.note} onChange={(e) => setCondition(picked.code, { note: e.target.value })} />
              </div>
            )
          })}
        </div>
      </section>

      {(shown('dislikes') || shown('style') || form.questions.length > 0) && (
        <section className={styles.section} data-section="more">
          <h2>미용할 때 알아 둘 것</h2>
          {shown('dislikes') && (
            <>
              <label className={styles.label} htmlFor={`${id}-d`}>싫어하는 것·조심할 것 <small>(예: 발 만지기, 드라이기 소리)</small></label>
              <textarea id={`${id}-d`} className={styles.area} name="dislikes" rows={2} maxLength={200} value={draft.dislikes} onChange={(e) => set({ dislikes: e.target.value })} />
            </>
          )}
          {shown('style') && (
            <>
              <label className={styles.label} htmlFor={`${id}-s`}>원하는 스타일</label>
              <textarea id={`${id}-s`} className={styles.area} name="style" rows={2} maxLength={200} value={draft.style} onChange={(e) => set({ style: e.target.value })} />
            </>
          )}
          {form.questions.map((question) => (
            <div key={question.question_id} data-field={`extra-${question.question_id}`}>
              <label className={styles.label} htmlFor={`${id}-q${question.question_id}`}>
                {question.label}{question.required && <small> (꼭 답해 주세요)</small>}
              </label>
              <input id={`${id}-q${question.question_id}`} className={styles.input} type="text" maxLength={200}
                value={draft.extras[question.question_id] ?? ''}
                onChange={(e) => set({ extras: { ...draft.extras, [question.question_id]: e.target.value } })} />
            </div>
          ))}
        </section>
      )}

      {consentParts.length > 0 && (
        // 문진표 끝의 동의서(⑪-C1b) — 적은 답으로 보아 노령이거나 지병이 있으면(매장이 모든 아이에게를 켰으면 늘) 나타난다.
        <section className={styles.section} data-section="consent">
          <h2>미용 동의서</h2>
          <p className={styles.hint}>미용 전에 아래 내용을 읽고 서명해 주세요.</p>
          {shownConditions.length > 0 && <p className={styles.facts}>알려 주신 지병: {shownConditions.join(' · ')}</p>}
          {consentParts.map((part) => (
            <div key={part} className={styles.part} data-part={part}>
              <h3>{CONSENT_PART_TITLES[part]}</h3>
              {(form.consent.texts[part]?.body ?? '')
                .split('\n')
                .filter((text) => text.trim() !== '')
                .map((text, index) => (
                  <p key={index}>{text}</p>
                ))}
            </div>
          ))}
          <label className={styles.label} htmlFor={`${id}-signer`}>서명하는 분의 이름</label>
          <input id={`${id}-signer`} className={styles.input} type="text" name="signer_name" data-field="signerName" {...invalid('signerName')}
            value={draft.signerName} maxLength={50} autoComplete="name"
            onChange={(e) => { setSignerEdited(true); set({ signerName: e.target.value }) }} />
          <div className={styles.label}>서명</div>
          <div data-field="signature">
            <SignaturePad resetKey={resetKey} onChange={(png) => set({ signature: png })} />
          </div>
          <div className={styles.agree} data-field="consentAgreed">
            <input id={`${id}-consent`} type="checkbox" checked={draft.consentAgreed} onChange={(e) => set({ consentAgreed: e.target.checked })} />
            <label htmlFor={`${id}-consent`}>위 내용을 읽었고 동의해요</label>
          </div>
        </section>
      )}

      <section className={styles.privacy} data-section="privacy" data-testid="privacy">
        <h2>개인정보 수집·이용 안내</h2>
        <ul>
          <li>받는 것: 보호자 이름·전화번호, 아이의 이름·품종·나이·몸무게·건강 상태와 적어 주신 글</li>
          <li>쓰는 곳: {form.shop.name}의 미용 예약과 안전한 미용</li>
          <li>지우는 때: {form.shop.name}에서 확인해 등록하기 전에는 {form.keep_days}일 뒤에 지워요. 등록한 뒤에는 매장에 지워 달라고 하실 수 있어요</li>
        </ul>
        <div className={styles.agree} data-field="agreed">
          <input id={`${id}-agree`} type="checkbox" checked={draft.agreed} onChange={(e) => set({ agreed: e.target.checked })} />
          <label htmlFor={`${id}-agree`}>개인정보 수집·이용에 동의해요</label>
        </div>
      </section>

      {notice !== null && (
        <p className={styles.notice} role="alert">
          {notice}
        </p>
      )}
      {more && <p className={styles.closing}>보내면 이 링크는 닫혀요. 아이가 더 있으면 아래 버튼을 눌러 주세요.</p>}
      <button className={styles.send} type="submit" disabled={!ready || sending}>
        {sending ? '보내는 중…' : '보내기'}
      </button>
      {more && (
        <button className={styles.more} type="button" disabled={!ready || sending} onClick={() => void send(true)}>
          보내고 다른 아이도 적기
        </button>
      )}
    </form>
  )
}

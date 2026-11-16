'use client'

import { useRouter } from 'next/navigation'
import { type FormEvent, useId, useState } from 'react'
import styles from './Consent.module.css'
import { SignaturePad } from './SignaturePad'

const NOTICE_CHANGED = '내용이 바뀌었어요. 다시 읽어 주세요'
const NOTICE_SIMPLER = '서명을 조금 간단하게 다시 적어 주세요'
const NOTICE_LATER = '잠시 후 다시 보내 주세요'

/**
 * 이름·서명·동의 체크와 보내기. 보호자의 브라우저는 웹 자신의 경로에만 보낸다 — 웹 서버가 백엔드로 넘긴다.
 * digest 는 보호자가 읽은 문서의 지문이다. 낼 때 그대로 돌려보내, 읽은 뒤 내용이 바뀌었으면 받지 않게 한다.
 */
export function ConsentSubmit({ token, digest }: { token: string; digest: string }) {
  const router = useRouter()
  const nameId = useId()
  const agreeId = useId()
  const [name, setName] = useState('')
  const [signature, setSignature] = useState<string | null>(null)
  const [agreed, setAgreed] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const [resetKey, setResetKey] = useState(0)

  /** 빠진 것. 없으면 null — 있으면 백엔드를 부르지 않는다. */
  const missing = (): string | null => {
    if (name.trim() === '') return '이름을 적어 주세요'
    if (signature === null) return '서명해 주세요'
    if (!agreed) return '동의에 체크해 주세요'
    return null
  }

  const send = async (event: FormEvent) => {
    event.preventDefault()
    if (sending) return
    const lacking = missing()
    if (lacking !== null) {
      setNotice(lacking)
      return
    }
    setSending(true)
    setNotice(null)
    let status: number
    try {
      const res = await fetch(`/f/${token}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_digest: digest, signer_name: name.trim(), signature_png: signature }),
      })
      status = res.status
    } catch {
      status = 503
    }
    setSending(false)
    if (status === 204 || status === 410 || status === 404) {
      // 보냈어요(또는 그 사이 닫힌) 화면으로 바뀐다. 410 은 이미 낸 것이다 — 오류로 보이지 않는다.
      router.refresh()
    } else if (status === 409) {
      // 읽은 뒤 내용이 바뀌었다 — 새 문안을 읽고 다시 서명한다. 적은 이름은 남긴다.
      setNotice(NOTICE_CHANGED)
      setSignature(null)
      setAgreed(false)
      setResetKey((key) => key + 1)
      router.refresh()
    } else if (status === 413 || status === 422) {
      setNotice(NOTICE_SIMPLER)
    } else {
      setNotice(NOTICE_LATER)
    }
  }

  return (
    <form className={styles.sign} onSubmit={send} noValidate>
      <noscript>
        <p className={styles.notice}>서명하려면 자바스크립트를 켜 주세요</p>
      </noscript>
      <label className={styles.field} htmlFor={nameId}>
        이름
      </label>
      <input
        id={nameId}
        className={styles.input}
        type="text"
        name="signer_name"
        value={name}
        maxLength={50}
        autoComplete="name"
        onChange={(event) => setName(event.target.value)}
      />
      <div className={styles.field}>서명</div>
      <SignaturePad onChange={setSignature} resetKey={resetKey} />
      <div className={styles.agree}>
        <input id={agreeId} type="checkbox" checked={agreed} onChange={(event) => setAgreed(event.target.checked)} />
        <label htmlFor={agreeId}>위 내용을 읽었고 동의합니다</label>
      </div>
      {notice !== null && (
        <p className={styles.notice} role="alert">
          {notice}
        </p>
      )}
      <button className={styles.send} type="submit" disabled={sending}>
        {sending ? '보내는 중…' : '동의하고 보내기'}
      </button>
    </form>
  )
}

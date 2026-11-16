'use client'

import { useRouter } from 'next/navigation'
import { type FormEvent, useEffect, useId, useRef, useState } from 'react'
import styles from './Consent.module.css'
import { SignaturePad } from './SignaturePad'

const NOTICE_CHANGED = '내용이 바뀌었어요. 다시 읽어 주세요'
const NOTICE_SIMPLER = '서명을 조금 간단하게 다시 적어 주세요'
const NOTICE_LATER = '잠시 후 다시 보내 주세요'

type Props = { token: string; digest: string; shopName: string }

/**
 * 이름·서명·동의 체크와 보내기. 보호자의 브라우저는 웹 자신의 경로에만 보낸다 — 웹 서버가 백엔드로 넘긴다.
 * digest 는 보호자가 읽은 문서의 지문이다. 낼 때 그대로 돌려보내, 읽은 뒤 내용이 바뀌었으면 받지 않게 한다.
 */
export function ConsentSubmit({ token, digest, shopName }: Props) {
  const router = useRouter()
  const nameId = useId()
  const agreeId = useId()
  const nameRef = useRef<HTMLInputElement>(null)
  const doneRef = useRef<HTMLParagraphElement>(null)
  const [name, setName] = useState('')
  const [signature, setSignature] = useState<string | null>(null)
  const [agreed, setAgreed] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const [resetKey, setResetKey] = useState(0)
  const [done, setDone] = useState(false)
  // 스크립트가 오기 전에는 버튼을 잠근다 — 그때 누르면 브라우저가 폼을 그대로 내, 적은 이름이 주소에 실린다.
  const [ready, setReady] = useState(false)

  useEffect(() => {
    // 스크립트가 오기 전에 친 이름은 칸에만 있고 상태에는 없다 — 한 번 옮겨 온다.
    const typed = nameRef.current?.value ?? ''
    if (typed !== '') setName(typed)
    setReady(true)
  }, [])

  // 보냈다는 글로 포커스를 옮긴다 — 화면을 다시 읽는 동안에도 스크린리더가 읽는다.
  useEffect(() => {
    if (done) doneRef.current?.focus()
  }, [done])

  /** 칸에 실제로 있는 글자. 스크립트가 오기 전에 친 글자는 상태에 없고 칸에만 있다. */
  const typedName = () => (nameRef.current?.value ?? name).trim()

  /** 빠진 것. 없으면 null — 있으면 백엔드를 부르지 않는다. */
  const missing = (): string | null => {
    if (typedName() === '') return '이름을 적어 주세요'
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
        body: JSON.stringify({ doc_digest: digest, signer_name: typedName(), signature_png: signature }),
      })
      status = res.status
    } catch {
      status = 503
    }
    setSending(false)
    if (status === 204 || status === 410) {
      // 다시 읽기를 기다리지 않고 곧바로 알린다 — 느린 망에서 "안 눌렸다"로 보이지 않게.
      // 410 은 이미 낸 것이다 — 오류로 보이지 않는다.
      setDone(true)
      router.refresh()
    } else if (status === 404) {
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

  if (done) {
    return (
      <p ref={doneRef} className={styles.done} role="status" tabIndex={-1}>
        보냈어요. {shopName}에서 확인할게요.
      </p>
    )
  }

  return (
    // method 는 스크립트 없이 나갈 때를 위한 것이다 — GET 이면 칸의 값이 주소에 실린다.
    <form className={styles.sign} method="post" onSubmit={send} noValidate>
      <noscript>
        <p className={styles.notice}>서명하려면 자바스크립트를 켜 주세요</p>
      </noscript>
      <label className={styles.field} htmlFor={nameId}>
        이름
      </label>
      <input
        ref={nameRef}
        id={nameId}
        className={styles.input}
        type="text"
        name="signer_name"
        value={name}
        maxLength={50}
        autoComplete="name"
        onChange={(event) => {
          setName(event.target.value)
          setNotice(null)
        }}
      />
      <div className={styles.field}>서명</div>
      <SignaturePad
        onChange={(png) => {
          setSignature(png)
          if (png !== null) setNotice(null)
        }}
        resetKey={resetKey}
      />
      <div className={styles.agree}>
        <input
          id={agreeId}
          type="checkbox"
          checked={agreed}
          onChange={(event) => {
            setAgreed(event.target.checked)
            if (event.target.checked) setNotice(null)
          }}
        />
        <label htmlFor={agreeId}>위 내용을 읽었고 동의해요</label>
      </div>
      {notice !== null && (
        <p className={styles.notice} role="alert">
          {notice}
        </p>
      )}
      <button className={styles.send} type="submit" disabled={!ready || sending}>
        {sending ? '보내는 중…' : '동의하고 보내기'}
      </button>
    </form>
  )
}

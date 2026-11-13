import { sessionSecret } from './config'

/** 무엇을 봉하는가. 용도마다 키가 달라 한쪽으로 봉한 값은 다른 쪽에서 열리지 않는다. */
export type Purpose = 'session' | 'claim'

const IV_BYTES = 12

async function keyFor(purpose: Purpose): Promise<CryptoKey> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`${purpose}:${sessionSecret()}`))
  return crypto.subtle.importKey('raw', digest, 'AES-GCM', false, ['encrypt', 'decrypt'])
}

/** 글자를 봉한다(AES-256-GCM). 결과는 base64url(iv ‖ 암호문과 태그)이다. */
export async function seal(purpose: Purpose, value: string): Promise<string> {
  const iv = crypto.getRandomValues(new Uint8Array(IV_BYTES))
  const sealed = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, await keyFor(purpose), new TextEncoder().encode(value))
  return Buffer.concat([iv, new Uint8Array(sealed)]).toString('base64url')
}

/** 봉한 값을 연다. 우리가 그 용도로 봉한 것이 아니면 null 이다 — 어떤 입력에도 던지지 않는다. */
export async function open(purpose: Purpose, sealed: string): Promise<string | null> {
  try {
    if (!/^[A-Za-z0-9_-]+$/.test(sealed)) return null
    const bytes = Buffer.from(sealed, 'base64url')
    if (bytes.length <= IV_BYTES) return null
    const plain = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: bytes.subarray(0, IV_BYTES) },
      await keyFor(purpose),
      bytes.subarray(IV_BYTES),
    )
    return new TextDecoder().decode(plain)
  } catch {
    return null
  }
}

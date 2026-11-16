import styles from './ErrorScreen.module.css'

export type ErrorKind = 'not_found' | 'closed' | 'busy' | 'unavailable' | 'forbidden'

const SCREENS: Record<ErrorKind, { mark: string; title: string; text?: string; login?: true }> = {
  not_found: { mark: 'Not found', title: '알림장을 찾을 수 없어요' },
  closed: {
    mark: 'Closed',
    title: '닫힌 알림장이에요',
    text: '기간이 지났거나 매장에서 닫은 알림장이에요. 매장에 다시 요청해 주세요.',
    // 닫힌 링크로는 잇지 않는다. 이미 이어진 보호자가 로그인해 지난 기록을 보게 한다.
    login: true,
  },
  busy: { mark: 'One moment', title: '잠시 후 다시 열어 주세요' },
  unavailable: { mark: 'One moment', title: '잠시 후 다시 열어 주세요' },
  // 로그인한 보호자의 계정이 정지됐다.
  forbidden: { mark: 'Closed', title: '이 계정으로는 볼 수 없어요' },
}

/** 서류(동의서)의 화면. 알림장과 글이 다른 것만 적는다 — 로그인 링크가 없다(서류는 계정에 잇지 않는다). */
const FORM_SCREENS: Partial<Record<ErrorKind, { mark: string; title: string; text?: string }>> = {
  not_found: { mark: 'Not found', title: '서류를 찾을 수 없어요' },
  closed: {
    mark: 'Closed',
    title: '닫힌 서류예요',
    text: '기간이 지났거나 매장에서 닫은 서류예요. 매장에 다시 요청해 주세요.',
  },
}

/**
 * login 은 로그인할 수단이 있는가다. 있을 때만 닫힌 화면에 내 기록으로 가는 링크를 둔다.
 * what 은 무엇의 오류인가다 — 서류면 서류의 글을 쓴다.
 */
export function ErrorScreen({
  kind,
  login = false,
  what = 'report',
}: {
  kind: ErrorKind
  login?: boolean
  what?: 'report' | 'form'
}) {
  const screen: { mark: string; title: string; text?: string; login?: true } =
    (what === 'form' ? FORM_SCREENS[kind] : undefined) ?? SCREENS[kind]
  const { mark, title, text } = screen
  const offersLogin = what === 'report' && screen.login
  return (
    <main className={styles.screen}>
      <div className={styles.mark} aria-hidden="true">
        {mark}
      </div>
      <h1 className={styles.title}>{title}</h1>
      {text && <p className={styles.text}>{text}</p>}
      {offersLogin && login && (
        <a className={styles.link} href="/me">
          로그인하고 지난 기록 보기
        </a>
      )}
    </main>
  )
}

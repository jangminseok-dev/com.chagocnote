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

export function ErrorScreen({ kind }: { kind: ErrorKind }) {
  const { mark, title, text, login } = SCREENS[kind]
  return (
    <main className={styles.screen}>
      <div className={styles.mark} aria-hidden="true">
        {mark}
      </div>
      <h1 className={styles.title}>{title}</h1>
      {text && <p className={styles.text}>{text}</p>}
      {login && (
        <a className={styles.link} href="/me">
          로그인하고 지난 기록 보기
        </a>
      )}
    </main>
  )
}

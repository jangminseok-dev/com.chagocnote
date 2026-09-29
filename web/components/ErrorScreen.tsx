import styles from './ErrorScreen.module.css'

export type ErrorKind = 'not_found' | 'closed' | 'busy' | 'unavailable'

const SCREENS: Record<ErrorKind, { mark: string; title: string; text?: string }> = {
  not_found: { mark: 'Not found', title: '알림장을 찾을 수 없어요' },
  closed: {
    mark: 'Closed',
    title: '닫힌 알림장이에요',
    text: '기간이 지났거나 매장에서 닫은 알림장이에요. 매장에 다시 요청해 주세요.',
  },
  busy: { mark: 'One moment', title: '잠시 후 다시 열어 주세요' },
  unavailable: { mark: 'One moment', title: '잠시 후 다시 열어 주세요' },
}

export function ErrorScreen({ kind }: { kind: ErrorKind }) {
  const { mark, title, text } = SCREENS[kind]
  return (
    <main className={styles.screen}>
      <div className={styles.mark} aria-hidden="true">
        {mark}
      </div>
      <h1 className={styles.title}>{title}</h1>
      {text && <p className={styles.text}>{text}</p>}
    </main>
  )
}

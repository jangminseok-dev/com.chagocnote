import styles from './Member.module.css'

/**
 * 로그인 화면. 지금은 개발용 로그인뿐이다 — 카카오·애플은 연결한 뒤에 그린다.
 * next 는 로그인 뒤 돌아갈 경로다(이미 검증한 값을 받는다).
 */
export function LoginScreen({ dev, next, failed }: { dev: boolean; next: string; failed: boolean }) {
  return (
    <main className={styles.page} data-section="login">
      <div className={styles.mark} aria-hidden="true">
        Sign in
      </div>
      <h1 className={styles.title}>로그인</h1>
      <p className={styles.text}>로그인하면 우리 아이의 지난 미용 알림장을 모아 볼 수 있어요.</p>
      {failed && (
        <p className={styles.alert} role="alert">
          로그인하지 못했어요. 다시 시도해 주세요.
        </p>
      )}
      {dev ? (
        <form className={styles.form} method="post" action="/login/dev">
          <input type="hidden" name="next" value={next} />
          <label className={styles.label} htmlFor="login-name">
            개발용 로그인 이름
          </label>
          <input className={styles.input} id="login-name" name="name" required maxLength={50} autoComplete="off" />
          <button className={styles.primary} type="submit">
            로그인
          </button>
        </form>
      ) : (
        <p className={styles.alert}>로그인은 준비 중이에요.</p>
      )}
    </main>
  )
}

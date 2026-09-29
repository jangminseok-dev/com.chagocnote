import styles from './ReportView.module.css'

/** 케어 메모. 줄바꿈은 CSS 가 살린다. */
export function CareNote({ text }: { text: string }) {
  return (
    <section data-section="note">
      <div className={styles.label}>
        <i className={styles.serif}>Care note</i>
        <span>매장에서 남긴 말</span>
      </div>
      <p className={`${styles.card} ${styles.memo}`}>{text}</p>
    </section>
  )
}

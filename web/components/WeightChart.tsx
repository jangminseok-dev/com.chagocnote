import { koreanDate, weight } from '../lib/format'
import type { WeightItem } from '../lib/guardian'
import styles from './Member.module.css'

const W = 300
const H = 90
const PAD = 8

/**
 * 몸무게 변화(⑫ 설계 3.3) — 날짜와 kg 의 목록, 점이 둘 이상이면 그 위에 선 그림(라이브러리 없이 SVG).
 * 풀이 문구·색 구분·목표선이 없다 — 숫자와 선만.
 */
export function WeightChart({ items }: { items: WeightItem[] }) {
  if (items.length === 0) return null
  const values = items.map((item) => item.weight_kg)
  const low = Math.min(...values)
  const span = Math.max(...values) - low || 1
  const x = (i: number) => PAD + (i * (W - PAD * 2)) / Math.max(items.length - 1, 1)
  const y = (kg: number) => H - PAD - ((kg - low) * (H - PAD * 2)) / span
  return (
    <section className={styles.weights} data-section="weights">
      <h2>몸무게</h2>
      {items.length > 1 && (
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="몸무게 변화">
          <polyline fill="none" stroke="currentColor" strokeWidth="1.5" points={items.map((item, i) => `${x(i)},${y(item.weight_kg)}`).join(' ')} />
          {items.map((item, i) => (
            <circle key={i} cx={x(i)} cy={y(item.weight_kg)} r="2.5" fill="currentColor" />
          ))}
        </svg>
      )}
      <ul>
        {items.map((item, i) => (
          <li key={i}>
            <span>{koreanDate(item.visit_date)}</span>
            <b>{weight(item.weight_kg)}</b>
          </li>
        ))}
      </ul>
    </section>
  )
}

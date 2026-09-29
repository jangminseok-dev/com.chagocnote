// 표시 형식. 날짜는 문자열의 숫자를 그대로 읽는다 — 서버의 시간대에 기대지 않는다.

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]
const WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

/** 'YYYY-MM-DD…' 의 앞 열 글자를 [년, 월, 일] 로. */
function dateParts(value: string): [number, number, number] {
  return [Number(value.slice(0, 4)), Number(value.slice(5, 7)), Number(value.slice(8, 10))]
}

/** '2026-09-28' → '28' */
export function dayNumber(visitDate: string): string {
  return String(dateParts(visitDate)[2])
}

/** '2026-09-28' → ['September', 'Monday'] */
export function monthAndWeekday(visitDate: string): [string, string] {
  const [year, month, day] = dateParts(visitDate)
  // 요일은 달력 계산이다. UTC 로 만들고 UTC 로 읽어 시간대가 끼어들지 않게 한다.
  const weekday = new Date(Date.UTC(year, month - 1, day)).getUTCDay()
  return [MONTHS[month - 1], WEEKDAYS[weekday]]
}

/** '2026-10-28T23:59:59+09:00' → '10월 28일' */
export function koreanDate(iso: string): string {
  const [, month, day] = dateParts(iso)
  return `${month}월 ${day}일`
}

/** 55000 → '55,000' */
export function won(amount: number): string {
  return amount.toLocaleString('en-US')
}

/** 4.2 → '4.2 kg' */
export function weight(kg: number): string {
  return `${kg} kg`
}

/** 18 → '0:18', 65 → '1:05' */
export function duration(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

export function reportTitle(petName: string | null): string {
  return petName === null ? '미용 알림장' : `${petName}의 미용 알림장`
}

/** 'after' → '미용 후' */
export function phaseLabel(phase: 'before' | 'after'): string {
  return phase === 'after' ? '미용 후' : '미용 전'
}

/** 그림의 alt 와 버튼 이름에 쓴다. → '미용 후 사진', '미용 전 영상' */
export function mediaLabel(media: { kind: 'photo' | 'video'; phase: 'before' | 'after' }): string {
  return `${phaseLabel(media.phase)} ${media.kind === 'video' ? '영상' : '사진'}`
}

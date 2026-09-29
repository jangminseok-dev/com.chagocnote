import { afterEach, describe, expect, test, vi } from 'vitest'
import { dayNumber, duration, koreanDate, monthAndWeekday, reportTitle, weight, won } from '../lib/format'

afterEach(() => {
  vi.unstubAllEnvs()
})

// 서버의 시간대가 어디든 날짜가 밀리지 않는다. 시간대를 바꿔 가며 같은 값을 본다.
describe.each(['Asia/Seoul', 'America/Los_Angeles', 'UTC'])('서버 시간대가 %s 일 때', (zone) => {
  function inZone() {
    vi.stubEnv('TZ', zone)
    // 시간대가 실제로 바뀌었는지 — 바뀌지 않으면 아래 검사는 뜻이 없다.
    expect(new Intl.DateTimeFormat().resolvedOptions().timeZone).toBe(zone)
  }

  test('방문 날짜의 일', () => {
    inZone()
    expect(dayNumber('2026-09-28')).toBe('28')
    expect(dayNumber('2026-01-01')).toBe('1')
    expect(dayNumber('2026-12-31')).toBe('31')
  })

  test('방문 날짜의 영문 월과 요일', () => {
    inZone()
    expect(monthAndWeekday('2026-09-28')).toEqual(['September', 'Monday'])
    expect(monthAndWeekday('2026-01-01')).toEqual(['January', 'Thursday'])
    expect(monthAndWeekday('2026-12-31')).toEqual(['December', 'Thursday'])
  })

  test('닫히는 날은 문자열의 날짜 그대로다', () => {
    inZone()
    expect(koreanDate('2026-10-28T23:59:59+09:00')).toBe('10월 28일')
    expect(koreanDate('2026-01-01T00:00:00+09:00')).toBe('1월 1일')
    expect(koreanDate('2026-12-31T23:59:59+09:00')).toBe('12월 31일')
  })
})

test('금액은 세 자리마다 쉼표다', () => {
  expect(won(55000)).toBe('55,000')
  expect(won(0)).toBe('0')
  expect(won(1000000)).toBe('1,000,000')
})

test('몸무게는 kg 을 붙인다', () => {
  expect(weight(4.2)).toBe('4.2 kg')
  expect(weight(4)).toBe('4 kg')
})

test('영상 길이는 분:초다', () => {
  expect(duration(18)).toBe('0:18')
  expect(duration(65)).toBe('1:05')
  expect(duration(0)).toBe('0:00')
  expect(duration(59)).toBe('0:59')
  expect(duration(60)).toBe('1:00')
  expect(duration(3599)).toBe('59:59')
})

test('제목은 이름이 있으면 "○○의 미용 알림장" 이다', () => {
  expect(reportTitle('두부')).toBe('두부의 미용 알림장')
})

test('이름이 없으면 "미용 알림장" 이다', () => {
  expect(reportTitle(null)).toBe('미용 알림장')
})

/// 일정 설정 화면의 입력 규칙. 서버 규칙(10분 단위 영업시간, 여는 시각 < 닫는
/// 시각)을 앱에서 먼저 확인한다 — 최종 판단은 서버다.
library;

/// `HH:MM` 을 분으로.
int minutesOf(String hhmm) =>
    int.parse(hhmm.substring(0, 2)) * 60 + int.parse(hhmm.substring(3, 5));

/// 분을 `HH:MM` 으로.
String hhmmOf(int minutes) =>
    '${(minutes ~/ 60).toString().padLeft(2, '0')}:${(minutes % 60).toString().padLeft(2, '0')}';

bool opensBeforeCloses(String opensAt, String closesAt) =>
    minutesOf(opensAt) < minutesOf(closesAt);

/// 임시 휴무 입력(`2026.10.09`, `2026-10-09`, `20261009`)을 날짜로 바꾼다.
/// 없는 날짜나 오늘보다 이른 날은 null — 지난 휴무는 뜻이 없다.
DateTime? parseClosedDate(String raw, DateTime today) {
  final digits = raw.replaceAll(RegExp(r'[.\-/\s]'), '');
  if (!RegExp(r'^\d{8}$').hasMatch(digits)) return null;
  final year = int.parse(digits.substring(0, 4));
  final month = int.parse(digits.substring(4, 6));
  final day = int.parse(digits.substring(6, 8));
  final date = DateTime(year, month, day);
  if (date.year != year || date.month != month || date.day != day) return null;
  if (date.isBefore(DateTime(today.year, today.month, today.day))) return null;
  return date;
}

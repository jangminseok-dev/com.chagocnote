/// 서버가 주는 매장 시각·날짜 문자열과 화면의 `DateTime` 사이의 변환. 기능 폴더 여럿이 함께 쓴다.
///
/// 시간대 계산은 하지 않는다 — 응답 시각은 매장 시간대이고 앱은 벽시계 값만 보인다(결정 기록 006).
library;

/// 매장 시간대가 붙은 시각(`2026-10-02T14:00:00+09:00`).
///
/// 화면에는 [wall](매장의 벽시계 — 시간대 없이 만든 `DateTime`)을 보이고,
/// 서버에는 받은 문자열 [iso]를 그대로 돌려보낸다. 기기 시간대로 바꾸지 않는다
/// (결정 기록 006 — 응답 시각은 매장 시간대다).
class ShopTime {
  const ShopTime._(this.wall, this.iso);

  factory ShopTime.parse(String iso) {
    final m = _pattern.firstMatch(iso);
    if (m == null) throw FormatException('시각 형식이 아닙니다', iso);
    int part(int i) => int.parse(m.group(i) ?? '0');
    return ShopTime._(
      DateTime(part(1), part(2), part(3), part(4), part(5), part(6)),
      iso,
    );
  }

  static final _pattern = RegExp(
    r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?',
  );

  final DateTime wall;
  final String iso;

  /// 그날(매장 시간대)의 날짜만.
  DateTime get day => DateTime(wall.year, wall.month, wall.day);
}

/// `2026-10-02` → 그날 자정(시간대 없음).
DateTime parseDay(String value) {
  final parts = value.split('-').map(int.parse).toList();
  return DateTime(parts[0], parts[1], parts[2]);
}

/// 날짜를 `2026-10-02`로.
String isoDay(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

/// 달을 `2026-10`으로.
String isoMonth(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}';

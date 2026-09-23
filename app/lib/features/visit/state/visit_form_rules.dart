/// 예약 폼의 소요 규칙. 서버 규칙(10~600분, 10분 단위)을 앱에서 먼저 지킨다 —
/// 최종 판단은 서버다.
library;

const minDuration = 10;
const maxDuration = 600;

/// [+]·[−] 한 번에 바뀌는 소요. 길게 누르면 [durationLongStep].
const durationStep = 10;
const durationLongStep = 30;

int clampDuration(int minutes) =>
    minutes.clamp(minDuration, maxDuration).toInt();

/// 고른 메뉴로 채우는 소요 — 메뉴 기본 소요의 합(기본 소요가 없는 메뉴는
/// 매장 기본 소요), 메뉴가 없으면 매장 기본 소요. 600분을 넘지 않는다.
/// 서버는 소요를 비우면 같은 합을 쓰지만 600을 넘으면 422 라, 앱은 늘
/// 채워 보낸다(결정 기록 006).
int menuDuration(Iterable<int?> menuDefaults, int shopDefault) {
  final list = menuDefaults.toList();
  if (list.isEmpty) return shopDefault;
  final sum = list.fold<int>(0, (total, m) => total + (m ?? shopDefault));
  return clampDuration(sum);
}

/// 소요를 한 칸(10분, [long]이면 30분) 늘리거나 줄인다.
int stepDuration(int minutes, {required bool longer, bool long = false}) {
  final step = long ? durationLongStep : durationStep;
  return clampDuration(minutes + (longer ? step : -step));
}

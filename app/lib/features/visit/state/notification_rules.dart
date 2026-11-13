import '../api/notification_models.dart';

/// 방문 상세의 블록에 보일 줄 — 취소된 줄을 뺀다. 순서는 서버가 준 그대로(최신순)다.
List<NotificationMessage> visibleRows(List<NotificationMessage> rows) => [
  for (final row in rows)
    if (row.status != NotificationStatus.canceled) row,
];

/// [row]가 그 종류의 가장 최근 줄인가 — 재발송은 가장 최근 줄을 다시 보내므로 단추는 그 줄에만 둔다.
bool isLatestOfKind(List<NotificationMessage> rows, NotificationMessage row) =>
    rows.firstWhere((other) => other.kind == row.kind).messageId ==
    row.messageId;

/// 전날 리마인드 시각 — 08:00 부터 21:00 까지 30분 간격(서버가 받는 범위).
final List<String> reminderTimeChoices = [
  for (var minutes = 8 * 60; minutes <= 21 * 60; minutes += 30)
    '${(minutes ~/ 60).toString().padLeft(2, '0')}:${(minutes % 60).toString().padLeft(2, '0')}',
];

/// 다음 예약 제안을 보낼 때 — null 은 지난 방문 간격대로.
const List<int?> nextVisitWeekChoices = [null, 2, 3, 4, 5, 6, 8, 10, 12];

/// 다음 예약 제안을 다시 보내지 않는 기간(일).
const List<int> cooldownDayChoices = [14, 30, 60, 90];

/// 서버 값 [current]가 고르기 목록에 없으면 맨 앞에 더한다 — 지금 값이 보이지 않으면 안 된다.
List<T> withCurrent<T>(List<T> choices, T current) =>
    choices.contains(current) ? choices : [current, ...choices];

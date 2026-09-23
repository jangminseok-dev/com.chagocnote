import '../api/visit_models.dart';

/// 하루 목록의 가족 묶음 하나 — 같은 보호자·같은 시작 시각의 방문들(서버의
/// `group_key`가 같은 줄). 화면은 묶음을 카드 하나로 그린다.
class DayGroup {
  DayGroup(this.items);

  final List<DayVisitItem> items;

  List<Visit> get visits => [for (final i in items) i.visit];
  List<int> get ids => [for (final i in items) i.visit.visitId];
  Visit get first => items.first.visit;
  ShopTime get startsAt => first.startsAt;

  /// 묶음에서 가장 늦게 끝나는 시각.
  DateTime get endsAt => items
      .map((i) => i.visit.endsAt.wall)
      .reduce((a, b) => a.isAfter(b) ? a : b);

  bool get overlapping => items.any((i) => i.overlapping);
  bool get unresolved => items.any((i) => i.unresolved);

  /// 시간을 차지하는 방문이 있는가(취소·노쇼만이면 빈 시간이다).
  bool get occupiesTime => items.any((i) => i.visit.occupiesTime);

  /// 묶음의 상태가 모두 같으면 그 상태, 섞였으면 null.
  String? get uniformStatus {
    final statuses = {for (final i in items) i.visit.status};
    return statuses.length == 1 ? statuses.single : null;
  }
}

/// 같은 `group_key`끼리 묶는다. 처음 나온 순서(=서버의 시작 순)를 지킨다 —
/// 같은 시각에 다른 보호자의 방문이 끼어 있어도 묶음이 쪼개지지 않는다.
List<DayGroup> groupDay(List<DayVisitItem> items) {
  final byKey = <String, List<DayVisitItem>>{};
  for (final item in items) {
    byKey.putIfAbsent(item.groupKey, () => []).add(item);
  }
  return [for (final list in byKey.values) DayGroup(list)];
}

/// 목록에서 [groups]의 각 묶음 앞에 둘 빈 시간(분). 시간을 차지하는 묶음들
/// 사이가 [minMinutes] 이상 비었을 때만 값이 있다. 첫 묶음 앞은 비워 둔다.
List<int?> gapsBefore(List<DayGroup> groups, {int minMinutes = 60}) {
  DateTime? latestEnd;
  return [
    for (final g in groups)
      () {
        if (!g.occupiesTime) return null;
        final start = g.startsAt.wall;
        final gap = latestEnd == null
            ? null
            : start.difference(latestEnd!).inMinutes;
        if (latestEnd == null || g.endsAt.isAfter(latestEnd!)) {
          latestEnd = g.endsAt;
        }
        return gap != null && gap >= minMinutes ? gap : null;
      }(),
  ];
}

/// 시간표의 칸 번호. 앞선 묶음과 겹치면 옆 칸으로 보낸다(가장 왼쪽 빈 칸).
/// [groups]는 시작 순이다. 돌려주는 목록은 같은 순서의 칸 번호다.
List<int> timelineColumns(List<DayGroup> groups) {
  final columnEnds = <DateTime>[];
  final result = <int>[];
  for (final g in groups) {
    final start = g.startsAt.wall;
    var column = columnEnds.indexWhere((end) => !end.isAfter(start));
    if (column == -1) {
      columnEnds.add(g.endsAt);
      column = columnEnds.length - 1;
    } else {
      columnEnds[column] = g.endsAt;
    }
    result.add(column);
  }
  return result;
}

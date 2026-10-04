import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/state/day_layout.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/visit_fixtures.dart';

DayVisitItem _item(
  int id,
  String start, {
  int duration = 60,
  String? group,
  String status = 'reserved',
  bool reportSent = false,
}) => DayVisitItem.fromJson(
  dayItemJson(
    visitJson(
      visitId: id,
      start: start,
      durationMinutes: duration,
      status: status,
    ),
    groupKey: group ?? 'g$id',
    reportSent: reportSent,
  ),
);

void main() {
  test('같은 group_key 는 사이에 다른 방문이 끼어도 한 묶음이다', () {
    final groups = groupDay([
      _item(1, '14:00', group: 'a'),
      _item(2, '14:00', group: 'b'),
      _item(3, '14:00', group: 'a'),
    ]);

    expect(groups.map((g) => g.ids), [
      [1, 3],
      [2],
    ]);
  });

  test('묶음의 끝은 가장 늦게 끝나는 방문이고, 상태가 섞이면 하나로 말하지 않는다', () {
    final group = groupDay([
      _item(1, '13:00', duration: 60, group: 'a'),
      _item(2, '13:00', duration: 90, group: 'a', status: 'in_progress'),
    ]).single;

    expect(group.endsAt, DateTime(2026, 10, 2, 14, 30));
    expect(group.uniformStatus, isNull);
  });

  test('취소된 형제의 긴 소요는 묶음 끝에 들지 않는다', () {
    final group = groupDay([
      _item(1, '13:00', duration: 60, group: 'a'),
      _item(2, '13:00', duration: 150, group: 'a', status: 'canceled'),
    ]).single;

    expect(group.endsAt, DateTime(2026, 10, 2, 14));

    final allCanceled = groupDay([
      _item(3, '13:00', duration: 60, group: 'b', status: 'canceled'),
      _item(4, '13:00', duration: 150, group: 'b', status: 'no_show'),
    ]).single;

    expect(allCanceled.endsAt, DateTime(2026, 10, 2, 15, 30));
  });

  test('묶음은 완료한 방문이 모두 보냈을 때만 보냄이다', () {
    DayVisitItem item(int id, String status, {bool sent = false}) =>
        _item(id, '13:00', group: 'a', status: status, reportSent: sent);
    bool sent(List<DayVisitItem> items) => groupDay(items).single.reportSent;

    expect(
      sent([
        item(1, 'completed', sent: true),
        item(2, 'completed', sent: true),
      ]),
      isTrue,
    );
    // 일부만 보냈는데 표시하면 다 보낸 줄 안다.
    expect(
      sent([item(1, 'completed', sent: true), item(2, 'completed')]),
      isFalse,
    );
    // 취소한 아이는 보낼 것이 없다 — 세지 않는다.
    expect(
      sent([item(1, 'completed', sent: true), item(2, 'canceled')]),
      isTrue,
    );
    expect(sent([item(1, 'reserved'), item(2, 'canceled')]), isFalse);
  });

  test('시간을 차지하는 묶음 사이가 한 시간 이상 비면 그 길이를 준다', () {
    final groups = groupDay([
      _item(1, '10:00', duration: 150),
      _item(2, '13:00', duration: 90),
      _item(3, '15:30', duration: 60),
      _item(4, '15:40', duration: 60),
    ]);

    expect(gapsBefore(groups), [null, null, 60, null]);
  });

  test('취소·노쇼는 빈 시간으로 센다', () {
    final groups = groupDay([
      _item(1, '10:00'),
      _item(2, '11:00', status: 'canceled'),
      _item(3, '13:00'),
    ]);

    expect(gapsBefore(groups), [null, null, 120]);
  });

  test('앞 방문이 길게 이어지면 그 끝부터 잰다', () {
    final groups = groupDay([
      _item(1, '10:00', duration: 300),
      _item(2, '11:00'),
      _item(3, '16:00'),
    ]);

    expect(gapsBefore(groups), [null, null, 60]);
  });

  test('겹치는 묶음은 옆 칸으로, 끝난 칸은 다시 쓴다', () {
    final groups = groupDay([
      _item(1, '10:00', duration: 120),
      _item(2, '11:00', duration: 60),
      _item(3, '12:00', duration: 60),
      _item(4, '12:30', duration: 60),
    ]);

    expect(timelineColumns(groups), [0, 1, 0, 1]);
  });

  group('시간표 범위', () {
    test('설정이 없으면 10~19시, 영업시간이 있으면 그 시간이 기본이다', () {
      expect(timelineHours(null, []), (first: 10, last: 19));
      final settings = VisitSettings.fromJson(
        settingsJson(opensAt: '09:00:00', closesAt: '18:30:00'),
      );
      expect(timelineHours(settings, []), (
        first: 9,
        last: 19,
      )); // 18:30 은 19시 칸까지
    });

    test('영업시간 밖에 걸친 묶음이 있으면 그만큼 넓힌다', () {
      final settings = VisitSettings.fromJson(settingsJson());
      final groups = groupDay([
        _item(1, '08:30', duration: 60),
        _item(2, '18:00', duration: 90),
      ]);
      expect(timelineHours(settings, groups), (first: 8, last: 20));
    });

    test('영업시간 밖에서 정각에 끝나는 묶음은 그 시까지만 넓힌다', () {
      final settings = VisitSettings.fromJson(settingsJson());
      final groups = groupDay([_item(1, '18:00', duration: 120)]); // 20:00 끝
      expect(timelineHours(settings, groups), (first: 10, last: 20));
    });
  });
}

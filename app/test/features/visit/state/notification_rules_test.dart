import 'package:chagocnote/features/visit/api/notification_models.dart';
import 'package:chagocnote/features/visit/state/notification_rules.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/visit_fixtures.dart';

List<NotificationMessage> _rows(List<Map<String, dynamic>> items) =>
    NotificationMessage.listFromJson({'items': items});

void main() {
  test('보이는 줄은 취소된 것을 빼고 서버의 순서(최신순)를 지킨다', () {
    final rows = _rows([
      notificationMessageJson(
        messageId: 4,
        kind: 'reminder',
        status: 'scheduled',
      ),
      notificationMessageJson(
        messageId: 3,
        kind: 'reminder',
        status: 'canceled',
      ),
      notificationMessageJson(messageId: 2, status: 'sent'),
      notificationMessageJson(messageId: 1, status: 'canceled'),
    ]);

    expect(visibleRows(rows).map((m) => m.messageId), [4, 2]);
  });

  test('같은 종류의 줄 가운데 첫 줄만 가장 최근 줄이다', () {
    final rows = _rows([
      notificationMessageJson(
        messageId: 3,
        status: 'failed',
        errorKind: 'transient',
      ),
      notificationMessageJson(
        messageId: 2,
        kind: 'reminder',
        status: 'scheduled',
      ),
      notificationMessageJson(
        messageId: 1,
        status: 'failed',
        errorKind: 'transient',
      ),
    ]);

    expect(rows.map((m) => isLatestOfKind(rows, m)), [true, true, false]);
  });

  test('리마인드 시각은 08:00 부터 21:00 까지 30분 간격이다', () {
    expect(reminderTimeChoices.length, 27);
    expect(reminderTimeChoices.first, '08:00');
    expect(reminderTimeChoices[1], '08:30');
    expect(reminderTimeChoices.last, '21:00');
  });

  test('주와 쿨다운의 고르기 값', () {
    expect(nextVisitWeekChoices, [null, 2, 3, 4, 5, 6, 8, 10, 12]);
    expect(cooldownDayChoices, [14, 30, 60, 90]);
  });

  test('서버 값이 목록에 없으면 맨 앞에 더하고 있으면 그대로다', () {
    expect(withCurrent(cooldownDayChoices, 45), [45, 14, 30, 60, 90]);
    expect(withCurrent(cooldownDayChoices, 30), cooldownDayChoices);
    expect(withCurrent(nextVisitWeekChoices, null), nextVisitWeekChoices);
    expect(withCurrent(reminderTimeChoices, '18:10').first, '18:10');
  });
}

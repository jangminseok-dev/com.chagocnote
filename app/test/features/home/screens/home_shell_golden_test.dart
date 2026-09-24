import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

void main() {
  testWidgets('홈 셸 골든 — 2026-09-22, 캘린더 탭', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    // 목업의 9월 — 월요일 휴무, 지난날은 마릿수, 앞날은 예약 수, 오늘(22일) 5마리.
    final backend = VisitTestBackend({
      'GET /v1/shops/3/visits/calendar': (o, b) => FakeResponse(
        statusCode: 200,
        data: calendarJson(
          days: {
            for (final e in {
              1: 3,
              2: 2,
              3: 4,
              4: 1,
              5: 2,
              8: 3,
              9: 2,
              10: 4,
              11: 1,
              12: 2,
              15: 3,
              16: 4,
              17: 1,
              18: 2,
              19: 3,
              22: 5,
            }.entries)
              e.key: {'visit_count': e.value, 'completed_count': e.value},
            for (final e in {23: 2, 24: 3, 25: 4, 26: 1, 29: 2, 30: 1}.entries)
              e.key: {'visit_count': e.value, 'open_count': e.value},
          },
          closedDays: {7, 14, 21, 28},
        ),
      ),
      'GET /v1/shops/3/visits': (o, b) => FakeResponse(
        statusCode: 200,
        data: dayJson(
          date: '2026-09-22',
          items: [
            dayItemJson(
              visitJson(
                date: '2026-09-22',
                start: '10:00',
                status: 'completed',
                pet: visitPetJson(name: '콩이'),
              ),
            ),
            dayItemJson(
              visitJson(
                visitId: 102,
                date: '2026-09-22',
                start: '13:00',
                status: 'in_progress',
                pet: visitPetJson(petId: 12, name: '두부'),
              ),
              groupKey: 'g2',
            ),
            dayItemJson(
              visitJson(
                visitId: 103,
                date: '2026-09-22',
                start: '13:00',
                status: 'in_progress',
                pet: visitPetJson(petId: 13, name: '보리'),
              ),
              groupKey: 'g2',
            ),
            dayItemJson(
              visitJson(
                visitId: 104,
                date: '2026-09-22',
                start: '15:30',
                pet: visitPetJson(petId: 14, name: '몽이'),
              ),
            ),
            dayItemJson(
              visitJson(
                visitId: 105,
                date: '2026-09-22',
                start: '17:00',
                pet: visitPetJson(petId: 15, name: '코코'),
              ),
              overlapping: true,
            ),
          ],
        ),
      ),
    });
    final setup = CustomerTestSetup(
      backend.call,
      overrides: [todayProvider.overrideWithValue(DateTime(2026, 9, 22))],
    );
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(customerRouterApp(setup.container));
    await settle(tester);

    await expectLater(
      find.byKey(ScreenKeys.home),
      matchesGoldenFile('goldens/home_shell.png'),
    );
  });
}

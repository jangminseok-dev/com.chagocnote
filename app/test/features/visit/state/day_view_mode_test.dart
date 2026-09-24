import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/features/visit/state/day_view_mode.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

void main() {
  test('기본은 목록이고, 고른 것을 기기에 기억한다', () async {
    final setup = CustomerTestSetup(
      (options, body) => const FakeResponse(statusCode: 500),
    );
    addTearDown(setup.container.dispose);

    expect(
      await setup.container.read(dayViewModeProvider.future),
      DayViewMode.list,
    );
    await setup.container
        .read(dayViewModeProvider.notifier)
        .select(DayViewMode.timeline);

    expect(
      setup.container.read(dayViewModeProvider).value,
      DayViewMode.timeline,
    );
    expect(await setup.prefs.read(PrefsKeys.dayViewMode), 'timeline');
  });

  test('기억한 것이 시간표면 시간표로 시작한다', () async {
    final setup = CustomerTestSetup(
      (options, body) => const FakeResponse(statusCode: 500),
    );
    addTearDown(setup.container.dispose);
    await setup.prefs.write(PrefsKeys.dayViewMode, 'timeline');

    expect(
      await setup.container.read(dayViewModeProvider.future),
      DayViewMode.timeline,
    );
  });
}

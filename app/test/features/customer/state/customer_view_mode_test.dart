import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/features/customer/state/customer_view_mode.dart';
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
      await setup.container.read(customerViewModeProvider.future),
      CustomerViewMode.list,
    );
    await setup.container
        .read(customerViewModeProvider.notifier)
        .select(CustomerViewMode.grid);

    expect(
      setup.container.read(customerViewModeProvider).value,
      CustomerViewMode.grid,
    );
    expect(await setup.prefs.read(PrefsKeys.customerViewMode), 'grid');
  });

  test('기억한 것이 격자면 격자로 시작한다', () async {
    final setup = CustomerTestSetup(
      (options, body) => const FakeResponse(statusCode: 500),
    );
    addTearDown(setup.container.dispose);
    await setup.prefs.write(PrefsKeys.customerViewMode, 'grid');

    expect(
      await setup.container.read(customerViewModeProvider.future),
      CustomerViewMode.grid,
    );
  });
}

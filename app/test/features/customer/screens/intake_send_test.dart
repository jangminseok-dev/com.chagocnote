// 문진표 보내기 셋(⑪-C) — 새 손님(고객 등록의 첫 화면), 새 아이·다시 받기(반려동물 상세의 보호자 탭).
import 'dart:convert';

import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/consent_fixtures.dart';
import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/intake_fixtures.dart';
import '../../../support/visit_test_backend.dart';

class _World {
  _World({FakeResponse? issue}) {
    final base = VisitTestBackend({
      'POST /v1/shops/3/intake-forms': (o, body) {
        sent.add(jsonDecode(utf8.decode(body!)) as Map<String, dynamic>);
        return issue ?? FakeResponse(statusCode: 201, data: formLinkJson(url: fakeIntakeUrl));
      },
      'GET /v1/shops/3/pets/11': (o, b) => FakeResponse(statusCode: 200, data: petDetailJson()),
    });
    setup = CustomerTestSetup(base.call);
  }

  late final CustomerTestSetup setup;
  final sent = <Map<String, dynamic>>[];

  Future<void> open(WidgetTester tester, String path) async {
    useTallView(tester, height: 1800);
    addTearDown(setup.container.dispose);
    await pushOnHome<Object?>(tester, setup, path);
  }
}

Future<void> _tap(WidgetTester tester, Key key) async {
  await tester.ensureVisible(find.byKey(key));
  await tester.tap(find.byKey(key));
  await settle(tester);
}

void main() {
  testWidgets('고객 등록의 첫 화면에서 새 손님에게 문진표를 보낸다 — 누르기 한 번에 공유 시트, 주소 하나', (tester) async {
    final world = _World();
    await world.open(tester, '/customers/new');

    expect(find.text(AppStrings.intakeSendNewHint), findsOneWidget);
    await _tap(tester, const ValueKey('intake-send-new'));

    expect(world.sent, [{'customer_id': null, 'pet_id': null}]);
    expect(world.setup.shareSheet.shared, [fakeIntakeUrl]);
    expect(find.text(fakeIntakeUrl), findsNothing);      // 주소는 화면에 그리지 않는다
  });

  testWidgets('반려동물 상세의 보호자 탭 — 새 아이 문진표는 그 고객으로, 다시 받기는 그 아이로 보낸다', (tester) async {
    final world = _World();
    await world.open(tester, '/pets/11?tab=owner');

    await _tap(tester, const ValueKey('intake-send-customer'));
    await _tap(tester, const ValueKey('intake-send-pet'));

    expect(world.sent, [{'customer_id': 7, 'pet_id': null}, {'customer_id': null, 'pet_id': 11}]);
    expect(world.setup.shareSheet.shared, hasLength(2));
    expect(find.widgetWithText(AppButton, AppStrings.intakeSendAddPet), findsOneWidget);
    expect(find.widgetWithText(AppButton, AppStrings.intakeSendUpdate), findsOneWidget);
  });

  testWidgets('링크를 만들지 못하면 알리고 공유 시트를 띄우지 않으며 다시 누를 수 있다', (tester) async {
    final world = _World(issue: const FakeResponse(statusCode: 500, data: {'code': 'INTERNAL_ERROR', 'message': 'x'}));
    await world.open(tester, '/customers/new');

    await _tap(tester, const ValueKey('intake-send-new'));

    expect(find.text(AppStrings.intakeSendFailed), findsOneWidget);
    expect(world.setup.shareSheet.shared, isEmpty);
    expect(tester.widget<AppButton>(find.widgetWithText(AppButton, AppStrings.intakeSendNew)).busy, isFalse);
  });

  testWidgets('공유 창이 열리지 않으면 보낸 서류에서 다시 공유할 수 있다고 알린다', (tester) async {
    final world = _World();
    world.setup.shareSheet.error = Exception('채널 오류');
    await world.open(tester, '/customers/new');

    await _tap(tester, const ValueKey('intake-send-new'));

    expect(find.text(AppStrings.intakeShareFailed), findsOneWidget);
    expect(world.sent, hasLength(1));
  });
}

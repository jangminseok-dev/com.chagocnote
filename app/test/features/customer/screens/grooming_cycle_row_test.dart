// 반려동물 상세 정보 탭의 미용 주기 줄과 시트(⑬ 설계 3.1·3.2).
import 'dart:async';
import 'dart:convert';

import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/load_fonts.dart';

const _cyclePath = '/v1/shops/3/pets/11/grooming-cycle';

/// 주기([revisit])를 들고 있는 서버. 쓰기는 직접 정한 값을 바꾼다(계산은 서버 몫이라 흉내만).
class _Server {
  _Server(this.revisit);

  Map<String, dynamic>? revisit;
  bool passedAway = false;
  FutureOr<FakeResponse?> Function(String key)? onWrite;
  final bodies = <Map<String, dynamic>>[];
  final calls = <String>[];

  Future<FakeResponse> handle(String key, List<int>? body) async {
    switch (key) {
      case 'GET /v1/shops/3/pets/11':
        return FakeResponse(
          statusCode: 200,
          data: petDetailJson(
            pet: petJson(passedAwayAt: passedAway ? '2026-10-01T00:00:00Z' : null),
            revisit: revisit,
          ),
        );
      case 'GET /v1/shops/3/customers/7':
        return FakeResponse(statusCode: 200, data: customerDetailJson());
      case 'GET /v1/shops/3/customers/7/guardian-link':
        return FakeResponse(statusCode: 200, data: guardianLinkJson(linked: false));
      case 'GET /v1/shops/3/customers':
        return FakeResponse(statusCode: 200, data: pageJson(items: [familyJson()]));
    }
    if (!key.startsWith('GET ')) calls.add(key); // 쓰기만 센다(홈의 달력 읽기는 빼고)
    if (key.startsWith('GET ')) return const FakeResponse(statusCode: 500, data: 'x');
    if (body != null) bodies.add(jsonDecode(utf8.decode(body)) as Map<String, dynamic>);
    final override = await onWrite?.call(key);
    if (override != null) return override;
    switch (key) {
      case 'PUT $_cyclePath':
        final weeks = bodies.last['weeks'] as int;
        revisit = petRevisitJson(cycleWeeks: weeks, cycleSource: 'manual', dueDate: '2026-11-19');
        return const FakeResponse(statusCode: 204);
      case 'DELETE $_cyclePath':
        revisit = petRevisitJson();
        return const FakeResponse(statusCode: 204);
    }
    return const FakeResponse(statusCode: 500, data: 'x');
  }
}

Future<CustomerTestSetup> _openPet(WidgetTester tester, _Server server) async {
  tester.view.physicalSize = const Size(390, 1700);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  final setup = CustomerTestSetup(
    (options, body) => server.handle('${options.method} ${options.path}', body),
    overrides: [todayProvider.overrideWithValue(DateTime(2026, 11, 17))],
  );
  addTearDown(setup.container.dispose);
  await tester.pumpWidget(customerRouterApp(setup.container));
  await tester.pumpAndSettle();
  setup.container.read(routerProvider).push('/pets/11');
  await tester.pumpAndSettle();
  return setup;
}

Future<void> _tap(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.tap(finder);
  await tester.pump(const Duration(milliseconds: 1));
  await tester.pumpAndSettle();
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

void main() {
  setUpAll(loadTestFonts);

  testWidgets('계산한 주기는 "보통 N주마다"와 다음 올 때(쯤), 안내한 날을 보인다', (tester) async {
    await _openPet(tester, _Server(petRevisitJson(nudgedOn: '2026-11-10')));

    expect(find.text('보통 6주마다 와요 · 지난 방문에서 계산'), findsOneWidget);
    expect(find.text('다음은 11월 12일쯤'), findsOneWidget);
    expect(find.text(AppStrings.revisitNudgedOn(DateTime(2026, 11, 10), DateTime(2026, 11, 17))), findsOneWidget);
  });

  testWidgets('직접 정한 주기', (tester) async {
    await _openPet(tester, _Server(petRevisitJson(cycleWeeks: 8, cycleSource: 'manual')));
    expect(find.text('8주마다 와요 · 직접 정함'), findsOneWidget);
  });

  testWidgets('간격 하나는 주기가 아니다 — 지난 간격을 글로만, 날짜는 기본 간격으로 어림', (tester) async {
    await _openPet(
      tester,
      _Server(petRevisitJson(cycleWeeks: 4, cycleSource: 'single', lastIntervalWeeks: 2)),
    );
    expect(find.text('지난번에는 2주 만에 왔어요'), findsOneWidget);
    expect(find.text('다음은 매장 기본 간격(4주)으로 어림해요'), findsOneWidget);
    expect(find.text('다음은 11월 12일쯤(어림)'), findsOneWidget);
  });

  testWidgets('한 번 온 아이', (tester) async {
    await _openPet(
      tester,
      _Server(petRevisitJson(cycleWeeks: 4, cycleSource: 'none', intervalCount: 0, lastIntervalWeeks: null)),
    );
    expect(find.text('아직 한 번 왔어요'), findsOneWidget);
  });

  testWidgets('완료 방문이 없으면 "미용 주기 정하기" 한 줄이다', (tester) async {
    await _openPet(
      tester,
      _Server(
        petRevisitJson(cycleWeeks: 4, cycleSource: 'none', intervalCount: 0, lastVisitDate: null, dueDate: null),
      ),
    );
    expect(find.text('미용 주기 정하기'), findsOneWidget);
    expect(find.textContaining('쯤'), findsNothing);
  });

  testWidgets('앞날 예약이 있으면 다음 올 때 대신 그렇게 말한다', (tester) async {
    await _openPet(tester, _Server(petRevisitJson(hasUpcoming: true)));
    expect(find.text(AppStrings.cycleHasUpcoming), findsOneWidget);
  });

  testWidgets('줄을 누르면 시트 — 주를 올리면 아래 날짜가 따라 바뀌고 [저장]으로 그 값을 보낸 뒤 상세를 다시 읽는다', (tester) async {
    final server = _Server(petRevisitJson());
    await _openPet(tester, server);

    await _tap(tester, find.text('보통 6주마다 와요 · 지난 방문에서 계산'));
    expect(find.text(AppStrings.cycleSheetPreview(DateTime(2026, 11, 12))), findsOneWidget);
    await _tap(tester, find.bySemanticsLabel(AppStrings.stepUp));
    expect(find.text(AppStrings.cycleSheetPreview(DateTime(2026, 11, 19))), findsOneWidget);
    // 계산한 값이면 되돌릴 것이 없다.
    expect(_button(AppStrings.cycleReset), findsNothing);
    await _tap(tester, _button(AppStrings.save));

    expect(server.calls, ['PUT $_cyclePath']);
    expect(server.bodies.single, {'weeks': 7});
    expect(find.text('7주마다 와요 · 직접 정함'), findsOneWidget);
  });

  testWidgets('직접 정한 값이면 [계산한 값으로 돌아가기]가 DELETE 를 보낸다', (tester) async {
    final server = _Server(petRevisitJson(cycleWeeks: 8, cycleSource: 'manual'));
    await _openPet(tester, server);

    await _tap(tester, find.text('8주마다 와요 · 직접 정함'));
    await _tap(tester, _button(AppStrings.cycleReset));

    expect(server.calls, ['DELETE $_cyclePath']);
    expect(find.text('보통 6주마다 와요 · 지난 방문에서 계산'), findsOneWidget);
  });

  testWidgets('저장이 실패하면 시트 안에 까닭을 말하고 시트는 남는다', (tester) async {
    final server = _Server(petRevisitJson())
      ..onWrite = (key) => const FakeResponse(statusCode: 500, data: {'code': 'INTERNAL', 'message': 'x'});
    await _openPet(tester, server);

    await _tap(tester, find.text('보통 6주마다 와요 · 지난 방문에서 계산'));
    await _tap(tester, _button(AppStrings.save));

    expect(_button(AppStrings.save), findsOneWidget);
    expect(find.byKey(const ValueKey('grooming-cycle-error')), findsOneWidget);
  });

  testWidgets('무지개다리를 건넌 아이에게는 주기 줄이 없다', (tester) async {
    final server = _Server(petRevisitJson())..passedAway = true;
    await _openPet(tester, server);

    expect(find.textContaining('주마다'), findsNothing);
  });
}

// 미용 동의 줄(기본 탭), 주의 고객 줄과 시트(보호자 탭), 고객 목록의 주의 표시(③-B).
import 'dart:async';
import 'dart:convert';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/error/error_messages.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/load_fonts.dart';

const _consentPath = '/v1/shops/3/pets/11/grooming-consent';
const _cautionPath = '/v1/shops/3/customers/7/caution';
const _reasonKey = ValueKey('caution-reason');

/// 가짜 서버 — 동의 받은 날([consentOn])과 주의 표시([caution])를 들고 있고 쓰기가 바꾼다.
/// [onWrite]가 있으면 쓰기의 응답을 그것이 정한다(문 걸기·실패).
class _Server {
  _Server({this.consentOn, this.caution, this.noShowCount = 0});

  String? consentOn;
  Map<String, dynamic>? caution;
  int noShowCount;
  bool passedAway = false;
  FutureOr<FakeResponse?> Function(String key)? onWrite;
  final bodies = <Map<String, dynamic>>[];

  Map<String, dynamic> _pet() => petDetailJson(
    pet: petJson(
      groomingConsentOn: consentOn,
      passedAwayAt: passedAway ? '2026-10-01T00:00:00Z' : null,
    ),
    caution: caution,
  );

  Map<String, dynamic> _customer() => customerDetailJson(
    customer: customerJson(caution: caution),
    noShowCount: noShowCount,
  );

  Future<FakeResponse> handle(String key, List<int>? body) async {
    switch (key) {
      case 'GET /v1/shops/3/pets/11':
        return FakeResponse(statusCode: 200, data: _pet());
      case 'GET /v1/shops/3/customers/7':
        return FakeResponse(statusCode: 200, data: _customer());
      case 'GET /v1/shops/3/customers/7/guardian-link':
        return FakeResponse(
          statusCode: 200,
          data: guardianLinkJson(linked: false),
        );
      case 'GET /v1/shops/3/customers':
        return FakeResponse(
          statusCode: 200,
          data: pageJson(items: [familyJson(caution: caution != null)]),
        );
    }
    final write = key.endsWith('/grooming-consent') || key.endsWith('/caution');
    if (!write) return const FakeResponse(statusCode: 500, data: 'x');
    if (body != null) {
      bodies.add(jsonDecode(utf8.decode(body)) as Map<String, dynamic>);
    }
    final override = await onWrite?.call(key);
    if (override != null) return override;
    switch (key) {
      case 'PUT $_consentPath':
        consentOn = '2026-11-14';
        return FakeResponse(statusCode: 200, data: _pet());
      case 'DELETE $_consentPath':
        consentOn = null;
        return FakeResponse(statusCode: 200, data: _pet());
      case 'PUT $_cautionPath':
        caution = cautionJson(reason: bodies.last['reason'] as String);
        return FakeResponse(statusCode: 200, data: _customer());
      case 'DELETE $_cautionPath':
        caution = null;
        return FakeResponse(statusCode: 200, data: _customer());
    }
    return const FakeResponse(statusCode: 500, data: 'x');
  }
}

FakeResponse _error(int status, String code) => FakeResponse(
  statusCode: status,
  data: {'code': code, 'message': 'x'},
);

String _serverError() =>
    messageFor(ApiException(statusCode: 500, code: 'INTERNAL', message: 'x'));

Future<CustomerTestSetup> _openPet(
  WidgetTester tester,
  _Server server, {
  bool ownerTab = false,
}) async {
  tester.view.physicalSize = const Size(390, 1700);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  final setup = CustomerTestSetup(
    (options, body) =>
        server.handle('${options.method} ${options.path}', body),
  );
  addTearDown(setup.container.dispose);
  await tester.pumpWidget(customerRouterApp(setup.container));
  await tester.pumpAndSettle();
  setup.container.read(routerProvider).push('/pets/11');
  await tester.pumpAndSettle();
  if (ownerTab) {
    await tester.tap(find.text(AppStrings.petTabOwner));
    await tester.pumpAndSettle();
  }
  return setup;
}

Future<void> _settle(WidgetTester tester) async {
  await tester.pump(const Duration(milliseconds: 1));
  await tester.pumpAndSettle();
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

int _count(CustomerTestSetup setup, String call) =>
    setup.calls.where((c) => c == call).length;

void main() {
  setUpAll(loadTestFonts);

  group('미용 동의 줄', () {
    testWidgets('받은 적이 없으면 그렇게 보이고 [받았어요]로 오늘 날짜를 적는다', (tester) async {
      final server = _Server();
      final setup = await _openPet(tester, server);
      expect(find.text(AppStrings.groomingConsentLabel), findsOneWidget);
      expect(find.text(AppStrings.groomingConsentNone), findsOneWidget);

      await tester.tap(find.byKey(const ValueKey('grooming-consent-set')));
      await _settle(tester);

      expect(_count(setup, 'PUT $_consentPath'), 1);
      expect(server.bodies.single, {'received_on': null});
      expect(find.text('2026년 11월 14일에 받았어요'), findsOneWidget);
      expect(_button(AppStrings.consentReceived), findsNothing);
    });

    testWidgets('[받았어요]를 연타해도 한 번만 보낸다', (tester) async {
      final gate = Completer<void>();
      final server = _Server()
        ..onWrite = (key) async {
          await gate.future;
          return null;
        };
      final setup = await _openPet(tester, server);

      final button = find.byKey(const ValueKey('grooming-consent-set'));
      await tester.tap(button);
      await tester.pump();
      await tester.tap(button);
      await tester.pump();
      gate.complete();
      await _settle(tester);

      expect(_count(setup, 'PUT $_consentPath'), 1);
    });

    testWidgets('받았으면 ··· 에서 다시 받았다고 적거나 기록을 지운다', (tester) async {
      final server = _Server(consentOn: '2025-12-01');
      final setup = await _openPet(tester, server);
      expect(find.text('2025년 12월 1일에 받았어요'), findsOneWidget);

      await tester.tap(find.bySemanticsLabel(AppStrings.groomingConsentMore));
      await tester.pumpAndSettle();
      await tester.tap(find.text(AppStrings.groomingConsentAgain));
      await _settle(tester);
      expect(_count(setup, 'PUT $_consentPath'), 1);
      expect(find.text('2026년 11월 14일에 받았어요'), findsOneWidget);

      await tester.tap(find.bySemanticsLabel(AppStrings.groomingConsentMore));
      await tester.pumpAndSettle();
      await tester.tap(find.text(AppStrings.groomingConsentClear));
      await _settle(tester);
      expect(_count(setup, 'DELETE $_consentPath'), 1);
      expect(find.text(AppStrings.groomingConsentNone), findsOneWidget);
    });

    testWidgets('실패하면 스낵바로 알리고 줄은 그대로다', (tester) async {
      final server = _Server()..onWrite = (key) => _error(500, 'INTERNAL');
      await _openPet(tester, server);

      await tester.tap(find.byKey(const ValueKey('grooming-consent-set')));
      await _settle(tester);

      expect(find.text(_serverError()), findsOneWidget);
      expect(find.text(AppStrings.groomingConsentNone), findsOneWidget);
      expect(
        tester.widget<AppButton>(_button(AppStrings.consentReceived)).busy,
        isFalse,
      );
    });

    testWidgets('무지개다리를 건넌 아이에게는 동의 줄이 없다', (tester) async {
      await _openPet(tester, _Server()..passedAway = true);

      expect(find.text(AppStrings.groomingConsentLabel), findsNothing);
    });
  });

  group('주의 고객 줄', () {
    testWidgets('표시가 없으면 그렇게 보이고, 노쇼 횟수와 보호자 계정 연결 사이에 있다', (tester) async {
      await _openPet(tester, _Server(), ownerTab: true);

      expect(find.text(AppStrings.cautionNone), findsOneWidget);
      expect(
        tester.getTopLeft(find.text(AppStrings.cautionLabel)).dy,
        greaterThan(tester.getTopLeft(find.text(AppStrings.noShowCountLabel)).dy),
      );
      expect(
        tester.getTopLeft(find.text(AppStrings.cautionLabel)).dy,
        lessThan(
          tester.getTopLeft(find.text(AppStrings.upcomingVisitsLabel)).dy,
        ),
      );
    });

    testWidgets('[표시하기]는 빈 시트를 열고, 빈 글·빈칸만으로는 저장이 눌리지 않는다', (tester) async {
      final server = _Server(noShowCount: 1);
      final setup = await _openPet(tester, server, ownerTab: true);

      await tester.tap(find.byKey(const ValueKey('caution-set')));
      await tester.pumpAndSettle();
      expect(tester.widget<TextField>(find.byKey(_reasonKey)).controller!.text, '');
      expect(tester.widget<AppButton>(_button(AppStrings.save)).onPressed, isNull);

      await tester.enterText(find.byKey(_reasonKey), '   ');
      await tester.pump();
      expect(tester.widget<AppButton>(_button(AppStrings.save)).onPressed, isNull);
      await tester.testTextInput.receiveAction(TextInputAction.done);
      await _settle(tester);

      expect(_count(setup, 'PUT $_cautionPath'), 0);
      expect(find.text(AppStrings.cautionSheetTitle), findsOneWidget);
    });

    testWidgets('사유를 적어 저장하면 시트가 닫히고 줄에 사유와 기한이 보인다', (tester) async {
      final server = _Server();
      final setup = await _openPet(tester, server, ownerTab: true);

      await tester.tap(find.byKey(const ValueKey('caution-set')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(_reasonKey), '  예약 시간에 늦게 와요 ');
      await tester.pump();
      await tester.tap(_button(AppStrings.save));
      await _settle(tester);

      expect(server.bodies.single, {'reason': '예약 시간에 늦게 와요'});
      expect(_count(setup, 'PUT $_cautionPath'), 1);
      expect(find.text(AppStrings.cautionSheetTitle), findsNothing);
      expect(find.text('예약 시간에 늦게 와요'), findsOneWidget);
      expect(find.text('2027년 11월 14일까지 보여요'), findsOneWidget);
      expect(find.byKey(const ValueKey('caution-set')), findsNothing);
    });

    testWidgets('노쇼가 2번이면 알리고 시트의 사유를 "노쇼 2번"으로 채워 연다 — 저절로 표시하지 않는다', (
      tester,
    ) async {
      final server = _Server(noShowCount: 2);
      final setup = await _openPet(tester, server, ownerTab: true);
      expect(find.text('노쇼가 2번 있어요'), findsOneWidget);
      expect(_count(setup, 'PUT $_cautionPath'), 0);

      await tester.tap(find.byKey(const ValueKey('caution-set')));
      await tester.pumpAndSettle();

      expect(
        tester.widget<TextField>(find.byKey(_reasonKey)).controller!.text,
        '노쇼 2번',
      );
      await tester.tap(_button(AppStrings.save));
      await _settle(tester);
      expect(server.bodies.single, {'reason': '노쇼 2번'});
    });

    testWidgets('노쇼가 1번이면 제안하지 않는다', (tester) async {
      await _openPet(tester, _Server(noShowCount: 1), ownerTab: true);

      expect(find.textContaining('노쇼가'), findsNothing);
      expect(find.text(AppStrings.cautionNone), findsOneWidget);
    });

    testWidgets('사유는 100자까지만 들어가고, 붙여넣은 줄바꿈은 한 줄이 된다', (tester) async {
      final server = _Server();
      await _openPet(tester, server, ownerTab: true);
      await tester.tap(find.byKey(const ValueKey('caution-set')));
      await tester.pumpAndSettle();

      await tester.enterText(find.byKey(_reasonKey), '가' * 101);
      await tester.pump();
      expect(
        tester.widget<TextField>(find.byKey(_reasonKey)).controller!.text,
        '가' * 100,
      );

      await tester.enterText(find.byKey(_reasonKey), '노쇼\n두 번\t있음');
      await tester.pump();
      await tester.tap(_button(AppStrings.save));
      await _settle(tester);

      final sent = server.bodies.single['reason'] as String;
      expect(sent.contains('\n') || sent.contains('\t'), isFalse);
      expect(sent.replaceAll(' ', ''), '노쇼두번있음');
    });

    testWidgets('저장을 연타해도 한 번만 보낸다', (tester) async {
      final gate = Completer<void>();
      final server = _Server()
        ..onWrite = (key) async {
          await gate.future;
          return null;
        };
      final setup = await _openPet(tester, server, ownerTab: true);
      await tester.tap(find.byKey(const ValueKey('caution-set')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(_reasonKey), '무단 취소');
      await tester.pump();

      await tester.tap(_button(AppStrings.save));
      await tester.pump();
      expect(tester.widget<AppButton>(_button(AppStrings.save)).busy, isTrue);
      await tester.tap(_button(AppStrings.save));
      await tester.pump();
      gate.complete();
      await _settle(tester);

      expect(_count(setup, 'PUT $_cautionPath'), 1);
    });

    testWidgets('실패하면 시트가 남고 원인 문구가 보인다 — 사유는 문구에 없다', (tester) async {
      final server = _Server()..onWrite = (key) => _error(500, 'INTERNAL');
      await _openPet(tester, server, ownerTab: true);
      await tester.tap(find.byKey(const ValueKey('caution-set')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(_reasonKey), '무단 취소');
      await tester.pump();

      await tester.tap(_button(AppStrings.save));
      await _settle(tester);

      expect(find.text(AppStrings.cautionSheetTitle), findsOneWidget);
      expect(find.text(_serverError()), findsOneWidget);
      expect(_serverError().contains('무단 취소'), isFalse);
      expect(
        tester.widget<TextField>(find.byKey(_reasonKey)).controller!.text,
        '무단 취소',
      );
      expect(tester.widget<AppButton>(_button(AppStrings.save)).busy, isFalse);
    });

    testWidgets('표시가 있으면 ··· 에서 사유를 고친다 — 시트가 지금 사유로 열린다', (tester) async {
      final server = _Server(caution: cautionJson(reason: '노쇼 3번'));
      await _openPet(tester, server, ownerTab: true);
      expect(find.text('노쇼 3번'), findsOneWidget);

      await tester.tap(find.bySemanticsLabel(AppStrings.cautionMore));
      await tester.pumpAndSettle();
      await tester.tap(find.text(AppStrings.cautionEdit));
      await tester.pumpAndSettle();
      expect(
        tester.widget<TextField>(find.byKey(_reasonKey)).controller!.text,
        '노쇼 3번',
      );
      await tester.enterText(find.byKey(_reasonKey), '노쇼 4번');
      await tester.pump();
      await tester.tap(_button(AppStrings.save));
      await _settle(tester);

      expect(server.bodies.single, {'reason': '노쇼 4번'});
      expect(find.text('노쇼 4번'), findsOneWidget);
    });

    testWidgets('[주의 표시 지우기]는 한 번 묻고, [취소]하면 지우지 않는다', (tester) async {
      final server = _Server(caution: cautionJson());
      final setup = await _openPet(tester, server, ownerTab: true);

      await tester.tap(find.bySemanticsLabel(AppStrings.cautionMore));
      await tester.pumpAndSettle();
      await tester.tap(find.text(AppStrings.cautionClear));
      await tester.pumpAndSettle();
      expect(find.text(AppStrings.cautionClearConfirm), findsOneWidget);
      await tester.tap(_button(AppStrings.cancel));
      await _settle(tester);

      expect(_count(setup, 'DELETE $_cautionPath'), 0);
      expect(find.text('노쇼 2번'), findsOneWidget);
    });

    testWidgets('··· 의 [주의 표시 지우기]는 확인한 뒤 지우고 줄이 "표시하지 않았어요"로 돌아간다', (tester) async {
      final server = _Server(caution: cautionJson());
      final setup = await _openPet(tester, server, ownerTab: true);

      await tester.tap(find.bySemanticsLabel(AppStrings.cautionMore));
      await tester.pumpAndSettle();
      await tester.tap(find.text(AppStrings.cautionClear));
      await tester.pumpAndSettle();
      await tester.tap(_button(AppStrings.cautionClear));
      await _settle(tester);

      expect(_count(setup, 'DELETE $_cautionPath'), 1);
      expect(find.text(AppStrings.cautionNone), findsOneWidget);
    });

    testWidgets('지우기가 실패하면 스낵바로 알리고 줄은 남는다', (tester) async {
      final server = _Server(caution: cautionJson())
        ..onWrite = (key) => _error(500, 'INTERNAL');
      await _openPet(tester, server, ownerTab: true);

      await tester.tap(find.bySemanticsLabel(AppStrings.cautionMore));
      await tester.pumpAndSettle();
      await tester.tap(find.text(AppStrings.cautionClear));
      await tester.pumpAndSettle();
      await tester.tap(_button(AppStrings.cautionClear));
      await _settle(tester);

      expect(find.text(_serverError()), findsOneWidget);
      expect(find.text('노쇼 2번'), findsOneWidget);
    });

    testWidgets('골든 — 보호자 탭, 주의 고객', (tester) async {
      final server = _Server(caution: cautionJson(), noShowCount: 2);
      await _openPet(tester, server, ownerTab: true);
      tester.view.physicalSize = const Size(390, 1200);
      await tester.pumpAndSettle();

      await expectLater(
        find.byKey(ScreenKeys.petDetail),
        matchesGoldenFile('goldens/pet_detail_caution.png'),
      );
    });
  });

  group('고객 목록', () {
    Future<void> openList(WidgetTester tester, _Server server) async {
      final setup = CustomerTestSetup(
        (options, body) =>
            server.handle('${options.method} ${options.path}', body),
      );
      addTearDown(setup.container.dispose);
      await tester.pumpWidget(customerRouterApp(setup.container));
      await tester.pumpAndSettle();
      await tester.tap(find.text(AppStrings.tabCustomers));
      await tester.pumpAndSettle();
    }

    testWidgets('주의 표시가 살아 있는 가족의 줄에 "주의"가 붙는다', (tester) async {
      await openList(tester, _Server(caution: cautionJson()));

      expect(find.text('김민지 · ··5678 · 주의'), findsOneWidget);
    });

    testWidgets('표시가 없으면 붙지 않는다', (tester) async {
      await openList(tester, _Server());

      expect(find.text('김민지 · ··5678'), findsOneWidget);
      expect(find.textContaining('주의'), findsNothing);
    });
  });
}

// 반려동물 상세 [보호자] 탭의 보호자 계정 연결 줄 — 보이기·없기·끊기(⑦-3).
import 'dart:async';

import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

const _linkPath = '/v1/shops/3/customers/7/guardian-link';
const _linkedText = '보호자 계정 연결됨 · 11월 13일';

/// 가짜 서버 — 연결 조회([link])와 끊기([onDelete])의 응답을 테스트가 바꾼다.
class _Server {
  FutureOr<FakeResponse> Function() link = () =>
      FakeResponse(statusCode: 200, data: guardianLinkJson());
  FutureOr<FakeResponse> Function() onDelete = () =>
      const FakeResponse(statusCode: 204);

  FutureOr<FakeResponse> handle(String key) {
    switch (key) {
      case 'GET /v1/shops/3/pets/11':
        return FakeResponse(statusCode: 200, data: petDetailJson());
      case 'GET /v1/shops/3/pets/12':
        return FakeResponse(
          statusCode: 200,
          data: petDetailJson(pet: petJson(petId: 12, name: '두부')),
        );
      case 'GET /v1/shops/3/customers/7':
        return FakeResponse(
          statusCode: 200,
          data: customerDetailJson(noShowCount: 2),
        );
      case 'GET $_linkPath':
        return link();
      case 'DELETE $_linkPath':
        return onDelete();
    }
    // 홈(캘린더 탭)의 요청은 그냥 실패시킨다.
    return const FakeResponse(statusCode: 500, data: 'x');
  }
}

FakeResponse _error(int status, String code) => FakeResponse(
  statusCode: status,
  data: {'code': code, 'message': 'x'},
);

/// 반려동물 상세를 열고 [보호자] 탭을 누른다. 탭이 길어 화면을 길게 잡는다.
Future<CustomerTestSetup> _openOwnerTab(
  WidgetTester tester,
  _Server server, {
  String role = 'owner',
  int petId = 11,
}) async {
  tester.view.physicalSize = const Size(390, 1600);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  final setup = CustomerTestSetup(
    (options, body) => server.handle('${options.method} ${options.path}'),
    role: role,
  );
  addTearDown(setup.container.dispose);
  await tester.pumpWidget(customerRouterApp(setup.container));
  await tester.pumpAndSettle();
  setup.container.read(routerProvider).push('/pets/$petId');
  await tester.pumpAndSettle();
  await tester.tap(find.text(AppStrings.petTabOwner));
  await tester.pumpAndSettle();
  return setup;
}

Finder get _more => find.bySemanticsLabel(AppStrings.guardianLinkMore);

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

int _count(CustomerTestSetup setup, String call) =>
    setup.calls.where((c) => c == call).length;

/// ··· → [연결 끊기] 까지 눌러 확인 시트를 띄운다.
Future<void> _openConfirm(WidgetTester tester) async {
  await tester.tap(_more);
  await tester.pumpAndSettle();
  await tester.tap(find.text(AppStrings.endGuardianLink));
  await tester.pumpAndSettle();
}

/// 보호자 탭의 나머지가 그대로인지.
void _expectOwnerTabIntact() {
  expect(find.text('010-1234-5678'), findsOneWidget);
  expect(find.text(AppStrings.noShowCountLabel), findsOneWidget);
  expect(find.text(AppStrings.upcomingVisitsLabel), findsOneWidget);
  expect(_button(AppStrings.editOwner), findsOneWidget);
  expect(_button(AppStrings.addPet), findsOneWidget);
}

void main() {
  testWidgets('이어진 고객은 "보호자 계정 연결됨 · 11월 13일" 한 줄이 노쇼 횟수와 다가오는 예약 사이에 있다', (
    tester,
  ) async {
    await _openOwnerTab(tester, _Server());

    expect(find.text(_linkedText), findsOneWidget);
    expect(_more, findsOneWidget);
    final row = tester.getTopLeft(find.text(_linkedText)).dy;
    expect(
      row,
      greaterThan(tester.getTopLeft(find.text(AppStrings.noShowCountLabel)).dy),
    );
    expect(
      row,
      lessThan(
        tester.getTopLeft(find.text(AppStrings.upcomingVisitsLabel)).dy,
      ),
    );
    _expectOwnerTabIntact();
  });

  testWidgets('이어지지 않은 고객은 줄이 없고 연결 더 보기도 없다', (tester) async {
    final server = _Server()
      ..link = () => FakeResponse(
        statusCode: 200,
        data: guardianLinkJson(linked: false),
      );
    await _openOwnerTab(tester, server);

    expect(find.textContaining(AppStrings.guardianLinked), findsNothing);
    expect(_more, findsNothing);
    _expectOwnerTabIntact();
  });

  for (final linkedAt in <Object?>[null, 'x', '', 5]) {
    testWidgets('이은 날이 없거나 깨졌으면($linkedAt) "보호자 계정 연결됨" 만 보인다', (tester) async {
      final server = _Server()
        ..link = () => FakeResponse(
          statusCode: 200,
          data: {'linked': true, 'linked_at': linkedAt},
        );
      await _openOwnerTab(tester, server);

      expect(find.text(AppStrings.guardianLinked), findsOneWidget);
      expect(_more, findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }

  for (final failure in [
    const FakeResponse(statusCode: 503, data: 'x'),
    _error(403, 'PERMISSION_DENIED'),
    _error(404, 'CUSTOMER_NOT_FOUND'),
  ]) {
    testWidgets('연결을 읽지 못하면(${failure.statusCode}) 줄만 없고 이름·번호·예약·버튼은 그대로다', (
      tester,
    ) async {
      final server = _Server()..link = () => failure;
      await _openOwnerTab(tester, server);

      expect(find.textContaining(AppStrings.guardianLinked), findsNothing);
      expect(_more, findsNothing);
      expect(_button(AppStrings.retry), findsNothing);
      _expectOwnerTabIntact();
    });
  }

  testWidgets('연결을 읽는 중에는 줄이 없고, 오면 보인다', (tester) async {
    final gate = Completer<FakeResponse>();
    final server = _Server()..link = () => gate.future;
    await _openOwnerTab(tester, server);

    expect(find.textContaining(AppStrings.guardianLinked), findsNothing);
    _expectOwnerTabIntact();

    gate.complete(FakeResponse(statusCode: 200, data: guardianLinkJson()));
    await tester.pumpAndSettle();
    expect(find.text(_linkedText), findsOneWidget);
  });

  testWidgets('··· 를 누르면 [연결 끊기] 하나가 있는 시트가 뜬다', (tester) async {
    await _openOwnerTab(tester, _Server());

    await tester.tap(_more);
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.endGuardianLink), findsOneWidget);
    expect(find.text(AppStrings.endGuardianLinkConfirm), findsNothing);
  });

  testWidgets('확인 시트의 글은 설계의 글자 그대로이고, 취소하면 DELETE 를 보내지 않고 줄이 남는다', (
    tester,
  ) async {
    final setup = await _openOwnerTab(tester, _Server());

    await _openConfirm(tester);
    expect(
      find.text('보호자가 지난 기록을 더는 볼 수 없어요. 알림장을 다시 보내면 다시 이을 수 있어요.'),
      findsOneWidget,
    );
    expect(_button(AppStrings.endGuardianLink), findsOneWidget);
    await tester.tap(_button(AppStrings.cancel));
    await tester.pumpAndSettle();

    expect(_count(setup, 'DELETE $_linkPath'), 0);
    expect(find.text(_linkedText), findsOneWidget);
  });

  testWidgets('확인하면 DELETE 를 한 번 보내고 "보호자 연결을 끊었어요." 를 알리고 줄이 사라진다', (
    tester,
  ) async {
    final server = _Server();
    server.onDelete = () {
      server.link = () => FakeResponse(
        statusCode: 200,
        data: guardianLinkJson(linked: false),
      );
      return const FakeResponse(statusCode: 204);
    };
    final setup = await _openOwnerTab(tester, server);

    await _openConfirm(tester);
    await tester.tap(_button(AppStrings.endGuardianLink));
    await tester.pumpAndSettle();

    expect(_count(setup, 'DELETE $_linkPath'), 1);
    expect(find.text('보호자 연결을 끊었어요.'), findsOneWidget);
    expect(find.textContaining(AppStrings.guardianLinked), findsNothing);
    expect(_more, findsNothing);
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
    _expectOwnerTabIntact();
  });

  testWidgets('이미 끊긴 연결이면(404) "이미 끊긴 연결이에요." 를 알리고 줄이 사라진다', (tester) async {
    final server = _Server();
    server.onDelete = () {
      server.link = () => FakeResponse(
        statusCode: 200,
        data: guardianLinkJson(linked: false),
      );
      return _error(404, 'GUARDIAN_LINK_NOT_FOUND');
    };
    await _openOwnerTab(tester, server);

    await _openConfirm(tester);
    await tester.tap(_button(AppStrings.endGuardianLink));
    await tester.pumpAndSettle();

    expect(find.text('이미 끊긴 연결이에요.'), findsOneWidget);
    expect(find.textContaining(AppStrings.guardianLinked), findsNothing);
  });

  testWidgets('끊기가 실패하면(503) 원인 문구를 알리고 줄이 남는다', (tester) async {
    final server = _Server()
      ..onDelete = () => const FakeResponse(statusCode: 503, data: 'x');
    await _openOwnerTab(tester, server);

    await _openConfirm(tester);
    await tester.tap(_button(AppStrings.endGuardianLink));
    await tester.pumpAndSettle();

    expect(find.text('서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.'), findsOneWidget);
    expect(find.text('보호자 연결을 끊었어요.'), findsNothing);
    expect(find.text(_linkedText), findsOneWidget);
    expect(_more, findsOneWidget);
  });

  testWidgets('권한이 없으면(403 PERMISSION_DENIED) "이 작업을 할 권한이 없어요." 를 알리고 줄이 남는다', (
    tester,
  ) async {
    final server = _Server()
      ..onDelete = () => _error(403, 'PERMISSION_DENIED');
    await _openOwnerTab(tester, server);

    await _openConfirm(tester);
    await tester.tap(_button(AppStrings.endGuardianLink));
    await tester.pumpAndSettle();

    expect(find.text('이 작업을 할 권한이 없어요.'), findsOneWidget);
    expect(find.text(_linkedText), findsOneWidget);
  });

  testWidgets('확인을 빠르게 두 번 눌러도 DELETE 는 한 번이고 화면이 닫히지 않는다', (tester) async {
    final gate = Completer<FakeResponse>();
    final server = _Server()..onDelete = () => gate.future;
    final setup = await _openOwnerTab(tester, server);

    await _openConfirm(tester);
    // 시트가 닫히기 전에 같은 자리를 한 번 더 누른다.
    final confirm = tester.getCenter(_button(AppStrings.endGuardianLink));
    await tester.tapAt(confirm);
    await tester.tapAt(confirm);
    await tester.pumpAndSettle();

    expect(_count(setup, 'DELETE $_linkPath'), 1);
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);

    gate.complete(const FakeResponse(statusCode: 204));
    await tester.pumpAndSettle();
    expect(_count(setup, 'DELETE $_linkPath'), 1);
  });

  testWidgets('끊는 동안 ··· 는 눌리지 않는다', (tester) async {
    final gate = Completer<FakeResponse>();
    final server = _Server()..onDelete = () => gate.future;
    final setup = await _openOwnerTab(tester, server);

    await _openConfirm(tester);
    await tester.tap(_button(AppStrings.endGuardianLink));
    await tester.pumpAndSettle();
    await tester.tap(_more, warnIfMissed: false);
    await tester.pumpAndSettle();

    expect(
      find.text(AppStrings.endGuardianLink),
      findsNothing,
      reason: '시트가 열리지 않는다',
    );

    gate.complete(const FakeResponse(statusCode: 204));
    await tester.pumpAndSettle();
    expect(_count(setup, 'DELETE $_linkPath'), 1);
  });

  testWidgets('끊는 도중 화면을 떠나도 예외가 없다', (tester) async {
    final gate = Completer<FakeResponse>();
    final server = _Server()..onDelete = () => gate.future;
    final setup = await _openOwnerTab(tester, server);

    await _openConfirm(tester);
    await tester.tap(_button(AppStrings.endGuardianLink));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).pop();
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.petDetail), findsNothing);

    gate.complete(const FakeResponse(statusCode: 204));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('보호자 연결을 끊었어요.'), findsNothing);
  });

  testWidgets('직원에게도 줄이 있고 연결을 끊을 수 있다', (tester) async {
    final server = _Server();
    server.onDelete = () {
      server.link = () => FakeResponse(
        statusCode: 200,
        data: guardianLinkJson(linked: false),
      );
      return const FakeResponse(statusCode: 204);
    };
    final setup = await _openOwnerTab(tester, server, role: 'staff');

    expect(find.text(_linkedText), findsOneWidget);
    await _openConfirm(tester);
    await tester.tap(_button(AppStrings.endGuardianLink));
    await tester.pumpAndSettle();

    expect(_count(setup, 'DELETE $_linkPath'), 1);
    expect(find.textContaining(AppStrings.guardianLinked), findsNothing);
  });

  testWidgets('당겨서 새로고침하면 연결을 다시 읽는다', (tester) async {
    final server = _Server();
    final setup = await _openOwnerTab(tester, server);
    expect(_count(setup, 'GET $_linkPath'), 1);

    // 그 사이 보호자가 끊었다.
    server.link = () => FakeResponse(
      statusCode: 200,
      data: guardianLinkJson(linked: false),
    );
    await tester.fling(find.text('콩이'), const Offset(0, 400), 1000);
    await tester.pumpAndSettle();

    expect(_count(setup, 'GET $_linkPath'), 2);
    expect(find.textContaining(AppStrings.guardianLinked), findsNothing);
  });

  testWidgets('같은 보호자의 다른 아이의 상세에서도 그 고객의 줄이 보인다', (tester) async {
    final setup = await _openOwnerTab(tester, _Server(), petId: 12);

    expect(find.text(_linkedText), findsOneWidget);
    expect(_count(setup, 'GET $_linkPath'), 1);
  });

  testWidgets('끊은 뒤 다시 읽기가 실패하면 낡은 "연결됨" 줄을 남기지 않는다', (tester) async {
    final server = _Server();
    server.onDelete = () {
      server.link = () => const FakeResponse(statusCode: 503, data: 'x');
      return const FakeResponse(statusCode: 204);
    };
    final setup = await _openOwnerTab(tester, server);

    await _openConfirm(tester);
    await tester.tap(_button(AppStrings.endGuardianLink));
    await tester.pumpAndSettle();

    expect(_count(setup, 'DELETE $_linkPath'), 1);
    expect(find.text('보호자 연결을 끊었어요.'), findsOneWidget);
    expect(find.textContaining(AppStrings.guardianLinked), findsNothing);
    expect(_more, findsNothing);
    _expectOwnerTabIntact();
  });

  testWidgets('당겨서 새로고침한 연결 읽기가 실패하면 낡은 줄을 남기지 않고, 다시 되면 보인다', (tester) async {
    final server = _Server();
    await _openOwnerTab(tester, server);
    expect(find.text(_linkedText), findsOneWidget);

    server.link = () => const FakeResponse(statusCode: 503, data: 'x');
    await tester.fling(find.text('콩이'), const Offset(0, 400), 1000);
    await tester.pumpAndSettle();
    expect(find.textContaining(AppStrings.guardianLinked), findsNothing);
    _expectOwnerTabIntact();

    server.link = () =>
        FakeResponse(statusCode: 200, data: guardianLinkJson());
    await tester.fling(find.text('콩이'), const Offset(0, 400), 1000);
    await tester.pumpAndSettle();
    expect(find.text(_linkedText), findsOneWidget);
  });
}

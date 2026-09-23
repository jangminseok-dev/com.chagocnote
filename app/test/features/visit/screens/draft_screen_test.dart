import 'dart:async';

import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_chip.dart';
import 'package:chagocnote/features/home/state/today_provider.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 23))];
const _text = '안녕하세요 내일 2시반에 두부 부분미용 될까요?';

Future<Closed<DateTime>> _open(
  WidgetTester tester,
  CustomerTestSetup setup, {
  String path = '/visits/draft',
  Object? extra = _text,
}) {
  useTallView(tester);
  return pushOnHome<DateTime>(tester, setup, path, extra: extra);
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

Finder _guessChips() => find.byWidgetPredicate(
  (w) => w is AppChip && w.label == AppStrings.draftGuessed,
);

/// `Clipboard.getData`가 [text]를 돌려주게 한다(null 이면 빈 클립보드).
void _mockClipboard(WidgetTester tester, String? text) {
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(SystemChannels.platform, (call) async {
        if (call.method == 'Clipboard.getData') {
          return text == null ? null : {'text': text};
        }
        return null;
      });
  addTearDown(
    () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, null),
  );
}

void main() {
  testWidgets(
    '후보가 하나면 고른 상태로 보이고 짐작한 칸에 표시가 붙으며, [예약 이어서]가 ②를 채워 열고 저장한 날짜를 돌려준다',
    (tester) async {
      final backend = VisitTestBackend();
      Map<String, dynamic>? draftBody;
      backend.routes['POST /v1/shops/3/visit-drafts'] = (o, body) {
        draftBody = bodyOf(body);
        return FakeResponse(
          statusCode: 200,
          data: visitDraftJson(time: '14:30', guessedTime: true, menuIds: [3]),
        );
      };
      Map<String, dynamic>? sent;
      backend.routes['POST /v1/shops/3/visits'] = (o, body) {
        sent = bodyOf(body);
        return FakeResponse(statusCode: 201, data: savedJson([visitJson()]));
      };
      final setup = CustomerTestSetup(backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      final result = await _open(tester, setup);

      expect(find.byKey(ScreenKeys.visitDraft), findsOneWidget);
      expect(draftBody, {'text': _text});
      expect(find.text(_text), findsOneWidget);
      expect(find.text('이수진 · ··5678'), findsOneWidget);
      expect(find.text('두부'), findsOneWidget);
      expect(find.text('10월 2일 금'), findsOneWidget);
      expect(find.text('14:30'), findsOneWidget);
      expect(find.text('부분 미용'), findsOneWidget);
      // 짐작 표시는 시각에만 붙는다.
      expect(_guessChips(), findsOneWidget);
      expect(
        tester.widget<AppButton>(_button(AppStrings.draftContinue)).onPressed,
        isNotNull,
      );

      await tester.tap(_button(AppStrings.draftContinue));
      await settle(tester);
      expect(find.byKey(ScreenKeys.registerVisit), findsOneWidget);
      expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
      expect(
        find.text(AppStrings.saveReservation('10월 2일 금 14:30')),
        findsOneWidget,
      );
      expect(find.text(AppStrings.durationText(90)), findsOneWidget);

      await tester.tap(
        find.byWidgetPredicate(
          (w) => w is AppButton && w.label.startsWith('예약 저장'),
        ),
      );
      await settle(tester);
      expect(sent?['customer_id'], 7);
      expect(sent?['pet_ids'], [11]);
      expect(sent?['menu_ids'], [3]);
      // ②가 닫히면 초안 화면도 그 날짜로 닫힌다.
      expect(result.closed, isTrue);
      expect(result.value, DateTime(2026, 10, 2));
      expect(find.byKey(ScreenKeys.visitDraft), findsNothing);
    },
  );

  testWidgets('메뉴표를 아직 못 읽었으면 [예약 이어서]가 메뉴표를 기다린 뒤 메뉴를 채워 연다', (tester) async {
    final backend = VisitTestBackend();
    final menus = Completer<FakeResponse>();
    backend.routes['GET /v1/shops/3/menus'] = (o, b) => menus.future;
    backend.routes['POST /v1/shops/3/visit-drafts'] = (o, b) =>
        FakeResponse(statusCode: 200, data: visitDraftJson(menuIds: [3]));
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    expect(find.text('부분 미용'), findsNothing); // 메뉴표 전이라 메뉴 줄은 비어 있다

    await tester.tap(_button(AppStrings.draftContinue));
    await tester.pump();
    expect(find.byKey(ScreenKeys.registerVisit), findsNothing); // 메뉴표를 기다린다
    menus.complete(
      FakeResponse(statusCode: 200, data: {'items': defaultMenusJson()}),
    );
    await settle(tester);
    expect(find.byKey(ScreenKeys.registerVisit), findsOneWidget);
    // 글에 있던 "부분 미용"(90분)이 ②에 채워져 있다.
    expect(find.text(AppStrings.durationText(90)), findsOneWidget);
  });

  testWidgets('후보가 여럿이면 골라야 [예약 이어서]가 열리고, 고른 보호자의 ②로 간다', (tester) async {
    final backend = VisitTestBackend();
    backend.routes['POST /v1/shops/3/visit-drafts'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: visitDraftJson(
        guessedWho: true,
        petIds: [],
        candidates: [
          draftCandidateJson(),
          draftCandidateJson(
            customerId: 8,
            name: '김민지',
            phoneMasked: '010-98··-4321',
            pets: [draftPetJson(petId: 21, name: '콩이')],
            matchedPetIds: [],
          ),
        ],
      ),
    );
    backend.routes['GET /v1/shops/3/customers/8'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: customerDetailJson(
        customer: customerJson(
          customerId: 8,
          name: '김민지',
          phone: '01098764321',
        ),
        pets: [petJson(petId: 21, name: '콩이')],
      ),
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(
      tester.widget<AppButton>(_button(AppStrings.draftContinue)).onPressed,
      isNull,
    );
    // 누구인지 짐작이라 보호자 줄에도 표시가 붙는다.
    expect(_guessChips(), findsOneWidget);

    await tester.tap(find.text('김민지 · ··4321'));
    await settle(tester);
    expect(
      tester.widget<AppButton>(_button(AppStrings.draftContinue)).onPressed,
      isNotNull,
    );

    await tester.tap(_button(AppStrings.draftContinue));
    await settle(tester);
    expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
    expect(find.text('김민지 · ··4321'), findsOneWidget);
  });

  testWidgets('후보가 없으면 [고객 찾기]로 ①에 가고, 고른 뒤 ②가 초안의 날짜·시각·메뉴로 채워진다', (
    tester,
  ) async {
    final backend = VisitTestBackend();
    backend.routes['POST /v1/shops/3/visit-drafts'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: visitDraftJson(
        candidates: [],
        petIds: [],
        time: '11:00',
        menuIds: [1],
      ),
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(find.text(AppStrings.draftNoCandidates), findsOneWidget);
    expect(_button(AppStrings.draftContinue), findsNothing);
    await tester.tap(_button(AppStrings.draftFindCustomer));
    await settle(tester);
    expect(find.text(AppStrings.reserveWhoTitle), findsOneWidget);

    await tester.tap(find.text('두부').first);
    await settle(tester);
    expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
    expect(
      find.text(AppStrings.saveReservation('10월 2일 금 11:00')),
      findsOneWidget,
    );
    expect(find.text(AppStrings.durationText(60)), findsOneWidget);
  });

  testWidgets('날짜·시각·메뉴를 못 찾으면 빈 표시를 보이고, 해석에 실패하면 문구와 [다시 시도]를 보인다', (
    tester,
  ) async {
    final backend = VisitTestBackend();
    var calls = 0;
    backend.routes['POST /v1/shops/3/visit-drafts'] = (o, b) {
      calls++;
      if (calls == 1) {
        return const FakeResponse(
          statusCode: 422,
          data: {'code': 'VALIDATION_ERROR', 'message': 'x'},
        );
      }
      return FakeResponse(
        statusCode: 200,
        data: visitDraftJson(date: null, time: null, menuIds: []),
      );
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(find.text('입력한 내용을 확인해 주세요.'), findsOneWidget);
    await tester.tap(_button(AppStrings.retry));
    await settle(tester);

    expect(calls, 2);
    expect(find.text('이수진 · ··5678'), findsOneWidget);
    expect(find.text(AppStrings.draftEmptyValue), findsNWidgets(3));
    expect(_guessChips(), findsNothing);
  });

  testWidgets('붙여넣은 글이 1000자를 넘으면 앞 1000자만 보낸다', (tester) async {
    final backend = VisitTestBackend();
    Map<String, dynamic>? draftBody;
    backend.routes['POST /v1/shops/3/visit-drafts'] = (o, body) {
      draftBody = bodyOf(body);
      return FakeResponse(statusCode: 200, data: visitDraftJson());
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(
      tester,
      setup,
      path: '/visits/new?date=2026-10-02',
      extra: null,
    );

    _mockClipboard(tester, '가' * 1200);
    await tester.tap(_button(AppStrings.pasteFromKakao));
    await settle(tester);
    expect((draftBody?['text'] as String).length, 1000);
  });

  testWidgets('①의 [카톡 붙여넣기]는 클립보드 글로 초안 화면을 열고, 비어 있으면 문구를 보인다', (
    tester,
  ) async {
    final backend = VisitTestBackend();
    Map<String, dynamic>? draftBody;
    backend.routes['POST /v1/shops/3/visit-drafts'] = (o, body) {
      draftBody = bodyOf(body);
      return FakeResponse(statusCode: 200, data: visitDraftJson());
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    final result = await _open(
      tester,
      setup,
      path: '/visits/new?date=2026-10-02',
      extra: null,
    );

    _mockClipboard(tester, null);
    await tester.tap(_button(AppStrings.pasteFromKakao));
    await settle(tester);
    expect(find.text(AppStrings.clipboardEmpty), findsOneWidget);
    expect(find.byKey(ScreenKeys.visitDraft), findsNothing);

    _mockClipboard(tester, '  $_text  ');
    await tester.tap(_button(AppStrings.pasteFromKakao));
    await settle(tester);
    expect(find.byKey(ScreenKeys.visitDraft), findsOneWidget);
    expect(draftBody, {'text': _text});

    // 초안 → ② → 저장하면 ①도 그 날짜로 닫힌다(홈이 그날을 고른다).
    await tester.tap(_button(AppStrings.draftContinue));
    await settle(tester);
    await tester.tap(
      find.byWidgetPredicate(
        (w) => w is AppButton && w.label.startsWith('예약 저장'),
      ),
    );
    await settle(tester);
    expect(result.closed, isTrue);
    expect(result.value, DateTime(2026, 10, 2));
    expect(find.byKey(ScreenKeys.registerVisit), findsNothing);
  });
}

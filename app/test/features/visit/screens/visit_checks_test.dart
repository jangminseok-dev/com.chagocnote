// "확인할 것"(③-B) — 묶음 위젯과 그것이 붙는 세 화면(예약 등록·방문 상세·하루 목록).
// 알리기만 하고 막지 않는다: 읽는 중·읽기 실패면 묶음이 없고 저장은 그대로 된다.
import 'dart:async';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/error/error_messages.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/features/visit/api/check_models.dart';
import 'package:chagocnote/features/visit/screens/visit_checks_block.dart';
import 'package:chagocnote/features/visit/state/check_rules.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/consent_fixtures.dart';
import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/golden_frame.dart';
import '../../../support/load_fonts.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 23))];

const _checksPath = 'GET /v1/shops/3/visit-checks';
const _consentPath = 'PUT /v1/shops/3/pets/11/grooming-consent';

final _noShow = checkJson('no_show', detail: {'count': 2});
final _caution = checkJson(
  'caution',
  detail: {'reason': '노쇼 3번', 'until': '2027-11-14'},
);
final _first = checkJson('first_visit', scope: 'pet');
final _consent = checkJson(
  'consent',
  scope: 'pet',
  detail: {
    'reasons': ['senior', 'conditions'],
    'state': 'missing',
    'received_on': null,
  },
);
final _conditions = checkJson(
  'conditions',
  scope: 'pet',
  detail: {
    'items': [
      {'label': '심장병', 'note': '약 복용 중'},
      {'label': '슬개골', 'note': null},
    ],
  },
);

const _consentLine = '미용 동의서를 받아 주세요 (노령 · 지병)';
const _formsPath = 'POST /v1/shops/3/consent-forms';
final _consentSent = checkJson(
  'consent',
  scope: 'pet',
  detail: {
    'reasons': ['senior', 'conditions'],
    'state': 'missing',
    'received_on': null,
    'form_sent_on': '2026-11-16',
  },
);

List<VisitCheck> _parsed(List<Map<String, dynamic>> json) => parseChecks(json);

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

Finder _saveButton() => find.byWidgetPredicate(
  (w) => w is AppButton && w.label.startsWith('예약 저장'),
);

Future<void> _tapLabel(WidgetTester tester, String label) async {
  await tester.tap(find.bySemanticsLabel(label).first);
  await settle(tester);
}

Future<void> _pumpBlock(WidgetTester tester, Widget block) => tester.pumpWidget(
  MaterialApp(
    home: Scaffold(body: SingleChildScrollView(child: block)),
  ),
);

/// 예약 등록을 열고 두부네(보호자 7, 아이 11 하나)를 고른다 — 아이가 하나라 미리 골라진다.
Future<Closed<DateTime>> _openRegister(
  WidgetTester tester,
  CustomerTestSetup setup,
) async {
  useTallView(tester);
  final result = await pushOnHome<DateTime>(
    tester,
    setup,
    '/visits/new?date=2026-10-02',
  );
  await tester.tap(find.text('두부').first);
  await settle(tester);
  return result;
}

List<Map<String, List<String>>> _checkQueries(CustomerTestSetup setup) => [
  for (final r in setup.adapter.requests)
    if (r.path == '/v1/shops/3/visit-checks') r.uri.queryParametersAll,
];

/// 방문 101(두부, 아이 11)의 상세를 [checks]로 보이는 서버. 동의를 적으면 동의 줄이 빠진다.
class _DetailServer {
  _DetailServer(this.checks) {
    backend = VisitTestBackend({
      'GET /v1/shops/3/visits/101': (o, b) =>
          FakeResponse(statusCode: 200, data: visitDetailJson(checks: checks)),
      _consentPath: (o, b) {
        checks = [
          for (final c in checks)
            if (c['code'] != 'consent') c,
        ];
        return FakeResponse(statusCode: 200, data: petDetailJson());
      },
      _formsPath: (o, b) => FakeResponse(statusCode: 201, data: formLinkJson()),
      'GET /v1/shops/3/consent-document': (o, b) => FakeResponse(statusCode: 200, data: consentDocumentJson()),
    });
  }

  /// 이 방문의 날(매장 시간대) — 동의서의 기준일로 나간다.
  String get visitDay => (visitDetailJson()['visit'] as Map)['starts_at'].toString().substring(0, 10);

  List<Map<String, dynamic>> checks;
  late final VisitTestBackend backend;
}

Future<void> _openDetail(WidgetTester tester, CustomerTestSetup setup) async {
  useTallView(tester, height: 1400);
  await pushOnHome<Object?>(tester, setup, '/visits/101');
}

void main() {
  setUpAll(loadTestFonts);

  group('묶음', () {
    testWidgets('묶음이 없으면 아무것도 그리지 않는다', (tester) async {
      await _pumpBlock(tester, const VisitChecksBlock(sections: []));

      expect(find.text(AppStrings.checksTitle), findsNothing);
    });

    testWidgets('보호자 묶음과 아이 묶음을 제목·줄로 그린다', (tester) async {
      await _pumpBlock(
        tester,
        VisitChecksBlock(
          sections: [
            CheckSection(checks: _parsed([_caution, _noShow])),
            CheckSection(title: '두부', petId: 11, checks: _parsed([_first])),
          ],
        ),
      );

      expect(find.text(AppStrings.checksTitle), findsOneWidget);
      expect(find.text('주의 고객이에요 · 노쇼 3번'), findsOneWidget);
      expect(find.text('지난 1년 동안 노쇼 2번'), findsOneWidget);
      expect(find.text('두부'), findsOneWidget);
      expect(find.text(AppStrings.checkFirstVisit), findsOneWidget);
    });

    testWidgets('동의 줄의 [받았어요]는 받는 쪽이 있고 아이 묶음일 때만 있다', (tester) async {
      final checks = _parsed([_consent]);
      await _pumpBlock(
        tester,
        VisitChecksBlock(sections: [CheckSection(petId: 11, checks: checks)]),
      );
      expect(find.text(_consentLine), findsOneWidget);
      expect(_button(AppStrings.consentReceived), findsNothing);

      await _pumpBlock(
        tester,
        VisitChecksBlock(
          sections: [CheckSection(checks: checks)],
          onConsent: (_) {},
        ),
      );
      expect(_button(AppStrings.consentReceived), findsNothing);
    });

    testWidgets('[받았어요]는 그 아이를 넘기고, 적는 중이면 눌리지 않는다', (tester) async {
      final received = <int>[];
      Widget block({required bool busy}) => VisitChecksBlock(
        sections: [
          CheckSection(petId: 11, checks: _parsed([_consent])),
        ],
        onConsent: received.add,
        consentBusy: busy,
      );
      await _pumpBlock(tester, block(busy: false));
      await tester.tap(find.byKey(const ValueKey('consent-received-11')));
      expect(received, [11]);

      await _pumpBlock(tester, block(busy: true));
      await tester.tap(find.byKey(const ValueKey('consent-received-11')));
      expect(received, [11]);
    });

    testWidgets('지병 줄은 누르면 메모가 펼쳐지고 다시 누르면 접힌다 — 메모 없는 지병은 펼침에 없다', (
      tester,
    ) async {
      await _pumpBlock(
        tester,
        VisitChecksBlock(
          sections: [
            CheckSection(petId: 11, checks: _parsed([_conditions])),
          ],
        ),
      );
      expect(find.text('지병 · 심장병, 슬개골'), findsOneWidget);
      expect(find.text('심장병 — 약 복용 중'), findsNothing);

      await tester.tap(find.bySemanticsLabel('지병 · 심장병, 슬개골'));
      await tester.pump();
      expect(find.text('심장병 — 약 복용 중'), findsOneWidget);
      expect(find.textContaining('슬개골 —'), findsNothing);

      await tester.tap(find.bySemanticsLabel('지병 · 심장병, 슬개골'));
      await tester.pump();
      expect(find.text('심장병 — 약 복용 중'), findsNothing);
    });

    testWidgets('메모가 하나도 없는 지병 줄은 눌리지 않는다', (tester) async {
      await _pumpBlock(
        tester,
        VisitChecksBlock(
          sections: [
            CheckSection(
              petId: 11,
              checks: _parsed([
                checkJson(
                  'conditions',
                  scope: 'pet',
                  detail: {
                    'items': [
                      {'label': '슬개골', 'note': null},
                      {'label': '피부', 'note': ''},
                    ],
                  },
                ),
              ]),
            ),
          ],
        ),
      );

      expect(find.text('지병 · 슬개골, 피부'), findsOneWidget);
      expect(find.byIcon(Icons.expand_more), findsNothing);
    });

    testWidgets('골든', (tester) async {
      final frame = await pumpGoldenFrame(
        tester,
        SizedBox(
          width: 342,
          child: VisitChecksBlock(
            sections: [
              CheckSection(checks: _parsed([_caution, _noShow])),
              CheckSection(
                title: '두부',
                petId: 11,
                checks: _parsed([_consent, _conditions]),
              ),
              CheckSection(
                title: '보리',
                petId: 12,
                checks: _parsed([
                  _first,
                  checkJson(
                    'long_absence',
                    scope: 'pet',
                    detail: {'days': 200, 'last_visit_on': '2026-04-28'},
                  ),
                ]),
              ),
            ],
            onConsent: (_) {},
            onSend: (_, _) {},
            onSignHere: (_) {},
          ),
        ),
      );
      await tester.tap(find.bySemanticsLabel('지병 · 심장병, 슬개골'));
      await tester.pump();

      await expectLater(
        frame,
        matchesGoldenFile('goldens/visit_checks_block.png'),
      );
    });
  });

  group('예약 등록', () {
    testWidgets('보호자·아이·날짜로 묻고 저장 버튼 위에 묶음을 보인다 — 저장은 그대로 된다', (tester) async {
      final backend = VisitTestBackend({
        _checksPath: (o, b) => FakeResponse(
          statusCode: 200,
          data: checksPreviewJson(
            customer: [_noShow],
            pets: {
              11: [_first, checkJson('vaccination', scope: 'pet')],
            },
          ),
        ),
      });
      final setup = CustomerTestSetup(backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      final result = await _openRegister(tester, setup);

      expect(_checkQueries(setup), [
        {
          'customer_id': ['7'],
          'pet_ids': ['11'],
          'date': ['2026-10-02'],
        },
      ]);
      expect(find.text(AppStrings.checksTitle), findsOneWidget);
      expect(find.text('지난 1년 동안 노쇼 2번'), findsOneWidget);
      expect(find.text(AppStrings.checkFirstVisit), findsOneWidget);
      // 등록 화면에는 [받았어요]가 없다 — 방문 상세에서 한다.
      expect(_button(AppStrings.consentReceived), findsNothing);
      // 묶음은 저장 버튼 위다.
      expect(
        tester.getTopLeft(find.text(AppStrings.checksTitle)).dy,
        lessThan(tester.getTopLeft(find.text(AppStrings.pickTimeFirst)).dy),
      );

      await _tapLabel(tester, '14:00');
      await tester.tap(_saveButton());
      await settle(tester);
      expect(result.closed, isTrue);
    });

    testWidgets('읽지 못하면 묶음도 오류 문구도 없고 저장할 수 있다', (tester) async {
      final backend = VisitTestBackend({
        _checksPath: (o, b) => const FakeResponse(
          statusCode: 500,
          data: {'code': 'INTERNAL', 'message': 'x'},
        ),
      });
      final setup = CustomerTestSetup(backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      final result = await _openRegister(tester, setup);

      expect(_checkQueries(setup), hasLength(1));
      expect(find.text(AppStrings.checksTitle), findsNothing);
      expect(
        find.text(
          messageFor(
            ApiException(statusCode: 500, code: 'INTERNAL', message: 'x'),
          ),
        ),
        findsNothing,
      );

      await _tapLabel(tester, '14:00');
      await tester.tap(_saveButton());
      await settle(tester);
      expect(result.closed, isTrue);
    });

    testWidgets('보이던 묶음을 다시 읽다가 실패하면 낡은 묶음을 숨긴다', (tester) async {
      var fail = false;
      final backend = VisitTestBackend({
        _checksPath: (o, b) => fail
            ? const FakeResponse(
                statusCode: 500,
                data: {'code': 'INTERNAL', 'message': 'x'},
              )
            : FakeResponse(
                statusCode: 200,
                data: checksPreviewJson(customer: [_noShow]),
              ),
      });
      final setup = CustomerTestSetup(backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _openRegister(tester, setup);
      expect(find.text('지난 1년 동안 노쇼 2번'), findsOneWidget);

      fail = true;
      setup.container.invalidate(visitChecksProvider);
      await settle(tester);

      expect(_checkQueries(setup), hasLength(2));
      expect(find.text(AppStrings.checksTitle), findsNothing);
      // 저장 버튼 자리는 그대로다(아직 시각을 고르지 않았다).
      expect(find.text(AppStrings.pickTimeFirst), findsOneWidget);
    });

    testWidgets('읽는 중에도 저장할 수 있다', (tester) async {
      final gate = Completer<FakeResponse>();
      final backend = VisitTestBackend({_checksPath: (o, b) => gate.future});
      final setup = CustomerTestSetup(backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      final result = await _openRegister(tester, setup);

      expect(find.text(AppStrings.checksTitle), findsNothing);
      await _tapLabel(tester, '14:00');
      await tester.tap(_saveButton());
      await settle(tester);

      expect(result.closed, isTrue);
      gate.complete(FakeResponse(statusCode: 200, data: checksPreviewJson()));
      await settle(tester);
    });

    testWidgets('날짜를 바꾸면 새 날짜로 다시 묻고, 늦게 온 앞 날짜의 응답은 보이지 않는다', (tester) async {
      final late = Completer<FakeResponse>();
      final backend = VisitTestBackend({
        _checksPath: (o, b) => o.queryParameters['date'] == '2026-10-02'
            ? late.future
            : FakeResponse(
                statusCode: 200,
                data: checksPreviewJson(customer: [_noShow]),
              ),
      });
      final setup = CustomerTestSetup(backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _openRegister(tester, setup);

      await _tapLabel(tester, '10월 3일 토');
      expect(_checkQueries(setup).map((q) => q['date']!.single), [
        '2026-10-02',
        '2026-10-03',
      ]);
      expect(find.text('지난 1년 동안 노쇼 2번'), findsOneWidget);

      late.complete(
        FakeResponse(
          statusCode: 200,
          data: checksPreviewJson(
            pets: {
              11: [_first],
            },
          ),
        ),
      );
      await settle(tester);

      expect(find.text(AppStrings.checkFirstVisit), findsNothing);
      expect(find.text('지난 1년 동안 노쇼 2번'), findsOneWidget);
    });

    testWidgets('보호자만의 방문은 pet_ids 없이 묻는다', (tester) async {
      final backend = VisitTestBackend({
        _checksPath: (o, b) => FakeResponse(
          statusCode: 200,
          data: checksPreviewJson(
            customer: o.queryParameters.containsKey('pet_ids')
                ? const []
                : [_caution],
          ),
        ),
      });
      final setup = CustomerTestSetup(backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _openRegister(tester, setup);
      expect(find.text(AppStrings.checksTitle), findsNothing);

      await _tapLabel(tester, AppStrings.ownerOnly);

      expect(_checkQueries(setup).last.containsKey('pet_ids'), isFalse);
      expect(find.text('주의 고객이에요 · 노쇼 3번'), findsOneWidget);
    });

    testWidgets('아이가 둘이면 아이 이름으로 나눈다', (tester) async {
      final backend = VisitTestBackend({
        'GET /v1/shops/3/customers/7': (o, b) => FakeResponse(
          statusCode: 200,
          data: customerDetailJson(
            customer: customerJson(name: '이수진'),
            pets: [
              petJson(petId: 11, name: '두부'),
              petJson(petId: 12, name: '보리'),
            ],
          ),
        ),
        _checksPath: (o, b) => FakeResponse(
          statusCode: 200,
          data: checksPreviewJson(
            pets: {
              for (final id in (o.queryParameters['pet_ids'] as List? ?? []))
                id as int: [_first],
            },
          ),
        ),
      });
      final setup = CustomerTestSetup(backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _openRegister(tester, setup);

      await _tapLabel(tester, '두부');
      await _tapLabel(tester, '보리');

      expect(_checkQueries(setup).last['pet_ids'], ['11', '12']);
      expect(find.text(AppStrings.checkFirstVisit), findsNWidgets(2));
      final block = find.byType(VisitChecksBlock);
      expect(
        find.descendant(of: block, matching: find.text('두부')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: block, matching: find.text('보리')),
        findsOneWidget,
      );
    });
  });

  group('방문 상세', () {
    testWidgets('확인할 것이 없으면 묶음이 없다', (tester) async {
      final server = _DetailServer([]);
      final setup = CustomerTestSetup(server.backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _openDetail(tester, setup);

      expect(find.text(AppStrings.checksTitle), findsNothing);
    });

    testWidgets('모르는 항목은 버리고 아는 항목만 보인다 — 지병은 눌러서 메모를 본다', (tester) async {
      final server = _DetailServer([
        _noShow,
        checkJson('vaccination', scope: 'pet', detail: {'due': '2026-12-01'}),
        checkJson('caution', detail: {'until': 3}),
        _conditions,
      ]);
      final setup = CustomerTestSetup(server.backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _openDetail(tester, setup);

      expect(find.text(AppStrings.checksTitle), findsOneWidget);
      expect(find.text('지난 1년 동안 노쇼 2번'), findsOneWidget);
      expect(find.textContaining('주의 고객'), findsNothing);
      await _tapLabel(tester, '지병 · 심장병, 슬개골');
      expect(find.text('심장병 — 약 복용 중'), findsOneWidget);
    });

    testWidgets('[받았어요]는 연타해도 한 번만 적고, 다시 읽어 동의 줄이 사라진다', (tester) async {
      final server = _DetailServer([_consent, _first]);
      final gate = Completer<void>();
      final write = server.backend.routes[_consentPath]!;
      server.backend.routes[_consentPath] = (o, b) async {
        await gate.future;
        return write(o, b);
      };
      final setup = CustomerTestSetup(server.backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _openDetail(tester, setup);
      expect(find.text(_consentLine), findsOneWidget);

      final button = find.byKey(const ValueKey('consent-received-11'));
      await tester.tap(button);
      await tester.pump();
      expect(tester.widget<AppButton>(button).busy, isTrue);
      await tester.tap(button);
      await tester.pump();
      gate.complete();
      await settle(tester);

      expect(setup.calls.where((c) => c == _consentPath), hasLength(1));
      expect(
        bodyOf(
          setup.adapter.lastBodyByPath['/v1/shops/3/pets/11/grooming-consent'],
        ),
        {'received_on': null},
      );
      expect(find.text(_consentLine), findsNothing);
      expect(find.text(AppStrings.checkFirstVisit), findsOneWidget);
    });

    // --- 전자 동의서(⑪) ---

    testWidgets('동의 줄에 버튼 셋이 있고, 보낸 링크가 살아 있으면 [다시 공유]다', (tester) async {
      final server = _DetailServer([_consent]);
      final setup = CustomerTestSetup(server.backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _openDetail(tester, setup);

      expect(_button(AppStrings.consentSend), findsOneWidget);
      expect(_button(AppStrings.consentSignHere), findsOneWidget);
      expect(_button(AppStrings.consentReceived), findsOneWidget);
      expect(_button(AppStrings.consentShareAgain), findsNothing);

      server.checks = [_consentSent];
      setup.container.invalidate(visitDetailProvider);
      await settle(tester);

      expect(find.text('$_consentLine · 11월 16일에 보냈어요'), findsOneWidget);
      expect(_button(AppStrings.consentShareAgain), findsOneWidget);
      expect(_button(AppStrings.consentSend), findsNothing);
    });

    testWidgets('[동의서 보내기]는 방문의 날을 넘기고 주소를 공유 시트에 준다 — 누르기 한 번', (tester) async {
      final server = _DetailServer([_consent]);
      final setup = CustomerTestSetup(server.backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _openDetail(tester, setup);

      await tester.tap(find.byKey(const ValueKey('consent-send-11')));
      await settle(tester);

      expect(bodyOf(setup.adapter.lastBodyByPath['/v1/shops/3/consent-forms']), {
        'pet_ids': [11],
        'for_date': server.visitDay,
      });
      expect(setup.shareSheet.shared, [fakeConsentUrl]);
      expect(setup.shareSheet.origins.single.width, greaterThan(0));
      // 보낸 뒤 확인할 것을 다시 읽는다 — 보낸 날이 실린다.
      expect(setup.calls.where((c) => c == 'GET /v1/shops/3/visits/101'), hasLength(2));
      expect(find.byType(SnackBar), findsNothing);
    });

    testWidgets('손으로 받았다고 적은 아이에게 보내면 무엇을 해야 하는지 말한다', (tester) async {
      final server = _DetailServer([_consent]);
      server.backend.routes[_formsPath] = (o, b) =>
          const FakeResponse(statusCode: 409, data: {'code': 'CONSENT_UP_TO_DATE', 'message': 'x'});
      final setup = CustomerTestSetup(server.backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _openDetail(tester, setup);

      await tester.tap(find.byKey(const ValueKey('consent-send-11')));
      await settle(tester);

      expect(find.text(AppStrings.consentSendUpToDate), findsOneWidget);
      expect(setup.shareSheet.shared, isEmpty);
    });

    testWidgets('공유 창이 실패하면 알리고 다시 누를 수 있다 — 다시 누르면 같은 링크다', (tester) async {
      final server = _DetailServer([_consent]);
      final setup = CustomerTestSetup(server.backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _openDetail(tester, setup);
      setup.shareSheet.error = Exception('채널 오류');

      final button = find.byKey(const ValueKey('consent-send-11'));
      await tester.tap(button);
      await settle(tester);
      expect(find.text(AppStrings.consentShareFailed), findsOneWidget);
      expect(tester.widget<AppButton>(button).busy, isFalse);

      setup.shareSheet.error = null;
      await tester.tap(button);
      await settle(tester);
      expect(setup.shareSheet.shared, [fakeConsentUrl]);
    });

    testWidgets('보내는 중에는 다시 눌리지 않는다', (tester) async {
      final server = _DetailServer([_consent]);
      final gate = Completer<void>();
      final issue = server.backend.routes[_formsPath]!;
      server.backend.routes[_formsPath] = (o, b) async {
        await gate.future;
        return issue(o, b);
      };
      final setup = CustomerTestSetup(server.backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _openDetail(tester, setup);

      final button = find.byKey(const ValueKey('consent-send-11'));
      await tester.tap(button);
      await tester.pump();
      expect(tester.widget<AppButton>(button).busy, isTrue);
      await tester.tap(button);
      await tester.pump();
      gate.complete();
      await settle(tester);

      expect(setup.calls.where((c) => c == _formsPath), hasLength(1));
    });

    testWidgets('[여기서 서명]은 누르기 한 번으로 서명 화면을 방문의 날로 연다', (tester) async {
      final server = _DetailServer([_consent]);
      final setup = CustomerTestSetup(server.backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _openDetail(tester, setup);

      await tester.tap(find.byKey(const ValueKey('consent-sign-11')));
      await settle(tester);

      expect(find.byKey(ScreenKeys.consentSign), findsOneWidget);
      final query = setup.adapter.requests.lastWhere((r) => r.path == '/v1/shops/3/consent-document').uri.queryParametersAll;
      expect(query, {
        'pet_ids': ['11'],
        'for_date': [server.visitDay],
      });
    });

    testWidgets('[받았어요]가 실패하면 스낵바로 알리고 줄은 남는다', (tester) async {
      final server = _DetailServer([_consent]);
      server.backend.routes[_consentPath] = (o, b) => const FakeResponse(
        statusCode: 500,
        data: {'code': 'INTERNAL', 'message': 'x'},
      );
      final setup = CustomerTestSetup(server.backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _openDetail(tester, setup);

      await tester.tap(find.byKey(const ValueKey('consent-received-11')));
      await settle(tester);

      expect(
        find.text(
          messageFor(
            ApiException(statusCode: 500, code: 'INTERNAL', message: 'x'),
          ),
        ),
        findsOneWidget,
      );
      expect(find.text(_consentLine), findsOneWidget);
      expect(
        tester
            .widget<AppButton>(
              find.byKey(const ValueKey('consent-received-11')),
            )
            .busy,
        isFalse,
      );
    });
  });

  group('하루 목록', () {
    Map<String, dynamic> visit(int id, int petId, String pet) => visitJson(
      visitId: id,
      date: '2026-09-23',
      start: '13:00',
      pet: visitPetJson(petId: petId, name: pet),
    );

    VisitTestBackend backend() => VisitTestBackend({
      'GET /v1/shops/3/visits': (o, b) => FakeResponse(
        statusCode: 200,
        data: dayJson(
          date: '2026-09-23',
          items: [
            dayItemJson(
              visit(1, 11, '두부'),
              groupKey: 'duo',
              customerCheckCount: 2,
              petCheckCount: 1,
            ),
            dayItemJson(
              visit(2, 12, '보리'),
              groupKey: 'duo',
              customerCheckCount: 2,
              petCheckCount: 1,
            ),
            dayItemJson(
              visitJson(
                visitId: 3,
                date: '2026-09-23',
                start: '16:00',
                pet: visitPetJson(petId: 13, name: '몽이'),
              ),
            ),
          ],
        ),
      ),
    });

    testWidgets('가족 묶음의 보호자 수는 한 번만 세고, 없는 줄에는 글자가 없다', (tester) async {
      final setup = CustomerTestSetup(backend().call, overrides: _today);
      addTearDown(setup.container.dispose);
      useTallView(tester, height: 1100);
      await pushOnHome<Object?>(tester, setup, '/visits/day/2026-09-23');

      expect(find.textContaining('확인 4'), findsOneWidget);
      expect(find.textContaining('확인'), findsOneWidget);
    });

    testWidgets('시간표의 블록에도 수가 보인다', (tester) async {
      final setup = CustomerTestSetup(backend().call, overrides: _today);
      addTearDown(setup.container.dispose);
      useTallView(tester, height: 1100);
      await pushOnHome<Object?>(tester, setup, '/visits/day/2026-09-23');

      await tester.tap(find.bySemanticsLabel(AppStrings.viewAsTimeline));
      await settle(tester);

      expect(find.textContaining('확인 4'), findsOneWidget);
      expect(find.textContaining('확인'), findsOneWidget);
    });
  });

  testWidgets('방문 수정 화면은 확인할 것을 묻지 않는다', (tester) async {
    final backend = VisitTestBackend({
      'GET /v1/shops/3/visits/101': (o, b) => FakeResponse(
        statusCode: 200,
        data: visitDetailJson(checks: [_noShow]),
      ),
    });
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    useTallView(tester);
    await pushOnHome<Object?>(tester, setup, '/visits/101/edit');

    expect(find.byType(VisitChecksBlock), findsNothing);
    expect(setup.calls, isNot(contains(_checksPath)));
  });
}

// 서명 보기·보낸 서류·반려동물 상세의 동의 줄(⑪-A3).
import 'dart:typed_data';

import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/features/customer/screens/consent_signatures_screen.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/consent_fixtures.dart';
import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/load_fonts.dart';
import '../../../support/visit_test_backend.dart';

// 1×1 흰 PNG — 실제로 그려지는 그림이면 된다.
final _png = Uint8List.fromList([
  0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01,
  0x00, 0x00, 0x00, 0x01, 0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x44, 0x41,
  0x54, 0x78, 0x9C, 0x63, 0xF8, 0xFF, 0xFF, 0x3F, 0x00, 0x05, 0xFE, 0x02, 0xFE, 0xA7, 0x35, 0x81, 0x84, 0x00, 0x00, 0x00,
  0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
]);

/// 서류 경로를 답하는 가짜 서버. forms 는 살아 있는 링크의 목록이다 — 끊으면 줄어든다.
class _World {
  _World({List<Map<String, dynamic>>? forms, Map<String, dynamic>? pet, int revokeStatus = 204})
    : forms = forms ?? [sentFormJson()] {
    final base = VisitTestBackend({
      'GET /v1/shops/3/forms': (o, b) => FakeResponse(statusCode: 200, data: {'items': this.forms}),
      'DELETE /v1/shops/3/forms/31': (o, b) {
        if (revokeStatus == 204) this.forms.removeWhere((f) => f['form_id'] == 31);
        return FakeResponse(statusCode: revokeStatus, data: revokeStatus == 204 ? null : {'code': 'INTERNAL_ERROR', 'message': 'x'});
      },
      'GET /v1/shops/3/pets/11': (o, b) => FakeResponse(statusCode: 200, data: petDetailJson(pet: pet)),
      'GET /v1/shops/3/pets/11/consent-signatures': (o, b) => FakeResponse(statusCode: 200, data: {
        'items': [
          signatureBriefJson(),
          signatureBriefJson(id: 90, channel: 'link', parts: const ['basic']),
          signatureBriefJson(id: 89, channel: 'intake', parts: const ['basic', 'condition']),
          signatureBriefJson(id: 88, channel: 'phone'),      // 모르는 받은 길 — 버린다
        ],
      }),
      'GET /v1/shops/3/consent-signatures/91': (o, b) => FakeResponse(statusCode: 200, data: signatureDetailJson(channel: 'in_shop')),
      'GET /v1/shops/3/consent-signatures/91/image': (o, b) => FakeResponse(statusCode: 200, data: _png),
      'GET /v1/shops/3/consent-signatures/89': (o, b) => FakeResponse(statusCode: 200, data: signatureDetailJson(id: 89, channel: 'intake')),
      'GET /v1/shops/3/consent-signatures/89/image': (o, b) => FakeResponse(statusCode: 200, data: _png),
      'POST /v1/shops/3/consent-forms': (o, b) => FakeResponse(statusCode: 201, data: formLinkJson()),
      'GET /v1/shops/3/consent-document': (o, b) => FakeResponse(statusCode: 200, data: consentDocumentJson()),
    });
    setup = CustomerTestSetup(base.call);
  }

  final List<Map<String, dynamic>> forms;
  late final CustomerTestSetup setup;

  Future<void> open(WidgetTester tester, String path) async {
    useTallView(tester, height: 1600);
    addTearDown(setup.container.dispose);
    await pushOnHome<Object?>(tester, setup, path);
  }
}

Map<String, dynamic> _signedPet() => {...petJson(), 'grooming_consent_on': '2026-11-16', 'grooming_consent_via': 'signature'};
Map<String, dynamic> _manualPet() => {...petJson(), 'grooming_consent_on': '2026-11-16', 'grooming_consent_via': 'manual'};

void main() {
  setUpAll(loadTestFonts);

  group('보낸 서류', () {
    testWidgets('줄마다 아이·보호자·보낸 날과 기간을 보이고 주소는 그리지 않는다', (tester) async {
      final world = _World(forms: [sentFormJson(pets: const [(11, '콩이'), (12, '보리')])]);
      await world.open(tester, '/forms');

      expect(find.text('콩이 · 보리'), findsOneWidget);
      expect(find.text('김민지 · 11월 16일에 보냄 · 11월 30일까지'), findsOneWidget);
      expect(find.textContaining('web.test'), findsNothing);
      expect(find.textContaining('FAKE-FORM-LINK'), findsNothing);
    });

    testWidgets('[다시 공유]는 서버를 부르지 않고 그 주소를 공유 시트에 준다', (tester) async {
      final world = _World();
      await world.open(tester, '/forms');
      world.setup.adapter.requests.clear();

      await tester.tap(find.byKey(const ValueKey('sent-form-share-31')));
      await settle(tester);

      expect(world.setup.shareSheet.shared, [fakeConsentUrl]);
      expect(world.setup.shareSheet.origins.single.width, greaterThan(0));
      expect(world.setup.calls, isEmpty);
    });

    testWidgets('[링크 끊기]는 한 번 묻고, 끊으면 줄이 사라진다', (tester) async {
      final world = _World();
      await world.open(tester, '/forms');

      await tester.tap(find.byKey(const ValueKey('sent-form-revoke-31')));
      await settle(tester);
      expect(find.text(AppStrings.sentFormRevokeAsk), findsOneWidget);
      await tester.tap(find.text(AppStrings.sentFormKeep));
      await settle(tester);
      expect(world.setup.calls.where((c) => c.startsWith('DELETE')), isEmpty);

      await tester.tap(find.byKey(const ValueKey('sent-form-revoke-31')));
      await settle(tester);
      await tester.tap(find.text(AppStrings.sentFormRevokeConfirm));
      await settle(tester);

      expect(world.setup.calls.where((c) => c == 'DELETE /v1/shops/3/forms/31'), hasLength(1));
      expect(find.byKey(const ValueKey('sent-form-31')), findsNothing);
      expect(find.text(AppStrings.sentFormsEmpty), findsOneWidget);
    });

    testWidgets('끊기가 실패하면 알리고 줄은 남는다', (tester) async {
      final world = _World(revokeStatus: 500);
      await world.open(tester, '/forms');

      await tester.tap(find.byKey(const ValueKey('sent-form-revoke-31')));
      await settle(tester);
      await tester.tap(find.text(AppStrings.sentFormRevokeConfirm));
      await settle(tester);

      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.byKey(const ValueKey('sent-form-31')), findsOneWidget);
    });

    testWidgets('고객 탭에는 살아 있는 링크가 있을 때만 보낸 서류 줄이 있고, 누르면 목록으로 간다', (tester) async {
      final world = _World();
      useTallView(tester, height: 1400);
      addTearDown(world.setup.container.dispose);
      await tester.pumpWidget(customerRouterApp(world.setup.container));
      await settle(tester);
      await tester.tap(find.text(AppStrings.tabCustomers));
      await settle(tester);

      expect(find.text('보낸 서류 1'), findsOneWidget);
      await tester.tap(find.text('보낸 서류 1'));
      await settle(tester);
      expect(find.byKey(ScreenKeys.sentForms), findsOneWidget);
    });

    testWidgets('보낸 서류가 없거나 읽지 못하면 고객 탭에 줄이 없다', (tester) async {
      for (final world in [_World(forms: []), _World()..forms.clear()]) {
        useTallView(tester, height: 1400);
        await tester.pumpWidget(customerRouterApp(world.setup.container));
        await settle(tester);
        await tester.tap(find.text(AppStrings.tabCustomers));
        await settle(tester);

        expect(find.textContaining('보낸 서류'), findsNothing);
        world.setup.container.dispose();
        await tester.pumpWidget(const SizedBox());
      }
    });
  });

  group('서명 보기', () {
    testWidgets('목록은 날짜·받은 길·적은 이름을 보이고 누르면 한 장을 연다', (tester) async {
      final world = _World(pet: _signedPet());
      await world.open(tester, '/pets/11/signatures');

      expect(find.byKey(ScreenKeys.consentSignatures), findsOneWidget);
      expect(find.text('2026년 11월 16일 · 매장에서 · 김민지'), findsOneWidget);
      expect(find.text('2026년 11월 16일 · 링크로 · 김민지'), findsOneWidget);
      expect(find.text('미용 안내 · 나이가 많은 아이'), findsOneWidget);

      await tester.tap(find.byKey(const ValueKey('signature-91')));
      await settle(tester);

      expect(find.text(AppStrings.signatureDetailTitle), findsOneWidget);
      expect(find.text(AppStrings.signatureNoteShop), findsOneWidget);
      expect(find.text('알려 주신 지병: 심장 질환'), findsOneWidget);
      expect(find.text('미용 안내의 글.'), findsOneWidget);
      expect(find.text('지병 안내의 글.'), findsOneWidget);
      expect(find.text('적은 이름: 김민지'), findsOneWidget);
      expect(find.textContaining('법적'), findsNothing);
      expect(world.setup.calls, contains('GET /v1/shops/3/consent-signatures/91/image'));
      expect(find.byKey(ConsentSignatureScreen.imageKey), findsOneWidget);
    });
  });

  group('문진표에서 받은 서명(⑪-C1b)', () {
    testWidgets('받은 길은 문진표에서이고 한 장에 문진표를 적으며 한 서명이라고 적혀 있다 — 모르는 받은 길은 버린다', (tester) async {
      final world = _World(pet: _signedPet());
      await world.open(tester, '/pets/11/signatures');

      expect(find.text('2026년 11월 16일 · ${AppStrings.signatureViaIntake} · 김민지'), findsOneWidget);
      expect(find.byKey(const ValueKey('signature-88')), findsNothing);

      await tester.tap(find.byKey(const ValueKey('signature-89')));
      await settle(tester);

      expect(find.text(AppStrings.signatureNoteIntake), findsOneWidget);
    });
  });

  group('반려동물 상세의 동의 줄', () {
    testWidgets('서명으로 받았으면 서명 받음과 [서명 보기]가 있다', (tester) async {
      final world = _World(pet: _signedPet());
      await world.open(tester, '/pets/11');

      expect(find.text('2026년 11월 16일에 서명 받음'), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('grooming-consent-signatures')));
      await settle(tester);
      expect(find.byKey(ScreenKeys.consentSignatures), findsOneWidget);
    });

    testWidgets('손으로 적었으면 지금 글 그대로이고 [서명 보기]가 없다', (tester) async {
      final world = _World(pet: _manualPet());
      await world.open(tester, '/pets/11');

      expect(find.text('2026년 11월 16일에 받았어요'), findsOneWidget);
      expect(find.byKey(const ValueKey('grooming-consent-signatures')), findsNothing);
    });

    testWidgets('받지 않은 아이의 ··· 에는 보내기와 여기서 서명만 있고, 보내면 공유 시트가 뜬다', (tester) async {
      final world = _World();
      await world.open(tester, '/pets/11');

      await tester.tap(find.byKey(const ValueKey('grooming-consent-more')));
      await settle(tester);
      expect(find.text(AppStrings.consentSend), findsOneWidget);
      expect(find.text(AppStrings.consentSignHere), findsOneWidget);
      expect(find.text(AppStrings.groomingConsentClear), findsNothing);

      await tester.tap(find.text(AppStrings.consentSend));
      await settle(tester);

      expect(bodyOf(world.setup.adapter.lastBodyByPath['/v1/shops/3/consent-forms']), {'pet_ids': [11]});
      expect(world.setup.shareSheet.shared, [fakeConsentUrl]);
    });

    testWidgets('··· 의 여기서 서명은 기준일 없이 서명 화면을 연다', (tester) async {
      final world = _World();
      await world.open(tester, '/pets/11');

      await tester.tap(find.byKey(const ValueKey('grooming-consent-more')));
      await settle(tester);
      await tester.tap(find.text(AppStrings.consentSignHere));
      await settle(tester);

      expect(find.byKey(ScreenKeys.consentSign), findsOneWidget);
      final query = world.setup.adapter.requests.lastWhere((r) => r.path == '/v1/shops/3/consent-document').uri.queryParametersAll;
      expect(query, {'pet_ids': ['11']});
    });
  });
}

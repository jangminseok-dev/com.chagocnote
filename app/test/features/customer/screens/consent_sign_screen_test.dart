// 매장에서 바로 받는 동의서 서명(⑪-A3) — 문서, 빠진 것, 보내기, 내용이 바뀜, 뒤로 가기.
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/features/customer/screens/consent_sign_screen.dart';
import 'package:chagocnote/features/customer/screens/signature_pad.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/consent_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_test_backend.dart';

const _document = '/v1/shops/3/consent-document';
const _sign = '/v1/shops/3/consent-signatures';

/// 문서 읽기와 서명 보내기만 답하는 가짜 서버. 그 밖(뒤에 깔린 홈의 읽기)은 기본 백엔드가 답한다.
class _World {
  _World({
    FakeResponse Function()? document,
    FutureOr<FakeResponse> Function(Map<String, dynamic> body)? sign,
  }) {
    final base = VisitTestBackend();
    setup = CustomerTestSetup(
      (o, b) async {
        if (o.path == _document) {
          documentQueries.add(o.uri.queryParametersAll);
          return (document ?? () => FakeResponse(statusCode: 200, data: consentDocumentJson()))();
        }
        if (o.path == _sign) {
          final body = jsonDecode(utf8.decode(b!)) as Map<String, dynamic>;
          signed.add(body);
          return await (sign ?? (_) => const FakeResponse(statusCode: 201, data: {'signature_id': 91}))(body);
        }
        if (base.routes.containsKey('${o.method} ${o.path}')) return base.call(o, b);
        return const FakeResponse(statusCode: 404, data: {});
      },
      // 그림 만들기는 가짜 시계에서 끝나지 않는다 — 정해진 바이트를 준다.
      overrides: [signaturePngMakerProvider.overrideWithValue((_) async => Uint8List.fromList([1, 2, 3]))],
    );
  }

  late final CustomerTestSetup setup;
  final documentQueries = <Map<String, List<String>>>[];
  final signed = <Map<String, dynamic>>[];

  Future<void> open(WidgetTester tester, [String location = '/consent/sign?pet_ids=11&for_date=2026-11-20']) async {
    tester.view.physicalSize = const Size(390, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(setup.container.dispose);
    await tester.pumpWidget(customerRouterApp(setup.container));
    await settle(tester);
    unawaited(setup.container.read(routerProvider).push(location));
    await settle(tester);
  }
}

Future<void> _fill(WidgetTester tester, {String name = '김민지', bool sign = true, bool agree = true}) async {
  if (name.isNotEmpty) await tester.enterText(find.byKey(ConsentSignScreen.nameKey), name);
  if (sign) {
    final box = tester.getRect(find.byKey(SignaturePad.canvasKey));
    await tester.dragFrom(box.center - const Offset(60, 0), const Offset(120, 20));
  }
  if (agree) await tester.tap(find.byKey(ConsentSignScreen.agreeKey));
  await tester.pump();
}

Future<void> _submit(WidgetTester tester) async {
  await tester.tap(find.byKey(ConsentSignScreen.submitKey));
  await settle(tester);
}

void main() {
  testWidgets('문서를 예약 날로 읽고 아이·지병·토막을 문서의 순서로 그린다', (tester) async {
    final world = _World();
    await world.open(tester);

    expect(world.documentQueries.single, {
      'pet_ids': ['11'],
      'for_date': ['2026-11-20'],
    });
    expect(find.text('콩이'), findsOneWidget);
    expect(find.text('알려 주신 지병: 심장 질환'), findsOneWidget);
    final titles = ['미용 안내', '나이가 많은 아이', '지병이 있는 아이'];
    final tops = [for (final title in titles) tester.getTopLeft(find.text(title)).dy];
    expect(tops, [...tops]..sort());
    expect(find.text('basic 글의 첫 줄.'), findsOneWidget);
    expect(find.text('basic 글의 둘째 줄.'), findsOneWidget);   // 줄바꿈은 문단이 된다
    expect(find.textContaining('해당:'), findsNothing);          // 아이가 하나면 없다
    expect(find.textContaining('지난번('), findsNothing);
    expect(find.textContaining('법적'), findsNothing);
  });

  testWidgets('가족이면 토막마다 해당하는 아이를 적고, 바뀐 부분만 받을 때는 지난 동의의 날을 알린다', (tester) async {
    final world = _World(
      document: () => FakeResponse(statusCode: 200, data: consentDocumentJson(
        pets: [
          {'pet_id': 11, 'name': '콩이', 'conditions': <String>[], 'parts': ['senior']},
          {'pet_id': 12, 'name': '보리', 'conditions': ['피부'], 'parts': ['condition']},
        ],
        texts: const ['senior', 'condition'],
        previousConsentOn: '2026-03-02',
      )),
    );
    await world.open(tester, '/consent/sign?pet_ids=12,11');

    expect(world.documentQueries.single, {'pet_ids': ['11', '12']});       // 기준일이 없으면 보내지 않는다
    expect(find.text('지난번(2026년 3월 2일)에 동의하신 내용에 더해 바뀐 부분만 확인해 주세요'), findsOneWidget);
    expect(find.text('해당: 콩이'), findsOneWidget);
    expect(find.text('해당: 보리'), findsOneWidget);
    expect(find.text('미용 안내'), findsNothing);
  });

  for (final (label, fill, message) in [
    ('이름', (WidgetTester t) => _fill(t, name: ''), '이름을 적어 주세요'),
    ('서명', (WidgetTester t) => _fill(t, sign: false), '서명해 주세요'),
    ('체크', (WidgetTester t) => _fill(t, agree: false), '동의에 체크해 주세요'),
  ]) {
    testWidgets('$label 이 빠지면 보내지 않고 그 자리에서 말한다', (tester) async {
      final world = _World();
      await world.open(tester);
      await fill(tester);

      await _submit(tester);

      expect(find.text(message), findsOneWidget);
      expect(world.signed, isEmpty);
    });
  }

  testWidgets('빠진 것을 채우면 안내가 사라진다', (tester) async {
    final world = _World();
    await world.open(tester);
    await _submit(tester);
    expect(find.text('이름을 적어 주세요'), findsOneWidget);

    await tester.enterText(find.byKey(ConsentSignScreen.nameKey), '김');
    await tester.pump();

    expect(find.text('이름을 적어 주세요'), findsNothing);
  });

  testWidgets('보내면 이름·지문·기준일·그림이 가고 보냈어요 한 장이 된다 — 닫기는 따로 누른다', (tester) async {
    final world = _World();
    await world.open(tester);
    await _fill(tester, name: '  김민지 ');

    await _submit(tester);

    expect(world.signed.single, {
      'pet_ids': [11],
      'doc_digest': 'digest-1',
      'signer_name': '김민지',
      'signature_png': 'AQID',
      'for_date': '2026-11-20',
    });
    expect(find.text('보냈어요'), findsOneWidget);
    expect(find.byKey(ConsentSignScreen.submitKey), findsNothing);
    expect(find.byKey(ScreenKeys.consentSign), findsOneWidget);     // 저절로 닫히지 않는다

    await tester.tap(find.byKey(ConsentSignScreen.closeKey));
    await settle(tester);
    expect(find.byKey(ScreenKeys.consentSign), findsNothing);
  });

  testWidgets('읽는 사이 내용이 바뀌면 알리고 다시 읽고, 이름은 남기고 서명과 체크를 비운다', (tester) async {
    var reads = 0;
    final world = _World(
      document: () => FakeResponse(statusCode: 200, data: consentDocumentJson(digest: 'digest-${reads += 1}')),
      sign: (body) => body['doc_digest'] == 'digest-1'
          ? const FakeResponse(statusCode: 409, data: {'code': 'CONSENT_DOCUMENT_CHANGED', 'message': 'x'})
          : const FakeResponse(statusCode: 201, data: {'signature_id': 92}),
    );
    await world.open(tester);
    await _fill(tester);

    await _submit(tester);

    expect(find.text('내용이 바뀌었어요. 다시 읽어 주세요'), findsOneWidget);
    expect(reads, 2);
    expect(tester.widget<TextField>(find.byKey(ConsentSignScreen.nameKey)).controller!.text, '김민지');
    expect(find.text('여기에 서명해 주세요'), findsOneWidget);

    // 다시 서명하지 않고 보내면 보내지 않는다.
    await _submit(tester);
    expect(find.text('서명해 주세요'), findsOneWidget);
    expect(world.signed, hasLength(1));

    // 다시 서명하면 새 지문으로 간다.
    await _fill(tester, name: '');
    await _submit(tester);
    expect(world.signed.last['doc_digest'], 'digest-2');
    expect(find.text('보냈어요'), findsOneWidget);
  });

  testWidgets('더 받을 것이 없으면 오류가 아니라 이미 받은 동의라고 말한다', (tester) async {
    final world = _World(
      document: () => const FakeResponse(statusCode: 409, data: {'code': 'CONSENT_UP_TO_DATE', 'message': 'x'}),
    );
    await world.open(tester);

    expect(find.text('이미 받은 동의예요'), findsOneWidget);
    expect(find.byKey(ConsentSignScreen.closeKey), findsOneWidget);
    expect(find.text('다시 시도'), findsNothing);
  });

  testWidgets('보내기가 실패하면 스낵바로 알리고 적은 것은 그대로다', (tester) async {
    final world = _World(sign: (_) => const FakeResponse(statusCode: 500, data: {'code': 'INTERNAL_ERROR', 'message': 'x'}));
    await world.open(tester);
    await _fill(tester);

    await _submit(tester);

    expect(find.byType(SnackBar), findsOneWidget);
    expect(find.text('보냈어요'), findsNothing);
    expect(find.text('여기에 서명해 주세요'), findsNothing);      // 서명이 남아 있다
    expect(tester.widget<TextField>(find.byKey(ConsentSignScreen.nameKey)).controller!.text, '김민지');
  });

  testWidgets('보내는 동안 두 번 보내지 않는다', (tester) async {
    final gate = Completer<FakeResponse>();
    final world = _World(sign: (_) => gate.future);
    await world.open(tester);
    await _fill(tester);

    await tester.tap(find.byKey(ConsentSignScreen.submitKey));
    // 그림을 만들고 요청이 나갈 때까지 몇 번 돌린다(응답은 붙들려 있다).
    for (var i = 0; i < 5; i++) {
      await tester.pump(const Duration(milliseconds: 1));
    }
    await tester.tap(find.byKey(ConsentSignScreen.submitKey), warnIfMissed: false);
    for (var i = 0; i < 5; i++) {
      await tester.pump(const Duration(milliseconds: 1));
    }
    expect(world.signed, hasLength(1));

    gate.complete(const FakeResponse(statusCode: 201, data: {'signature_id': 91}));
    await settle(tester);
    expect(find.text('보냈어요'), findsOneWidget);
  });

  testWidgets('서명하는 중의 뒤로 가기는 한 번 묻는다 — 매장의 화면이 그냥 보이지 않는다', (tester) async {
    final world = _World();
    await world.open(tester);

    await tester.tap(find.bySemanticsLabel('뒤로'));
    await settle(tester);
    expect(find.text('서명을 그만둘까요?'), findsOneWidget);
    await tester.tap(find.text('계속 서명하기'));
    await settle(tester);
    expect(find.byKey(ScreenKeys.consentSign), findsOneWidget);

    // 시스템의 뒤로 가기도 같다.
    await tester.binding.handlePopRoute();
    await settle(tester);
    expect(find.text('서명을 그만둘까요?'), findsOneWidget);
    await tester.tap(find.text('그만두기'));
    await settle(tester);
    expect(find.byKey(ScreenKeys.consentSign), findsNothing);
  });
}

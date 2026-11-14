// 기록 찾기 화면(⑨-1b) — 처음 화면, 쉬었다 묻기, 줄과 갈 곳, 빈 결과·실패, 아이로 좁히기.
import 'dart:async';

import 'package:chagocnote/core/proxy/media_images.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_photo_tile.dart';
import 'package:chagocnote/design/widgets/pressable.dart';
import 'package:chagocnote/features/customer/screens/pet_detail_screen.dart';
import 'package:chagocnote/features/search/screens/search_screen.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/search_fixtures.dart';
import '../../../support/upload_fakes.dart';
import '../../../support/visit_test_backend.dart';

const _search = '/v1/shops/3/search';
const _pause = Duration(milliseconds: 500);

FakeResponse _ok(List<Map<String, dynamic>> items) =>
    FakeResponse(statusCode: 200, data: searchResultJson(items));

/// 검색 경로만 답하는 가짜 서버. 그 밖(넘어간 상세 화면의 읽기)은 기본 백엔드에 있으면 그것이, 없으면 404 다.
class _World {
  _World([FutureOr<FakeResponse> Function(RequestOptions o)? search]) {
    final base = VisitTestBackend();
    setup = CustomerTestSetup(
      (o, b) {
        if (o.path == _search) {
          queries.add(Map.of(o.queryParameters));
          return (search ?? (_) => _ok([]))(o);
        }
        if (base.routes.containsKey('${o.method} ${o.path}')) return base.call(o, b);
        return const FakeResponse(statusCode: 404, data: {});
      },
      overrides: [mediaImagesProvider.overrideWithValue(images)],
    );
  }

  late final CustomerTestSetup setup;
  final images = FakeMediaImages();
  final queries = <Map<String, dynamic>>[];

  Future<void> open(WidgetTester tester, [String location = '/search']) async {
    tester.view.physicalSize = const Size(390, 1400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(setup.container.dispose);
    await tester.pumpWidget(customerRouterApp(setup.container));
    await settle(tester);
    unawaited(setup.container.read(routerProvider).push(location));
    await settle(tester);
  }

  /// 입력 칸에 적고 0.5초를 쉰다.
  Future<void> type(WidgetTester tester, String text) async {
    await tester.enterText(find.byKey(SearchScreen.fieldKey), text);
    await tester.pump(_pause);
    await settle(tester);
  }
}

Finder _row(int index) => find.byKey(ValueKey('search-item-$index'));

void main() {
  testWidgets('처음에는 무엇으로 찾는지와 예시를 보이고 아무것도 묻지 않는다', (tester) async {
    final w = _World();
    await w.open(tester);

    expect(find.byKey(ScreenKeys.search), findsOneWidget);
    expect(find.text(AppStrings.searchIntro), findsOneWidget);
    expect(find.text(AppStrings.searchExampleA), findsOneWidget);
    expect(find.text(AppStrings.searchExampleB), findsOneWidget);
    expect(find.text(AppStrings.searchEmpty), findsNothing);
    expect(w.queries, isEmpty);
  });

  testWidgets('0.5초를 쉬어야 묻고, 그 전에는 묻지 않는다 — 한 글자는 묻지 않는다', (tester) async {
    final w = _World((_) => _ok([searchItemJson()]));
    await w.open(tester);

    await tester.enterText(find.byKey(SearchScreen.fieldKey), '귀 청');
    await tester.pump(const Duration(milliseconds: 400));
    await tester.enterText(find.byKey(SearchScreen.fieldKey), '귀 청소');
    await tester.pump(const Duration(milliseconds: 400));
    expect(w.queries, isEmpty);
    await tester.pump(const Duration(milliseconds: 100));
    await settle(tester);
    expect(w.queries, [
      {'q': '귀 청소'},
    ]);

    await w.type(tester, '귀');
    expect(w.queries, hasLength(1));
    expect(find.text(AppStrings.searchIntro), findsOneWidget);
  });

  testWidgets('줄에는 이름, 종류와 날짜, 걸린 문장이 있다 — AI 라는 말은 없다', (tester) async {
    final w = _World(
      (_) => _ok([
        searchItemJson(photo: 'https://media.test/51.jpg'),
        searchPetItemJson(pet: '두부', petId: 102, kind: 'condition_note', snippet: '심장 질환 — 약 복용 중'),
        searchOwnerItemJson(),
      ]),
    );
    await w.open(tester);
    await w.type(tester, '귀 청소');

    expect(find.text(AppStrings.searchNearest), findsOneWidget);
    expect(find.descendant(of: _row(0), matching: find.text('콩이')), findsOneWidget);
    expect(find.descendant(of: _row(0), matching: find.text('케어 노트 · 11월 3일')), findsOneWidget);
    expect(find.descendant(of: _row(0), matching: find.text('귀 청소할 때 예민하게 반응했어요')), findsOneWidget);
    expect(find.descendant(of: _row(1), matching: find.text('두부')), findsOneWidget);
    expect(find.descendant(of: _row(1), matching: find.text('지병')), findsOneWidget);
    // 보호자 메모는 사진 칸 없이 보호자 이름으로.
    expect(find.descendant(of: _row(2), matching: find.text('김민지')), findsOneWidget);
    expect(find.descendant(of: _row(2), matching: find.text('보호자 메모')), findsOneWidget);
    expect(find.descendant(of: _row(2), matching: find.byType(AppPhotoTile)), findsNothing);
    expect(find.descendant(of: _row(0), matching: find.byType(AppPhotoTile)), findsOneWidget);
    expect(w.images.urls, ['https://media.test/51.jpg']);
    expect(find.textContaining('AI'), findsNothing);
  });

  testWidgets('방문 줄을 누르면 방문 상세로 가고, 돌아오면 검색어와 결과가 그대로다', (tester) async {
    final w = _World((_) => _ok([searchItemJson(visitId: 7)]));
    await w.open(tester);
    await w.type(tester, '귀 청소');

    await tester.tap(_row(0));
    await settle(tester);
    expect(find.byKey(ScreenKeys.visitDetail), findsOneWidget);

    w.setup.container.read(routerProvider).pop();
    await settle(tester);
    expect(find.byKey(ScreenKeys.search), findsOneWidget);
    expect(find.text('귀 청소'), findsOneWidget);
    expect(_row(0), findsOneWidget);
    expect(w.queries, hasLength(1)); // 다시 묻지 않았다
  });

  testWidgets('특이사항 줄은 그 아이의 상세로, 보호자 메모는 [보호자] 탭으로 간다', (tester) async {
    final w = _World((_) => _ok([searchPetItemJson(petId: 102), searchOwnerItemJson(openPetId: 101)]));
    await w.open(tester);
    await w.type(tester, '드라이기');

    await tester.tap(_row(0));
    await settle(tester);
    var pet = tester.widget<PetDetailScreen>(find.byType(PetDetailScreen));
    expect((pet.petId, pet.initialTab), (102, 0));

    w.setup.container.read(routerProvider).pop();
    await settle(tester);
    await tester.tap(_row(1));
    await settle(tester);
    pet = tester.widget<PetDetailScreen>(find.byType(PetDetailScreen));
    expect((pet.petId, pet.initialTab), (101, PetDetailScreen.ownerTab));
  });

  testWidgets('갈 곳이 없는 줄은 눌리지 않고 화살표가 없다', (tester) async {
    final w = _World((_) => _ok([searchOwnerItemJson(openPetId: null), searchItemJson()]));
    await w.open(tester);
    await w.type(tester, '전화');

    expect(tester.widget<Pressable>(find.descendant(of: _row(0), matching: find.byType(Pressable))).onTap, isNull);
    expect(tester.widget<Pressable>(find.descendant(of: _row(1), matching: find.byType(Pressable))).onTap, isNotNull);
    expect(find.descendant(of: _row(0), matching: find.byIcon(Icons.chevron_right)), findsNothing);
    expect(find.descendant(of: _row(1), matching: find.byIcon(Icons.chevron_right)), findsOneWidget);
    await tester.tap(_row(0), warnIfMissed: false);
    await settle(tester);
    expect(find.byKey(ScreenKeys.search), findsOneWidget);
  });

  testWidgets('찾은 것이 없으면 그렇게 알린다', (tester) async {
    final w = _World();
    await w.open(tester);
    await w.type(tester, '없는 말');

    expect(find.text(AppStrings.searchEmpty), findsOneWidget);
    expect(find.text(AppStrings.searchNearest), findsNothing);
    expect(find.text(AppStrings.searchIntro), findsNothing);
  });

  testWidgets('읽지 못하면 다시 시도할 수 있다', (tester) async {
    var fail = true;
    final w = _World(
      (_) => fail
          ? const FakeResponse(statusCode: 500, data: {'code': 'INTERNAL', 'message': 'x'})
          : _ok([searchItemJson()]),
    );
    await w.open(tester);
    await w.type(tester, '귀 청소');
    expect(_row(0), findsNothing);

    fail = false;
    await tester.tap(find.text(AppStrings.retry));
    await settle(tester);
    expect(_row(0), findsOneWidget);
    expect(w.queries, hasLength(2));
  });

  testWidgets('다시 묻는 동안에는 앞 결과를 그대로 보인다', (tester) async {
    final gate = Completer<FakeResponse>();
    final w = _World(
      (o) => o.queryParameters['q'] == '발톱' ? _ok([searchItemJson(snippet: '앞 결과')]) : gate.future,
    );
    await w.open(tester);
    await w.type(tester, '발톱');
    expect(find.text('앞 결과'), findsOneWidget);

    await tester.enterText(find.byKey(SearchScreen.fieldKey), '발톱 짧게');
    await tester.pump(_pause);
    await tester.pump(const Duration(milliseconds: 1));
    expect(find.text('앞 결과'), findsOneWidget);

    gate.complete(_ok([searchItemJson(snippet: '새 결과')]));
    await settle(tester);
    expect(find.text('새 결과'), findsOneWidget);
    expect(find.text('앞 결과'), findsNothing);
  });

  testWidgets('아이로 좁혀 열면 그 아이 안에서 찾고 위에 이름을 알린다', (tester) async {
    final w = _World();
    await w.open(tester, '/search?pet_id=101&pet=${Uri.encodeQueryComponent('콩이')}');

    expect(find.text('콩이의 기록에서'), findsOneWidget);
    await w.type(tester, '발톱');
    expect(w.queries, [
      {'q': '발톱', 'pet_id': 101},
    ]);
  });

  testWidgets('이름 없이 좁혀 열면 이름 없이 알린다', (tester) async {
    final w = _World();
    await w.open(tester, '/search?pet_id=101');
    expect(find.text(AppStrings.searchInThisPet), findsOneWidget);
  });

  testWidgets('깨진 번호로 열면 매장 전체에서 찾는다', (tester) async {
    final all = _World();
    await all.open(tester, '/search?pet_id=abc');
    expect(find.text(AppStrings.searchInThisPet), findsNothing);
    await all.type(tester, '발톱');
    expect(all.queries, [
      {'q': '발톱'},
    ]);
  });

  testWidgets('결과 화면의 모습', (tester) async {
    final w = _World(
      (_) => _ok([
        searchItemJson(photo: 'https://media.test/51.jpg'),
        searchPetItemJson(pet: '두부', petId: 102, snippet: '드라이기 소리를 무서워해서 타월 드라이 위주로 말려요. 간식으로 달래면 얌전해져요.'),
        searchPetItemJson(kind: 'condition_note', snippet: '심장 질환 — 약 복용 중'),
        searchOwnerItemJson(),
        searchItemJson(kind: 'visit_memo', petId: null, pet: null, visitId: 9, date: '2026-10-28', snippet: '상담만 하고 가심'),
      ]),
    );
    await w.open(tester);
    await w.type(tester, '예민한 아이');
    FocusManager.instance.primaryFocus?.unfocus();
    await settle(tester);

    await expectLater(find.byKey(ScreenKeys.search), matchesGoldenFile('goldens/search_results.png'));
  });
}

import 'package:chagocnote/core/plugs/pet_records_plug.dart';
import 'package:chagocnote/core/proxy/media_images.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/features/visit/screens/feed_view.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/upload_fakes.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

/// 반려동물 11(콩이)의 상세와 그 아이의 피드 두 쪽(두 번째 쪽은 [더 보기]로).
VisitTestBackend _backend({bool empty = false}) => VisitTestBackend({
  'GET /v1/shops/3/pets/11': (o, b) =>
      FakeResponse(statusCode: 200, data: petDetailJson()),
  'GET /v1/shops/3/visits/feed': (o, b) => FakeResponse(
    statusCode: 200,
    data: empty
        ? feedJson()
        : o.queryParameters['cursor'] == null
        ? feedJson(
            items: [
              feedItemJson(
                pet: visitPetJson(petId: 11, name: '콩이'),
                menus: const ['전체 미용'],
              ),
            ],
            nextCursor: 'c2',
          )
        : feedJson(
            items: [
              feedItemJson(
                visitId: 90,
                date: '2026-09-02',
                pet: visitPetJson(petId: 11, name: '콩이'),
                menus: const ['목욕'],
              ),
            ],
          ),
  ),
  'GET /v1/shops/3/visits/101': (o, b) =>
      FakeResponse(statusCode: 200, data: visitDetailJson()),
});

Future<CustomerTestSetup> _open(
  WidgetTester tester,
  VisitTestBackend backend,
) async {
  final setup = CustomerTestSetup(
    backend.call,
    overrides: [
      mediaImagesProvider.overrideWithValue(FakeMediaImages()),
      // app.dart 의 buildRoot 와 같은 꽂기.
      petRecordsPlugProvider.overrideWithValue(
        (petId) => PetRecordsView(petId: petId),
      ),
    ],
  );
  addTearDown(setup.container.dispose);
  useTallView(tester, height: 2400);
  await pushOnHome<Object?>(tester, setup, '/pets/11');
  await tester.tap(find.text(AppStrings.petTabRecords));
  await settle(tester);
  return setup;
}

void main() {
  testWidgets('[기록] 탭은 그 아이의 피드를 보이고, [더 보기]로 다음 쪽을 붙이며, 누르면 방문 상세로 간다', (
    tester,
  ) async {
    final setup = await _open(tester, _backend());

    expect(find.text('10월 2일 금 · 전체 미용'), findsOneWidget);
    expect(
      [
        for (final r in setup.adapter.requests)
          if (r.path == '/v1/shops/3/visits/feed') r.queryParameters,
      ],
      [
        {'pet_id': 11},
      ],
    );

    await tester.tap(
      find.byWidgetPredicate(
        (w) => w is AppButton && w.label == AppStrings.loadMore,
      ),
    );
    await settle(tester);
    expect(find.text('9월 2일 수 · 목욕'), findsOneWidget);
    expect(find.text(AppStrings.loadMore), findsNothing, reason: '마지막 쪽');

    await tester.tap(find.text('10월 2일 금 · 전체 미용'));
    await settle(tester);
    expect(find.byKey(ScreenKeys.visitDetail), findsOneWidget);
  });

  testWidgets('끝난 미용이 없으면 그렇게 적는다', (tester) async {
    await _open(tester, _backend(empty: true));

    expect(find.text(AppStrings.petRecordsEmpty), findsOneWidget);
  });
}

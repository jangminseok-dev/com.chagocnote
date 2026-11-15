// 검색 컨트롤러 — 처음 화면, 묻기, 늦게 온 옛 결과 버리기, 다시 시도.
import 'dart:async';

import 'package:chagocnote/features/search/state/search_controller.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/search_fixtures.dart';

const SearchScope _scope = (shopId: customerTestShopId, petId: null);

FakeResponse _ok(List<Map<String, dynamic>> items) =>
    FakeResponse(statusCode: 200, data: searchResultJson(items));

/// 검색어마다 응답을 손으로 내보내는 가짜 서버.
class _Gate {
  final asked = <String>[];
  final petIds = <Object?>[];
  final _waiting = <String, Completer<FakeResponse>>{};

  FutureOr<FakeResponse> call(RequestOptions o, Object? body) {
    final q = o.queryParameters['q'] as String;
    asked.add(q);
    petIds.add(o.queryParameters['pet_id']);
    return (_waiting[q] = Completer<FakeResponse>()).future;
  }

  void answer(String q, FakeResponse response) => _waiting.remove(q)!.complete(response);
}

/// 요청이 가짜 서버에 닿고 응답이 상태에 닿을 만큼 이벤트 루프를 돌린다(dio 의 인터셉터가 여러 번 양보한다).
Future<void> _tick() async {
  for (var i = 0; i < 30; i++) {
    await Future<void>.delayed(Duration.zero);
  }
}

void main() {
  late _Gate gate;
  late CustomerTestSetup setup;
  late ProviderSubscription<SearchState> sub;

  SearchState state() => setup.container.read(searchControllerProvider(_scope));
  SearchController controller() => setup.container.read(searchControllerProvider(_scope).notifier);

  setUp(() {
    gate = _Gate();
    setup = CustomerTestSetup(gate.call);
    sub = setup.container.listen(searchControllerProvider(_scope), (_, _) {});
    addTearDown(() {
      sub.close();
      setup.container.dispose();
    });
  });

  test('처음에는 아무것도 묻지 않는다', () {
    expect(state().query, '');
    expect(state().result, isNull);
    expect(gate.asked, isEmpty);
  });

  test('검색어를 다듬어 묻고 결과를 든다', () async {
    controller().search('  귀  청소 ');
    expect(state().query, '귀 청소');
    expect(state().result!.isLoading, isTrue);
    await _tick();
    gate.answer('귀 청소', _ok([searchItemJson()]));
    await _tick();
    expect(gate.asked, ['귀 청소']);
    expect(state().result!.value!.items.single.petName, '콩이');
  });

  test('같은 검색어는 다시 묻지 않는다 — 앞뒤 공백만 달라도', () async {
    controller().search('발톱');
    await _tick();
    gate.answer('발톱', _ok([]));
    await _tick();
    controller().search(' 발톱 ');
    controller().search('발톱\n');
    await _tick();
    expect(gate.asked, ['발톱']);
  });

  test('늦게 온 옛 결과는 버린다', () async {
    controller().search('귀 청');
    await _tick();
    controller().search('귀 청소');
    await _tick();
    gate.answer('귀 청소', _ok([searchItemJson(snippet: '새 결과')]));
    await _tick();
    gate.answer('귀 청', _ok([searchItemJson(snippet: '옛 결과')]));
    await _tick();
    expect(state().query, '귀 청소');
    expect(state().result!.value!.items.single.snippet, '새 결과');
  });

  test('늦게 온 옛 실패도 버린다', () async {
    controller().search('귀 청');
    await _tick();
    controller().search('귀 청소');
    await _tick();
    gate.answer('귀 청소', _ok([searchItemJson()]));
    await _tick();
    gate.answer('귀 청', const FakeResponse(statusCode: 500, data: {'code': 'INTERNAL', 'message': 'x'}));
    await _tick();
    expect(state().result!.hasError, isFalse);
    expect(state().result!.value!.items, hasLength(1));
  });

  test('두 자 미만으로 지우면 처음 화면이고 진행 중이던 결과가 뒤늦게 나타나지 않는다', () async {
    controller().search('귀 청소');
    await _tick();
    controller().search('귀');
    expect(state().query, '');
    expect(state().result, isNull);
    gate.answer('귀 청소', _ok([searchItemJson()]));
    await _tick();
    expect(state().result, isNull);
    expect(gate.asked, ['귀 청소']);
  });

  test('지운 뒤 같은 검색어를 다시 치면 다시 묻는다', () async {
    controller().search('발톱');
    await _tick();
    gate.answer('발톱', _ok([]));
    await _tick();
    controller().search('');
    controller().search('발톱');
    await _tick();
    expect(gate.asked, ['발톱', '발톱']);
  });

  test('다시 읽는 동안 앞 결과를 들고 있다', () async {
    controller().search('발톱');
    await _tick();
    gate.answer('발톱', _ok([searchItemJson(snippet: '앞 결과')]));
    await _tick();
    controller().search('발톱 짧게');
    expect(state().result!.isLoading, isTrue);
    expect(state().display!.value!.items.single.snippet, '앞 결과');
  });

  test('실패하면 오류를 들고, 다시 시도는 같은 검색어를 다시 묻는다', () async {
    controller().search('발톱');
    await _tick();
    gate.answer('발톱', const FakeResponse(statusCode: 500, data: {'code': 'INTERNAL', 'message': 'x'}));
    await _tick();
    expect(state().result!.hasError, isTrue);
    controller().retry();
    await _tick();
    gate.answer('발톱', _ok([searchItemJson()]));
    await _tick();
    expect(gate.asked, ['발톱', '발톱']);
    expect(state().result!.value!.items, hasLength(1));
  });

  test('처음 화면에서 다시 시도는 아무것도 하지 않는다', () async {
    controller().retry();
    await _tick();
    expect(gate.asked, isEmpty);
  });

  test('아이로 좁힌 검색은 pet_id 를 보낸다', () async {
    const SearchScope scoped = (shopId: customerTestShopId, petId: 101);
    final scopedSub = setup.container.listen(searchControllerProvider(scoped), (_, _) {});
    addTearDown(scopedSub.close);
    setup.container.read(searchControllerProvider(scoped).notifier).search('발톱');
    await _tick();
    expect(gate.petIds, [101]);
  });
}

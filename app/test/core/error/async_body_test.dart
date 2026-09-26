import 'dart:async';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/error/async_body.dart';
import 'package:chagocnote/core/error/error_messages.dart';
import 'package:chagocnote/core/proxy/network_watcher.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/upload_fakes.dart';

/// 부를 때마다 [next]의 앞에서 하나를 꺼내 돌려주거나(목록) 기다리거나(Completer) 던지는 목록 원본.
class _Source {
  final next = <Object>[];
  var calls = 0;

  Future<List<String>> load() async {
    calls++;
    final item = next.removeAt(0);
    if (item is List<String>) return item;
    if (item is Completer<List<String>>) return item.future;
    throw item;
  }
}

final _sourceProvider = Provider<_Source>((ref) => throw UnimplementedError());

final _listProvider = FutureProvider<List<String>>(
  (ref) => ref.read(_sourceProvider).load(),
);

final _offline = ApiException.network('timeout');
final _server = ApiException(statusCode: 503, code: 'HTTP_ERROR', message: 'x');
final _gone = ApiException(
  statusCode: 404,
  code: 'VISIT_NOT_FOUND',
  message: 'x',
);

class _Body extends ConsumerWidget {
  const _Body({this.refresh = false});

  final bool refresh;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AsyncBody<List<String>>(
      value: ref.watch(_listProvider),
      onRetry: () => ref.invalidate(_listProvider),
      onRefresh: refresh ? () => ref.refresh(_listProvider.future) : null,
      builder: (items) => ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [for (final i in items) ListTile(title: Text(i))],
      ),
    );
  }
}

Future<(_Source, FakeNetworkWatcher)> _pump(
  WidgetTester tester,
  List<Object> results, {
  bool refresh = false,
  bool pushed = false,
}) async {
  final source = _Source()..next.addAll(results);
  final network = FakeNetworkWatcher();
  Widget body = Scaffold(body: _Body(refresh: refresh));
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        _sourceProvider.overrideWithValue(source),
        networkWatcherProvider.overrideWithValue(network),
      ],
      retry: (_, _) => null,
      child: MaterialApp(
        home: pushed
            ? Builder(
                builder: (context) => Scaffold(
                  body: TextButton(
                    onPressed: () => Navigator.of(
                      context,
                    ).push(MaterialPageRoute<void>(builder: (_) => body)),
                    child: const Text('열기'),
                  ),
                ),
              )
            : body,
      ),
    ),
  );
  if (pushed) {
    await tester.tap(find.text('열기'));
  }
  await tester.pumpAndSettle();
  return (source, network);
}

Future<void> _retry(WidgetTester tester) async {
  await tester.tap(find.text(AppStrings.retry));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('처음 불러오는 중이면 로딩, 받으면 내용을 보인다', (tester) async {
    final source = _Source();
    final gate = Completer<List<String>>();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          _sourceProvider.overrideWithValue(source),
          networkWatcherProvider.overrideWithValue(FakeNetworkWatcher()),
          _listProvider.overrideWith((ref) => gate.future),
        ],
        child: const MaterialApp(home: Scaffold(body: _Body())),
      ),
    );
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    gate.complete(['콩이']);
    await tester.pumpAndSettle();
    expect(find.text('콩이'), findsOneWidget);
  });

  testWidgets('inline 에 placeholder 를 주면 처음 불러오는 동안 로딩 대신 그것을 보인다(달력의 빈 칸)', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          networkWatcherProvider.overrideWithValue(FakeNetworkWatcher()),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: AsyncBody<int>.inline(
              value: const AsyncLoading(),
              onRetry: () {},
              placeholder: const Text('빈 칸'),
              builder: (v) => Text('$v'),
            ),
          ),
        ),
      ),
    );
    expect(find.text('빈 칸'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('값 없이 인터넷 없음이면 불러오기 문구와 [다시 시도], 인터넷이 돌아오면 스스로 다시 불러온다', (
    tester,
  ) async {
    final (source, network) = await _pump(tester, [
      _offline,
      ['콩이'],
    ]);
    expect(find.text(offlineLoadMessage), findsOneWidget);
    expect(find.text(AppStrings.retry), findsOneWidget);

    network.restore();
    await tester.pumpAndSettle();
    expect(source.calls, 2);
    expect(find.text('콩이'), findsOneWidget);
  });

  testWidgets('다시 시도하는 동안은 오류 대신 로딩을 보인다', (tester) async {
    final gate = Completer<List<String>>();
    await _pump(tester, [_server, gate]);

    await tester.tap(find.text(AppStrings.retry));
    await tester.pump();
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.text(AppStrings.retry), findsNothing);

    gate.complete(['콩이']);
    await tester.pumpAndSettle();
    expect(find.text('콩이'), findsOneWidget);
  });

  testWidgets('서버 오류로 실패하면 인터넷이 돌아와도 스스로 다시 부르지 않는다', (tester) async {
    final (source, network) = await _pump(tester, [_server]);
    expect(
      find.text('서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.'),
      findsOneWidget,
    );
    network.restore();
    await tester.pumpAndSettle();
    expect(source.calls, 1);
  });

  testWidgets('없어진 것(404)은 [다시 시도] 대신, 뒤로 갈 수 있으면 [돌아가기]', (tester) async {
    await _pump(tester, [_gone], pushed: true);
    expect(find.text('방문을 찾을 수 없어요. 이미 지워졌을 수 있어요.'), findsOneWidget);
    expect(find.text(AppStrings.retry), findsNothing);

    await tester.tap(find.text(AppStrings.goBack));
    await tester.pumpAndSettle();
    expect(find.text('열기'), findsOneWidget);
  });

  testWidgets('뒤로 갈 곳이 없으면(탭 화면) 없어진 것은 문구만 보인다', (tester) async {
    await _pump(tester, [_gone]);
    expect(find.text('방문을 찾을 수 없어요. 이미 지워졌을 수 있어요.'), findsOneWidget);
    expect(find.text(AppStrings.retry), findsNothing);
    expect(find.text(AppStrings.goBack), findsNothing);
  });

  testWidgets('받은 데이터가 있는데 새로 불러오다 서버 오류면 내용은 그대로, 위에 띠와 [다시 시도]', (
    tester,
  ) async {
    final (source, _) = await _pump(tester, [
      ['콩이'],
    ], refresh: true);
    source.next.addAll([
      _server,
      ['콩이', '보리'],
    ]);

    await tester.fling(find.text('콩이'), const Offset(0, 400), 1000);
    await tester.pumpAndSettle();
    expect(find.text('콩이'), findsOneWidget);
    expect(
      find.text('서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.'),
      findsOneWidget,
    );

    await _retry(tester);
    expect(find.text('보리'), findsOneWidget);
    expect(find.text(AppStrings.retry), findsNothing);
  });

  testWidgets('띠의 [다시 시도]를 누르면 결과가 올 때까지 버튼이 사라진다', (tester) async {
    final gate = Completer<List<String>>();
    final (source, _) = await _pump(tester, [
      ['콩이'],
    ], refresh: true);
    source.next.addAll([_server, gate]);

    await tester.fling(find.text('콩이'), const Offset(0, 400), 1000);
    await tester.pumpAndSettle();
    expect(find.text(AppStrings.retry), findsOneWidget);

    await tester.tap(find.text(AppStrings.retry));
    await tester.pump();
    expect(find.text('콩이'), findsOneWidget, reason: '데이터는 그대로 남는다');
    expect(
      find.text(AppStrings.retry),
      findsNothing,
      reason: '결과가 올 때까지 버튼을 감춘다',
    );

    gate.complete(['콩이', '보리']);
    await tester.pumpAndSettle();
    expect(find.text('보리'), findsOneWidget);
    expect(find.text(AppStrings.retry), findsNothing);
  });

  testWidgets('받은 데이터 위 인터넷 없음은 [다시 시도] 없는 띠, 인터넷이 돌아오면 스스로 다시 불러와 띠가 사라진다', (
    tester,
  ) async {
    final (source, network) = await _pump(tester, [
      ['콩이'],
    ], refresh: true);
    source.next.addAll([
      _offline,
      ['콩이', '보리'],
    ]);

    await tester.fling(find.text('콩이'), const Offset(0, 400), 1000);
    await tester.pumpAndSettle();
    expect(find.text(offlineBannerMessage), findsOneWidget);
    expect(find.text(AppStrings.retry), findsNothing);

    network.restore();
    await tester.pumpAndSettle();
    expect(find.text('보리'), findsOneWidget);
    expect(find.text(offlineBannerMessage), findsNothing);
  });
}

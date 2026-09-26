// 오류 화면 다듬기 완료 기준 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해 받은 데이터 위 띠(인터넷 없음·
// 서버 오류), 처음 실패의 원인 문구, 인터넷 복귀 때 스스로 다시 불러오기, 대기열 멈춤과 [다시 시도]를 확인한다.
// 도구는 `flow_kit.dart`.
//
// 기기의 연결은 흐름이 끊을 수 없다. 그래서 앱의 API `Dio`에 스위치([Outage])를 끼워 요청을 연결 실패나 503 으로
// 돌려보내고, 인터넷 복귀 신호는 [FlowNetwork]로 보낸다. 대기열의 간격 재시도는 흐름이 기다리지 않게 멈춰
// 둔다 — 복귀 신호가 곧 다시 시도다. 그 밖은 실제로 한다(서버·렌디션·업로드).
//
// 준비(infra/ 에서): bash ../app/tool/prepare_record_flow.sh → 마지막 줄의 --dart-define 들(실행마다 새로).
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/error_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>

import 'dart:async';

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/error/error_messages.dart';
import 'package:chagocnote/core/proxy/media_picker.dart';
import 'package:chagocnote/core/proxy/network_watcher.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/design/widgets/app_error_banner.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/state/upload_queue.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const shopId = int.fromEnvironment('SHOP');
const visitA = int.fromEnvironment('VISIT_A');
const visitB = int.fromEnvironment('VISIT_B');
const ownerName = String.fromEnvironment('OWNER');

enum OutageMode { offline, server }

/// 요청을 서버에 닿기 전에 돌려보내는 스위치. [mode]가 null 이면 그대로 보낸다.
class Outage extends Interceptor {
  OutageMode? mode;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    switch (mode) {
      case null:
        handler.next(options);
      case OutageMode.offline:
        handler.reject(
          DioException.connectionError(requestOptions: options, reason: '흐름: 끊김'),
        );
      case OutageMode.server:
        handler.reject(
          DioException.badResponse(
            statusCode: 503,
            requestOptions: options,
            response: Response(
              requestOptions: options,
              statusCode: 503,
              data: 'Service Unavailable',
            ),
          ),
        );
    }
  }
}

/// 인터넷 복귀 신호 — 흐름이 [restore]로 보낸다.
class FlowNetwork implements NetworkWatcher {
  final _controller = StreamController<void>.broadcast();

  @override
  Stream<void> get restored => _controller.stream;

  void restore() => _controller.add(null);
}

/// 대기열의 간격 재시도를 멈춰 둔다(돌지 않는 타이머).
Timer _never(Duration delay, void Function() run) => Timer(
  const Duration(days: 1),
  () {},
);

/// 카메라 대신 — 한 장.
class OnePhoto implements MediaPicker {
  var made = 0;

  @override
  Future<List<String>> pickPhotos({required int limit}) async => [
    await makePhoto('eflow-${made++}', made),
  ];

  @override
  Future<String?> takePhoto() => makePhoto('eflow-${made++}', made);
}

final outage = Outage();
final network = FlowNetwork();

String get today {
  final now = DateTime.now();
  String two(int n) => n.toString().padLeft(2, '0');
  return '${now.year}-${two(now.month)}-${two(now.day)}';
}

Finder bannerWith(String text) => find.descendant(
  of: find.byType(AppErrorBanner),
  matching: find.text(text),
);

Future<void> pull() async {
  final list = find.byWidgetPredicate(
    (w) => w is ListView && w.scrollDirection == Axis.vertical,
  );
  await t.fling(list.first, const Offset(0, 500), 1200);
  await pumpFor(const Duration(seconds: 2));
}

Future<int> photosOf(int visitId) async {
  final detail = await container.read(visitApiProvider).detail(shopId, visitId);
  return detail.record?.media.length ?? 0;
}

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('오류 화면 다듬기 완료 기준', timeout: const Timeout(Duration(minutes: 15)), (
    tester,
  ) async {
    t = tester;
    await initializeGlass();
    await t.pumpWidget(
      buildRoot(
        overrides: [
          dioProvider.overrideWith(
            (ref) => Dio(
              BaseOptions(
                baseUrl: ref.watch(appConfigProvider).apiBaseUrl,
                connectTimeout: const Duration(seconds: 10),
                receiveTimeout: const Duration(seconds: 15),
                sendTimeout: const Duration(seconds: 15),
              ),
            )..interceptors.add(outage),
          ),
          networkWatcherProvider.overrideWithValue(network),
          uploadRetrySchedulerProvider.overrideWithValue(_never),
          mediaPickerProvider.overrideWithValue(OnePhoto()),
        ],
      ),
    );
    final end = DateTime.now().add(const Duration(seconds: 40));
    while (DateTime.now().isBefore(end)) {
      await t.pump(const Duration(milliseconds: 100));
      drain();
      if (find.byKey(ScreenKeys.login).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.home).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.shopSelect).evaluate().isNotEmpty) {
        break;
      }
    }
    if (find.byKey(ScreenKeys.login).evaluate().isEmpty) await logout();
    await login(ownerName);

    await step('1', '하루 목록 — 당겼는데 인터넷 없음이면 목록은 두고 띠, 돌아오면 스스로 다시 불러와 띠가 사라진다', () async {
      router.push('/visits/day/$today');
      await waitFor(find.byKey(ScreenKeys.day));
      await waitFor(find.text('콩이').first);
      outage.mode = OutageMode.offline;
      await pull();
      await shot('01a-offline-banner');
      soft(bannerWith(offlineBannerMessage).evaluate().isNotEmpty, '인터넷 없음 띠가 없다');
      soft(find.text('콩이').evaluate().isNotEmpty, '받은 목록이 사라졌다');
      soft(find.text(AppStrings.retry).evaluate().isEmpty, '인터넷 없음 띠에 [다시 시도]가 있다');

      outage.mode = null;
      network.restore();
      await pumpFor(const Duration(seconds: 2));
      await shot('01b-restored');
      soft(find.byType(AppErrorBanner).evaluate().isEmpty, '돌아왔는데 띠가 남았다');
    });

    await step('2', '하루 목록 — 서버 오류면 띠에 [다시 시도], 누르면 다시 불러와 띠가 사라진다', () async {
      outage.mode = OutageMode.server;
      await pull();
      await shot('02a-server-banner');
      soft(
        bannerWith('서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.').evaluate().isNotEmpty,
        '서버 오류 띠가 없다',
      );
      outage.mode = null;
      await tap(find.descendant(of: find.byType(AppErrorBanner), matching: find.text(AppStrings.retry)));
      await pumpFor(const Duration(seconds: 2));
      await shot('02b-retried');
      soft(find.byType(AppErrorBanner).evaluate().isEmpty, '다시 불러왔는데 띠가 남았다');
    });

    await step('3', '방문 상세 — 처음부터 인터넷 없음이면 원인 문구와 [다시 시도], 돌아오면 스스로 연다', () async {
      outage.mode = OutageMode.offline;
      router.push('/visits/$visitA');
      await waitFor(find.text(offlineLoadMessage));
      await shot('03a-offline-first');
      soft(find.text(AppStrings.retry).evaluate().isNotEmpty, '[다시 시도]가 없다');
      outage.mode = null;
      network.restore();
      await waitFor(p(AppStrings.addPhoto));
      await shot('03b-opened');
    });

    await step('4', '대기열 — 다시 해도 안 되는 실패(미용 전으로 되돌린 방문)면 멈춰 느낌표, 시작한 뒤 [다시 시도]로 붙는다', () async {
      await openVisit(visitB);
      outage.mode = OutageMode.offline;
      await tap(p(AppStrings.addPhoto));
      await tap(btn(AppStrings.takePhoto));
      await waitFor(find.text(AppStrings.uploadWaiting));
      await shot('04a-waiting');

      // 서버에서 방문을 미용 전으로 되돌린다 — 덧붙이기가 VISIT_NO_RECORD_YET(422)로 거절된다.
      outage.mode = null;
      final api = container.read(visitApiProvider);
      await api.transition(shopId, visitIds: [visitB], action: VisitAction.revert);
      network.restore();
      await waitFor(find.byIcon(Icons.priority_high), timeout: const Duration(seconds: 60));
      await shot('04b-stopped');
      final job = container.read(uploadQueueProvider).value!.single;
      note('멈춘 이유 ${job.stoppedCode}');
      soft(job.stoppedCode == 'VISIT_NO_RECORD_YET', '멈춘 이유가 다르다');

      await api.transition(shopId, visitIds: [visitB], action: VisitAction.start);
      await tap(p(AppStrings.uploadStopped));
      await waitFor(find.text('미용을 시작한 방문에만 기록을 쓸 수 있어요.'));
      await shot('04c-sheet');
      await tap(find.text(AppStrings.retry));
      final end = DateTime.now().add(const Duration(seconds: 60));
      while (await photosOf(visitB) < 1) {
        if (DateTime.now().isAfter(end)) throw TestFailure('사진이 붙지 않았다');
        await pumpFor(const Duration(seconds: 1));
      }
      await pumpFor(const Duration(seconds: 2));
      await shot('04d-attached');
      soft(container.read(uploadQueueProvider).value!.isEmpty, '대기열이 비지 않았다');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}

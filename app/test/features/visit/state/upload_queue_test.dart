import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:chagocnote/core/proxy/app_dirs.dart';
import 'package:chagocnote/core/proxy/network_watcher.dart';
import 'package:chagocnote/core/proxy/photo_renditions.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/visit/api/record_models.dart';
import 'package:chagocnote/features/visit/state/upload_job.dart';
import 'package:chagocnote/features/visit/state/upload_queue.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/upload_fakes.dart';
import '../../../support/visit_fixtures.dart';

/// 대기열 하나를 둘러싼 가짜들 — API 서버, 저장소(서명 URL PUT), 렌디션, 인터넷 신호, 다시 시도 예약.
class _Env {
  _Env(this.root, {List<UploadJob>? saved}) {
    if (saved != null) {
      File(
        '${root.path}/queue.json',
      ).writeAsStringSync(jsonEncode([for (final j in saved) j.toJson()]));
      for (final j in saved) {
        final dir = Directory('${root.path}/${j.id}')..createSync();
        for (final name in ['original', 'display', 'thumb']) {
          File('${dir.path}/$name.jpg').writeAsBytesSync([1, 2, 3]);
        }
      }
    }
    setup = CustomerTestSetup(
      _api,
      overrides: [
        uploadsDirProvider.overrideWith((ref) async => root),
        photoRenditionMakerProvider.overrideWithValue(maker),
        networkWatcherProvider.overrideWithValue(network),
        uploadRetrySchedulerProvider.overrideWithValue(retries.call),
        uploadDioProvider.overrideWithValue(
          Dio(BaseOptions())..httpClientAdapter = storage,
        ),
      ],
    );
  }

  final Directory root;
  late final CustomerTestSetup setup;
  final maker = FakeRenditionMaker();
  final network = FakeNetworkWatcher();
  final retries = FakeRetryScheduler();

  /// 발급할 때마다 51, 52… 를 준다.
  int nextMediaId = 51;
  final calls = <String>[];
  FutureOr<FakeResponse>? Function(String call)? apiFailure;
  FutureOr<FakeResponse>? Function(RequestOptions put)? storageFailure;

  late final storage = FakeHttpClientAdapter((options, body) async {
    calls.add('PUT ${options.uri.path} ${options.headers['content-type']}');
    final failure = storageFailure?.call(options);
    if (failure != null) return failure;
    return const FakeResponse(statusCode: 200);
  });

  Future<FakeResponse> _api(RequestOptions options, List<int>? body) async {
    final call = '${options.method} ${options.path}';
    calls.add(call);
    final failure = apiFailure?.call(call);
    if (failure != null) return await failure;
    return switch (call) {
      'POST /v1/shops/3/media/uploads' => FakeResponse(
        statusCode: 201,
        data: issuedUploadJson(mediaId: nextMediaId++),
      ),
      'POST /v1/shops/3/media/51/confirm' ||
      'POST /v1/shops/3/media/52/confirm' => const FakeResponse(
        statusCode: 200,
        data: {},
      ),
      'POST /v1/shops/3/visits/101/record/media' => FakeResponse(
        statusCode: 200,
        data: recordJson(media: [recordMediaJson()]),
      ),
      _ => throw StateError('예상하지 못한 요청: $call'),
    };
  }

  UploadQueue get queue => setup.container.read(uploadQueueProvider.notifier);

  List<UploadJob> get jobs =>
      setup.container.read(uploadQueueProvider).value ?? const [];

  /// 로그인해 두고 대기열을 연다.
  Future<void> open() async {
    await setup.container.read(sessionControllerProvider.future);
    await setup.container.read(uploadQueueProvider.future);
  }

  List<Map<String, dynamic>> get savedJson =>
      (jsonDecode(File('${root.path}/queue.json').readAsStringSync()) as List)
          .cast<Map<String, dynamic>>();

  /// 다 붙어서 대기열·폴더·기기의 목록이 모두 비었다(파일 지우기는 목록을 비운 뒤에 끝난다).
  bool get drained => jobs.isEmpty && folders.isEmpty && savedJson.isEmpty;

  List<String> get folders => [
    for (final e in root.listSync())
      if (e is Directory) e.path.split('/').last,
  ];
}

/// 조건이 설 때까지 진짜 시간으로 조금씩 기다린다(파일 입출력이 있어 가짜 시간을 쓰지 않는다).
Future<void> _until(bool Function() condition) async {
  for (var i = 0; i < 2000; i++) {
    if (condition()) return;
    await Future<void>.delayed(const Duration(milliseconds: 5));
  }
  fail('기다린 일이 일어나지 않았다');
}

/// 렌디션 셋은 동시에 올린다 — 도착 순서는 정해지지 않으니 연달아 온 PUT 은 이름순으로 맞춰 본다.
List<String> _ordered(List<String> calls) {
  final out = <String>[];
  var run = <String>[];
  for (final c in [...calls, '']) {
    if (c.startsWith('PUT ')) {
      run.add(c);
      continue;
    }
    out.addAll(run..sort());
    run = [];
    if (c.isNotEmpty) out.add(c);
  }
  return out;
}

const _uploadCalls = [
  'POST /v1/shops/3/media/uploads',
  'PUT /b/display/shops/3/51.jpg image/jpeg',
  'PUT /b/original/shops/3/51.jpg image/jpeg',
  'PUT /b/thumb/shops/3/51.jpg image/jpeg',
  'POST /v1/shops/3/media/51/confirm',
];

UploadJob _saved(
  String id, {
  UploadStage stage = UploadStage.prepared,
  int? mediaId,
  int userId = 1,
}) => UploadJob(
  id: id,
  userId: userId,
  shopId: 3,
  visitId: 101,
  phase: MediaPhase.before,
  stage: stage,
  width: 3000,
  height: 2000,
  mediaId: mediaId,
);

void main() {
  late Directory root;
  setUp(() async => root = await Directory.systemTemp.createTemp('uploads'));
  tearDown(() async => root.delete(recursive: true));

  _Env env0({List<UploadJob>? saved}) {
    final env = _Env(root, saved: saved);
    addTearDown(env.setup.container.dispose);
    return env;
  }

  test('다시 시도 간격은 1·2·4… 초, 최대 5분이다', () {
    expect(
      [for (var n = 1; n <= 11; n++) retryDelay(n).inSeconds],
      [1, 2, 4, 8, 16, 32, 64, 128, 256, 300, 300],
    );
  });

  test('사진을 넣으면 렌디션 → 발급 → 셋을 올리고 → 확인 → 덧붙이기, 붙으면 대기열과 파일에서 빠진다', () async {
    final env = env0();
    await env.open();

    await env.queue.addPhotos(
      shopId: 3,
      visitId: 101,
      phase: MediaPhase.after,
      sources: ['/picked/a.heic'],
    );
    await _until(() => env.drained);

    expect(_ordered(env.calls), [
      ..._uploadCalls,
      'POST /v1/shops/3/visits/101/record/media',
    ]);
    final append = env
        .setup
        .adapter
        .lastBodyByPath['/v1/shops/3/visits/101/record/media']!;
    expect(jsonDecode(utf8.decode(append)), {'media_id': 51, 'phase': 'after'});
    final issue =
        env.setup.adapter.lastBodyByPath['/v1/shops/3/media/uploads']!;
    expect(
      jsonDecode(utf8.decode(issue))['byte_size'],
      FakeRenditionMaker.sizes.original,
    );
    expect(
      env.storage.requests.every(
        (r) => !r.headers.containsKey('Authorization'),
      ),
      isTrue,
    );
    expect(env.folders, isEmpty);
    expect(env.savedJson, isEmpty);
  });

  test('올리는 동안 타일은 진행률을 보이고, 발급 전 렌디션이 앱 폴더에 남는다', () async {
    final env = env0();
    final gate = Completer<FakeResponse>();
    env.storageFailure = (put) =>
        put.path.contains('original') ? gate.future : null;
    await env.open();

    await env.queue.addPhotos(
      shopId: 3,
      visitId: 101,
      phase: MediaPhase.before,
      sources: ['/picked/a.jpg'],
    );
    await _until(() => env.jobs.single.running && env.jobs.single.progress > 0);

    final job = env.jobs.single;
    expect(job.stage, UploadStage.prepared);
    expect(File(job.thumbPath!).existsSync(), isTrue);
    expect(env.savedJson.single['stage'], 'prepared');
    expect(
      env.setup.container.read(visitUploadsProvider(101)).single.id,
      job.id,
    );
    expect(env.setup.container.read(visitUploadsProvider(102)), isEmpty);

    gate.complete(const FakeResponse(statusCode: 200));
    await _until(() => env.drained);
  });

  test('앱을 다시 켜면 남은 단계부터 — 확인된 사진은 덧붙이기만, 준비된 사진은 발급부터', () async {
    final env = env0(
      saved: [
        _saved('j1', stage: UploadStage.confirmed, mediaId: 77),
        _saved('j2'),
      ],
    );
    env.apiFailure = (call) =>
        call == 'POST /v1/shops/3/visits/101/record/media'
        ? FakeResponse(statusCode: 200, data: recordJson())
        : null;

    await env.open();
    await _until(() => env.drained);

    expect(_ordered(env.calls), [
      'POST /v1/shops/3/visits/101/record/media',
      ..._uploadCalls,
      'POST /v1/shops/3/visits/101/record/media',
    ]);
    expect(env.folders, isEmpty);
  });

  test('확인까지 끝나면 미디어 ID 를 기기에 남긴다 — 덧붙이기 전에 꺼져도 다시 올리지 않는다', () async {
    final env = env0();
    env.apiFailure = (call) => call.endsWith('/record/media')
        ? const FakeResponse(
            statusCode: 503,
            data: {'code': 'HTTP_ERROR', 'message': 'x'},
          )
        : null;
    await env.open();

    await env.queue.addPhotos(
      shopId: 3,
      visitId: 101,
      phase: MediaPhase.before,
      sources: ['/picked/a.jpg'],
    );
    await _until(() => env.jobs.single.waiting);

    expect(env.savedJson.single['stage'], 'confirmed');
    expect(env.savedJson.single['media_id'], 51);
  });

  test('실패하면 "대기 중"으로 남고 간격을 늘려 스스로, 인터넷이 돌아오면 바로 다시 한다', () async {
    final env = env0();
    var down = true;
    env.apiFailure = (call) => down && call == 'POST /v1/shops/3/media/uploads'
        ? throw DioException.connectionError(
            requestOptions: RequestOptions(),
            reason: '끊김',
          )
        : null;
    await env.open();

    await env.queue.addPhotos(
      shopId: 3,
      visitId: 101,
      phase: MediaPhase.before,
      sources: ['/picked/a.jpg'],
    );
    await _until(() => env.jobs.single.waiting);
    expect(env.jobs.single.failures, 1);

    env.retries.fire();
    await _until(
      () => env.jobs.single.failures == 2 && env.jobs.single.waiting,
    );
    env.retries.fire();
    await _until(
      () => env.jobs.single.failures == 3 && env.jobs.single.waiting,
    );
    expect(env.retries.delays, [
      const Duration(seconds: 1),
      const Duration(seconds: 2),
      const Duration(seconds: 4),
    ]);

    down = false;
    env.network.restore();
    await _until(() => env.drained);
    expect(
      env.calls.where((c) => c == 'POST /v1/shops/3/media/uploads'),
      hasLength(4),
    );
  });

  test('서명 URL 이 만료돼 저장소가 거절하면 다음 시도는 발급부터 다시 한다', () async {
    final env = env0();
    var expired = true;
    env.storageFailure = (put) => expired
        ? const FakeResponse(
            statusCode: 403,
            data: '<Error><Code>AccessDenied</Code></Error>',
          )
        : null;
    await env.open();

    await env.queue.addPhotos(
      shopId: 3,
      visitId: 101,
      phase: MediaPhase.before,
      sources: ['/picked/a.jpg'],
    );
    await _until(() => env.jobs.single.waiting);
    expired = false;
    env.retries.fire();
    await _until(() => env.drained);

    expect(env.calls.where((c) => c.startsWith('POST /v1/shops/3/media/')), [
      'POST /v1/shops/3/media/uploads',
      'POST /v1/shops/3/media/uploads',
      'POST /v1/shops/3/media/52/confirm',
    ]);
  });

  test('서버가 붙지 않은 사진을 정리했으면(MEDIA_NOT_FOUND) 간격을 두고 로컬 파일로 발급부터 다시 한다', () async {
    final env = env0(
      saved: [_saved('j1', stage: UploadStage.confirmed, mediaId: 40)],
    );
    var purged = true;
    env.apiFailure = (call) {
      if (call != 'POST /v1/shops/3/visits/101/record/media' || !purged) {
        return null;
      }
      purged = false;
      return const FakeResponse(
        statusCode: 404,
        data: {'code': 'MEDIA_NOT_FOUND', 'message': 'x'},
      );
    };

    await env.open();
    await _until(() => env.jobs.single.waiting);
    expect(env.jobs.single.stage, UploadStage.prepared);
    expect(env.jobs.single.mediaId, isNull);
    env.retries.fire();
    await _until(() => env.drained);

    expect(_ordered(env.calls), [
      'POST /v1/shops/3/visits/101/record/media',
      ..._uploadCalls,
      'POST /v1/shops/3/visits/101/record/media',
    ]);
    expect(env.retries.delays, [const Duration(seconds: 1)]);
  });

  test('덧붙이기가 계속 MEDIA_NOT_FOUND 여도 쉬지 않고 다시 올리지 않는다 — 재발급마다 간격을 늘린다', () async {
    final env = env0(
      saved: [_saved('j1', stage: UploadStage.confirmed, mediaId: 40)],
    );
    env.apiFailure = (call) =>
        call == 'POST /v1/shops/3/visits/101/record/media'
        ? const FakeResponse(
            statusCode: 404,
            data: {'code': 'MEDIA_NOT_FOUND', 'message': 'x'},
          )
        : null;

    await env.open();
    await _until(() => env.jobs.single.waiting);
    expect(env.calls, ['POST /v1/shops/3/visits/101/record/media']);

    env.retries.fire();
    await _until(
      () => env.jobs.single.failures == 2 && env.jobs.single.waiting,
    );
    expect(_ordered(env.calls), [
      'POST /v1/shops/3/visits/101/record/media',
      ..._uploadCalls,
      'POST /v1/shops/3/visits/101/record/media',
    ]);
    expect(env.retries.delays, [
      const Duration(seconds: 1),
      const Duration(seconds: 2),
    ]);
  });

  test('올리는 중에 빼면 취소하고 조용히 끝낸다 — 다시 시도도 덧붙이기도 없고 파일은 지운다', () async {
    final env = env0();
    final gate = Completer<FakeResponse>();
    env.storageFailure = (put) =>
        put.path.contains('original') ? gate.future : null;
    await env.open();
    await env.queue.addPhotos(
      shopId: 3,
      visitId: 101,
      phase: MediaPhase.before,
      sources: ['/picked/a.jpg'],
    );
    await _until(() => env.jobs.single.running && env.jobs.single.progress > 0);

    await env.queue.remove(env.jobs.single.id);
    await Future<void>.delayed(const Duration(milliseconds: 50));

    expect(env.jobs, isEmpty);
    expect(env.retries.delays, isEmpty);
    expect(
      env.calls.where((c) => c.contains('confirm') || c.contains('record')),
      isEmpty,
    );
    expect(env.folders, isEmpty);
    expect(env.savedJson, isEmpty);
  });

  test('읽을 수 없는 사진은 대기열에서 빠지고 나머지는 올린다', () async {
    final env = env0();
    env.maker.broken.add('/picked/broken.jpg');
    await env.open();

    await env.queue.addPhotos(
      shopId: 3,
      visitId: 101,
      phase: MediaPhase.before,
      sources: ['/picked/broken.jpg', '/picked/a.jpg'],
    );
    await _until(() => env.drained);

    expect(
      env.calls.where((c) => c == 'POST /v1/shops/3/media/uploads'),
      hasLength(1),
    );
    expect(env.folders, isEmpty);
  });

  test('로그아웃하면 대기열과 파일을 지운다', () async {
    final env = env0(saved: [_saved('j1')]);
    env.apiFailure = (call) => const FakeResponse(
      statusCode: 503,
      data: {'code': 'HTTP_ERROR', 'message': 'x'},
    );
    await env.open();
    await _until(() => env.jobs.single.waiting);

    await env.setup.container
        .read(sessionControllerProvider.notifier)
        .signOut();
    await _until(() => env.drained);

    await _until(() => env.folders.isEmpty);
    expect(env.savedJson, isEmpty);
  });

  test('세션이 만료되면 남겨 두고, 다른 사람이 로그인하면 그 사람 것이 아닌 항목을 지운다', () async {
    final env = env0(saved: [_saved('j1')]);
    env.apiFailure = (call) => const FakeResponse(
      statusCode: 503,
      data: {'code': 'HTTP_ERROR', 'message': 'x'},
    );
    await env.open();
    await _until(() => env.jobs.single.waiting);
    final controller = env.setup.container.read(
      sessionControllerProvider.notifier,
    );

    controller.endSession();
    await Future<void>.delayed(const Duration(milliseconds: 20));
    expect(env.jobs, hasLength(1));
    expect(env.folders, ['j1']);

    env.setup.gateway.meOnSignIn = Me(
      id: 2,
      displayName: '직원',
      profileImageUrl: null,
      identities: const ['kakao'],
      shops: [customerTestMe().shops.single],
    );
    await controller.signIn(
      const SocialCredential(provider: 'kakao', token: 't'),
    );
    await _until(() => env.jobs.isEmpty && env.folders.isEmpty);
  });

  test('처음 열 때 이 사람 것이 아니거나 이제 멤버가 아닌 매장의 항목, 목록에 없는 폴더를 지운다', () async {
    final other = UploadJob(
      id: 'j3',
      userId: 1,
      shopId: 99,
      visitId: 5,
      phase: MediaPhase.before,
      stage: UploadStage.prepared,
    );
    final env = env0(saved: [_saved('j1', userId: 2), other]);
    Directory('${root.path}/stray').createSync();
    await env.setup.container.read(sessionControllerProvider.future);
    expect(
      env.setup.container.read(sessionControllerProvider).value,
      isA<SignedIn>(),
    );

    await env.setup.container.read(uploadQueueProvider.future);

    expect(env.jobs, isEmpty);
    expect(env.folders, isEmpty);
    expect(env.calls, isEmpty);
  });

  test('대기열이 사라지면(앱 종료) 올리던 것을 취소하되 실패로 세지 않고, 기기의 목록은 남는다', () async {
    final env = env0();
    final gate = Completer<FakeResponse>();
    env.storageFailure = (put) =>
        put.path.contains('original') ? gate.future : null;
    await env.open();
    await env.queue.addPhotos(
      shopId: 3,
      visitId: 101,
      phase: MediaPhase.before,
      sources: ['/picked/a.jpg'],
    );
    await _until(() => env.jobs.single.running && env.jobs.single.progress > 0);

    env.setup.container.dispose();
    await Future<void>.delayed(const Duration(milliseconds: 50));

    expect(env.retries.delays, isEmpty);
    expect(env.savedJson.single['stage'], 'prepared');
    expect(env.folders, hasLength(1));
  });
}

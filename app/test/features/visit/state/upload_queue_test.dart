import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/app_dirs.dart';
import 'package:chagocnote/core/proxy/photo_renditions.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/proxy/video_transcoder.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/customer/state/customer_providers.dart';
import 'package:chagocnote/features/visit/api/record_models.dart';
import 'package:chagocnote/features/visit/state/feed_controller.dart';
import 'package:chagocnote/features/visit/state/upload_job.dart';
import 'package:chagocnote/features/visit/state/upload_queue.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
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
        final names = j.kind == MediaKind.video
            ? ['video.mp4', 'thumb.jpg']
            : ['original.jpg', 'display.jpg', 'thumb.jpg'];
        for (final name in names) {
          File('${dir.path}/$name').writeAsBytesSync([1, 2, 3]);
        }
      }
    }
    setup = CustomerTestSetup(
      _api,
      overrides: [
        uploadsDirProvider.overrideWith((ref) async => root),
        photoRenditionMakerProvider.overrideWithValue(maker),
        videoTranscoderProvider.overrideWithValue(transcoder),
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
  final transcoder = FakeVideoTranscoder();
  FakeNetworkWatcher get network => setup.network;
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
    if (call == 'POST /v1/shops/3/media/uploads' &&
        jsonDecode(utf8.decode(body!))['kind'] == 'video') {
      return FakeResponse(
        statusCode: 201,
        data: _issuedVideoJson(nextMediaId++),
      );
    }
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
      'GET /v1/shops/3/visits/feed' => FakeResponse(
        statusCode: 200,
        data: feedJson(),
      ),
      'GET /v1/shops/3/pets/7' => FakeResponse(
        statusCode: 200,
        data: petDetailJson(),
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

/// 영상 발급 응답 — 올릴 곳은 mp4·포스터 둘이다(display 없음).
Map<String, dynamic> _issuedVideoJson(int mediaId) => {
  'media_id': mediaId,
  'puts': {
    'original': 'http://media.test/b/original/shops/3/$mediaId.mp4?put=1',
    'display': null,
    'thumb': 'http://media.test/b/thumb/shops/3/$mediaId.jpg?put=1',
  },
  'expires_at': '2026-09-25T10:15:00+09:00',
};

const _videoUploadCalls = [
  'POST /v1/shops/3/media/uploads',
  'PUT /b/original/shops/3/51.mp4 video/mp4',
  'PUT /b/thumb/shops/3/51.jpg image/jpeg',
  'POST /v1/shops/3/media/51/confirm',
];

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
  String? stoppedCode,
  MediaKind kind = MediaKind.photo,
  int? durationSeconds,
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
  stoppedCode: stoppedCode,
  kind: kind,
  durationSeconds: durationSeconds,
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

  /// 고른 영상 파일(가짜 압축기가 이것을 video.mp4 로 복사한다).
  const videoBytes = 4096;
  String videoSource() {
    final picked = Directory.systemTemp.createTempSync('picked');
    addTearDown(() => picked.delete(recursive: true));
    final file = File('${picked.path}/clip.mov')
      ..writeAsBytesSync(List<int>.filled(videoBytes, 9));
    return file.path;
  }

  Future<VideoAddOutcome> addVideo(_Env env, String source) =>
      env.queue.addVideo(
        shopId: 3,
        visitId: 101,
        phase: MediaPhase.after,
        source: source,
      );

  Map<String, dynamic> issueBody(_Env env) =>
      jsonDecode(
            utf8.decode(
              env.setup.adapter.lastBodyByPath['/v1/shops/3/media/uploads']!,
            ),
          )
          as Map<String, dynamic>;

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

  test('붙은 뒤 피드와 반려동물 상세(프로필 사진)를 다시 읽는다', () async {
    final env = env0();
    await env.open();
    final c = env.setup.container;
    final feed = c.listen(
      feedControllerProvider((shopId: 3, petId: null)),
      (_, _) {},
    );
    final pet = c.listen(petDetailProvider((shopId: 3, petId: 7)), (_, _) {});
    addTearDown(feed.close);
    addTearDown(pet.close);
    List<String> reads() => [
      for (final call in env.calls)
        if (call.startsWith('GET')) call,
    ]..sort();
    await _until(() => reads().length == 2);

    await env.queue.addPhotos(
      shopId: 3,
      visitId: 101,
      phase: MediaPhase.after,
      sources: ['/picked/a.heic'],
    );
    await _until(() => env.drained);
    // 다시 읽기는 무효화 뒤 한 틈에 나간다.
    await Future<void>.delayed(const Duration(milliseconds: 50));

    expect(reads(), [
      'GET /v1/shops/3/pets/7',
      'GET /v1/shops/3/pets/7',
      'GET /v1/shops/3/visits/feed',
      'GET /v1/shops/3/visits/feed',
    ]);
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

  test('다시 해도 안 되는 실패는 권한·없음·업무 4xx 다 — 인터넷·서버·세션 만료·잦은 시도는 다시 해 본다', () {
    ApiException error(int status, String code) =>
        ApiException(statusCode: status, code: code, message: 'x');
    expect(stopsUpload(error(422, 'MEDIA_LIMIT_EXCEEDED')), isTrue);
    expect(stopsUpload(error(409, 'MEDIA_ALREADY_ATTACHED')), isTrue);
    expect(stopsUpload(error(403, 'PERMISSION_DENIED')), isTrue);
    expect(stopsUpload(error(404, 'VISIT_NOT_FOUND')), isTrue);
    expect(stopsUpload(ApiException.network('끊김')), isFalse);
    expect(stopsUpload(error(503, 'HTTP_ERROR')), isFalse);
    expect(stopsUpload(error(401, 'UNAUTHENTICATED')), isFalse);
    expect(stopsUpload(error(429, 'TOO_MANY_ATTEMPTS')), isFalse);
    expect(stopsUpload(StateError('x')), isFalse);
  });

  test('다시 해도 안 되는 실패면 멈추고 이유를 기기에 남긴다 — 스스로도, 인터넷이 돌아와도 다시 하지 않고 파일은 남는다', () async {
    final env = env0();
    var full = true;
    env.apiFailure = (call) => full && call == 'POST /v1/shops/3/media/uploads'
        ? const FakeResponse(
            statusCode: 422,
            data: {'code': 'MEDIA_LIMIT_EXCEEDED', 'message': 'x'},
          )
        : null;
    await env.open();

    await env.queue.addPhotos(
      shopId: 3,
      visitId: 101,
      phase: MediaPhase.before,
      sources: ['/picked/a.jpg'],
    );
    await _until(
      () => env.jobs.single.stopped && env.savedJson.single['stopped_code'] != null,
    );

    final job = env.jobs.single;
    expect(job.stoppedCode, 'MEDIA_LIMIT_EXCEEDED');
    expect(job.waiting, isFalse);
    expect(env.retries.delays, isEmpty, reason: '간격 재시도를 잡지 않는다');
    expect(env.savedJson.single['stopped_code'], 'MEDIA_LIMIT_EXCEEDED');
    expect(env.folders, [job.id]);

    env.network.restore();
    await Future<void>.delayed(const Duration(milliseconds: 50));
    expect(
      env.calls.where((c) => c == 'POST /v1/shops/3/media/uploads'),
      hasLength(1),
    );

    // 사용자가 다른 사진을 지워 자리를 낸 뒤 [다시 시도].
    full = false;
    await env.queue.retry(job.id);
    await _until(() => env.drained);
  });

  test('멈춘 항목은 앱을 다시 켜도 멈춰 있고, 멈춤 칸이 없던 옛 항목은 그대로 올린다', () async {
    final env = env0(
      saved: [
        _saved('j1', stoppedCode: 'VISIT_NOT_FOUND'),
        _saved('j2'),
      ],
    );
    env.apiFailure = (call) => call == 'POST /v1/shops/3/visits/101/record/media'
        ? FakeResponse(statusCode: 200, data: recordJson())
        : null;
    // 옛 항목 j2 는 stopped_code 없이 저장돼 있었다.
    final saved = env.savedJson;
    expect(saved.last.containsKey('stopped_code'), isTrue);
    File('${root.path}/queue.json').writeAsStringSync(
      jsonEncode([saved.first, {...saved.last}..remove('stopped_code')]),
    );

    await env.open();
    await _until(() => env.jobs.length == 1 && env.folders.length == 1);

    expect(env.jobs.single.id, 'j1');
    expect(env.jobs.single.stoppedCode, 'VISIT_NOT_FOUND');
    expect(env.folders, ['j1']);
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

  test('영상을 넣으면 압축 진행률이 타일에 흐르고, 끝나면 mp4·포스터 둘을 올리고 확인·덧붙이기까지 간다', () async {
    final env = env0();
    final gate = env.transcoder.gate = Completer<void>();
    env.transcoder.progressSteps = const [0.25, 0.5];
    await env.open();
    final seen = <double>[];
    final sub = env.setup.container.listen(uploadQueueProvider, (_, next) {
      for (final j in next.value ?? const <UploadJob>[]) {
        if (j.stage == UploadStage.preparing) seen.add(j.progress);
      }
    });
    addTearDown(sub.close);

    final added = addVideo(env, videoSource());
    await _until(() => env.transcoder.calls.length == 1);

    final job = env.jobs.single;
    expect(job.kind, MediaKind.video);
    expect(job.stage, UploadStage.preparing);
    expect(job.progress, 0);
    expect(env.transcoder.calls.single.$2, 60);

    gate.complete();
    expect(await added, VideoAddOutcome.added);
    await _until(() => env.drained);

    expect(seen, containsAllInOrder([0.25, 0.5]));
    expect(_ordered(env.calls), [
      ..._videoUploadCalls,
      'POST /v1/shops/3/visits/101/record/media',
    ]);
    expect(issueBody(env), {
      'kind': 'video',
      'content_type': 'video/mp4',
      'byte_size': videoBytes,
      'width': 1080,
      'height': 1920,
      'duration_seconds': 5,
    });
    expect(env.folders, isEmpty);
  });

  test('60초를 넘는 영상은 앞부분만 올렸다고 알린다', () async {
    final env = env0();
    env.transcoder
      ..trimmed = true
      ..durationSeconds = 60;
    await env.open();

    expect(await addVideo(env, videoSource()), VideoAddOutcome.trimmed);
    await _until(() => env.drained);

    expect(issueBody(env)['duration_seconds'], 60);
  });

  test('압축할 수 없는 영상은 대기열에서 빼고 이유를 돌려준다', () async {
    final env = env0();
    await env.open();

    env.transcoder.failWith = 'UNSUPPORTED';
    expect(await addVideo(env, videoSource()), VideoAddOutcome.unsupported);
    expect(env.jobs, isEmpty);
    expect(env.folders, isEmpty);

    env.transcoder.failWith = 'TOO_SHORT';
    expect(await addVideo(env, videoSource()), VideoAddOutcome.tooShort);
    expect(env.jobs, isEmpty);
    expect(env.folders, isEmpty);
    expect(env.calls, isEmpty);
  });

  test('압축 중 [올리기 취소]하면 네이티브를 취소하고 조용히 뺀다', () async {
    final env = env0();
    env.transcoder.gate = Completer<void>();
    await env.open();

    final added = addVideo(env, videoSource());
    await _until(() => env.transcoder.calls.length == 1);
    final outcome = expectLater(added, completion(VideoAddOutcome.cancelled));

    await env.queue.remove(env.jobs.single.id);
    expect(env.transcoder.cancelled, 1);
    await outcome;

    expect(env.jobs, isEmpty);
    expect(env.folders, isEmpty);
    expect(env.calls, isEmpty);
  });

  test('영상 둘을 연달아 넣으면 압축은 순서대로 돈다', () async {
    final env = env0();
    final gate = env.transcoder.gate = Completer<void>();
    await env.open();

    final first = addVideo(env, videoSource());
    final second = addVideo(env, videoSource());
    await _until(() => env.jobs.length == 2);
    await Future<void>.delayed(const Duration(milliseconds: 50));

    expect(env.transcoder.calls, hasLength(1));
    expect(env.jobs.last.stage, UploadStage.preparing);
    expect(env.jobs.last.progress, 0);

    gate.complete();
    expect(await first, VideoAddOutcome.added);
    expect(await second, VideoAddOutcome.added);
    expect(env.transcoder.calls, hasLength(2));
    await _until(() => env.drained);
  });

  test('압축 중인 첫째를 [올리기 취소]해도 기다리던 둘째는 이어서 압축한다', () async {
    final env = env0();
    env.transcoder.gate = Completer<void>();
    await env.open();

    final first = addVideo(env, videoSource());
    final second = addVideo(env, videoSource());
    await _until(
      () => env.jobs.length == 2 && env.transcoder.calls.length == 1,
    );
    final firstOutcome = expectLater(
      first,
      completion(VideoAddOutcome.cancelled),
    );

    // 취소가 붙든 압축을 끝낸 뒤 둘째는 붙들지 않는다.
    final removing = env.queue.remove(env.jobs.first.id);
    env.transcoder.gate = null;
    await removing;
    await firstOutcome;

    expect(await second, VideoAddOutcome.added);
    expect(env.transcoder.calls, hasLength(2));
    await _until(() => env.drained);
    expect(
      env.calls.where((c) => c == 'POST /v1/shops/3/media/uploads'),
      hasLength(1),
    );
  });

  test('압축을 기다리던 둘째를 빼면 네이티브를 건드리지 않고, 첫째는 그대로 압축한다', () async {
    final env = env0();
    final gate = env.transcoder.gate = Completer<void>();
    await env.open();

    final first = addVideo(env, videoSource());
    final second = addVideo(env, videoSource());
    await _until(
      () => env.jobs.length == 2 && env.transcoder.calls.length == 1,
    );

    await env.queue.remove(env.jobs.last.id);
    expect(env.transcoder.cancelled, 0);

    gate.complete();
    expect(await first, VideoAddOutcome.added);
    expect(await second, VideoAddOutcome.cancelled);
    expect(env.transcoder.calls, hasLength(1));
    await _until(() => env.drained);
  });

  test('200MB 를 넘어 서버가 거절한 영상은 멈춘다', () async {
    final env = env0();
    env.apiFailure = (call) => call == 'POST /v1/shops/3/media/uploads'
        ? const FakeResponse(
            statusCode: 422,
            data: {'code': 'MEDIA_TOO_LARGE', 'message': 'x'},
          )
        : null;
    await env.open();

    expect(await addVideo(env, videoSource()), VideoAddOutcome.added);
    await _until(
      () => env.jobs.single.stopped && env.savedJson.single['stopped_code'] != null,
    );

    expect(env.jobs.single.stoppedCode, 'MEDIA_TOO_LARGE');
    expect(env.savedJson.single['kind'], 'video');
    expect(env.retries.delays, isEmpty);
    expect(env.folders, [env.jobs.single.id]);
  });

  test('앱을 다시 켜면 prepared 영상 항목은 mp4·포스터를 이어 올린다', () async {
    final env = env0(
      saved: [_saved('v1', kind: MediaKind.video, durationSeconds: 12)],
    );
    expect(env.savedJson.single['kind'], 'video');
    expect(env.savedJson.single['duration_seconds'], 12);

    await env.open();
    await _until(() => env.drained);

    expect(_ordered(env.calls), [
      ..._videoUploadCalls,
      'POST /v1/shops/3/visits/101/record/media',
    ]);
    expect(issueBody(env), {
      'kind': 'video',
      'content_type': 'video/mp4',
      'byte_size': 3,
      'width': 3000,
      'height': 2000,
      'duration_seconds': 12,
    });
  });

  test('멈춤 칸처럼 kind 가 없던 옛 queue.json 항목은 사진으로 읽는다', () async {
    final env = env0(saved: [_saved('j1')]);
    final old = {...env.savedJson.single}
      ..remove('kind')
      ..remove('duration_seconds');
    File('${root.path}/queue.json').writeAsStringSync(jsonEncode([old]));
    expect(
      UploadJob.fromJson(old, root.path).kind,
      MediaKind.photo,
    );
    expect(UploadJob.fromJson(old, root.path).durationSeconds, isNull);

    await env.open();
    await _until(() => env.drained);

    expect(_ordered(env.calls), [
      ..._uploadCalls,
      'POST /v1/shops/3/visits/101/record/media',
    ]);
    expect(issueBody(env)['kind'], 'photo');
  });
}

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/media_images.dart';
import 'package:chagocnote/core/proxy/photo_album.dart';
import 'package:chagocnote/core/proxy/video_playback.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_video_playback.dart';
import '../../../support/upload_fakes.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

/// 방문 101 의 기록을 쥔 서버. 전체 교체를 받으면 보낸 자리대로 기록을 바꾸고 버전을 올린다.
/// [conflicts]번까지는 교체에 409 를 주며 그사이 대기열이 사진 53·54…(전)을 붙인 것처럼 한다.
/// [failure]가 있으면 교체를 그 응답으로 거절한다.
class _Server {
  _Server({this.status = 'completed', this.conflicts = 0, this.failure}) {
    backend = VisitTestBackend({
      'GET /v1/shops/3/visits/101': (o, b) {
        reads++;
        return FakeResponse(
          statusCode: 200,
          data: visitDetailJson(
            visit: visitJson(status: status),
            record: recordJson(
              weightKg: 4.2,
              careNote: '귀 청소',
              paymentMethod: 'card',
              totalAmount: 30000,
              items: [
                {'menu_id': 1, 'name': '목욕', 'amount': 30000},
              ],
              media: media,
              version: version,
            ),
          ),
        );
      },
      'PUT /v1/shops/3/visits/101/record': (o, body) {
        final sent = bodyOf(body);
        puts.add(sent);
        if (failure != null) return failure!;
        if (conflicts > 0) {
          conflicts--;
          media = [
            ...media,
            recordMediaJson(mediaId: 50 + version, sortOrder: version - 1),
          ];
          version++;
          return const FakeResponse(
            statusCode: 409,
            data: {'code': 'RECORD_VERSION_CONFLICT', 'message': '버전'},
          );
        }
        media = [
          for (final p in sent['media'] as List)
            recordMediaJson(
              mediaId: (p as Map)['media_id'] as int,
              phase: p['phase'] as String,
              sortOrder: p['sort_order'] as int,
            ),
        ];
        version++;
        return FakeResponse(statusCode: 200, data: recordJson(media: media));
      },
    });
  }

  String status;
  int conflicts;

  /// 상세를 읽은 횟수.
  int reads = 0;
  FakeResponse? failure;
  int version = 3;

  /// 전 51·52, 후 61·62.
  List<Map<String, dynamic>> media = [
    recordMediaJson(mediaId: 51, phase: 'before', sortOrder: 0),
    recordMediaJson(mediaId: 52, phase: 'before', sortOrder: 1),
    recordMediaJson(mediaId: 61, phase: 'after', sortOrder: 0),
    recordMediaJson(mediaId: 62, phase: 'after', sortOrder: 1),
  ];
  final puts = <Map<String, dynamic>>[];
  late final VisitTestBackend backend;
}

({
  CustomerTestSetup setup,
  FakeMediaImages images,
  FakePhotoAlbum album,
  FakeVideoPlaybackFactory videos,
})
_build(WidgetTester tester, _Server server) {
  final images = FakeMediaImages();
  final album = FakePhotoAlbum();
  final videos = FakeVideoPlaybackFactory();
  final setup = CustomerTestSetup(
    server.backend.call,
    overrides: [
      todayProvider.overrideWithValue(DateTime(2026, 10, 2)),
      mediaImagesProvider.overrideWithValue(images),
      photoAlbumProvider.overrideWithValue(album),
      videoPlaybackFactoryProvider.overrideWithValue(videos),
    ],
  );
  addTearDown(setup.container.dispose);
  useTallView(tester, height: 900);
  return (setup: setup, images: images, album: album, videos: videos);
}

Future<void> _tap(WidgetTester tester, Finder finder) async {
  await tester.tap(finder);
  await settle(tester);
}

List<(int, String, int)> _placed(Map<String, dynamic> put) => [
  for (final p in put['media'] as List)
    (
      (p as Map)['media_id'] as int,
      p['phase'] as String,
      p['sort_order'] as int,
    ),
];

void main() {
  testWidgets('연 사진부터 원본으로 보이고, 넘기면 머리의 전/후·자리가 따라간다', (tester) async {
    final app = _build(tester, _Server());
    await pushOnHome<Object?>(tester, app.setup, '/visits/101/photos/62');

    expect(find.byKey(ScreenKeys.photoViewer), findsOneWidget);
    // 보이는 순서는 대표 규칙 — 후 61·62, 전 51·52.
    expect(find.text('후 · 2 / 4'), findsOneWidget);
    expect(app.images.originals, contains(contains('original/shops/3/62.jpg')));

    await tester.drag(find.byType(PageView), const Offset(-400, 0));
    await settle(tester);

    expect(find.text('전 · 3 / 4'), findsOneWidget);
  });

  testWidgets('원본 저장은 원본 파일을 받아 앨범에 넣고, 권한이 없으면 켜 달라고 한다', (tester) async {
    final app = _build(tester, _Server());
    await pushOnHome<Object?>(tester, app.setup, '/visits/101/photos/51');

    await _tap(tester, find.bySemanticsLabel(AppStrings.saveOriginal));

    expect(app.images.files.single, contains('original/shops/3/51.jpg'));
    expect(app.album.saved, ['/fake/1.jpg']);
    expect(find.text(AppStrings.savedToAlbum), findsOneWidget);

    // 알림 띠가 아래 버튼 줄을 가리는 3초를 흘린다.
    await tester.pump(const Duration(seconds: 4));
    await settle(tester);
    app.album.denied = true;
    await _tap(tester, find.bySemanticsLabel(AppStrings.saveOriginal));
    expect(find.text(AppStrings.albumDenied), findsOneWidget);
  });

  testWidgets('전/후 바꾸기는 사진 자리만 바꾼 전체 교체 한 번 — 나머지 칸·버전은 읽은 그대로', (
    tester,
  ) async {
    final server = _Server();
    final app = _build(tester, server);
    await pushOnHome<Object?>(tester, app.setup, '/visits/101/photos/51');

    await _tap(tester, find.bySemanticsLabel(AppStrings.toAfter));

    final put = server.puts.single;
    expect(put['version'], 3);
    expect(put['weight_kg'], 4.2);
    expect(put['care_note'], '귀 청소');
    expect(put['payment_method'], 'card');
    expect(put['total_amount'], 30000);
    expect(put['items'], [
      {'menu_id': 1, 'amount': 30000},
    ]);
    expect(_placed(put), [
      (52, 'before', 0),
      (61, 'after', 0),
      (62, 'after', 1),
      (51, 'after', 2),
    ]);
    // 다시 읽으면 51 은 후 사진 셋째 — 보던 사진을 따라간다.
    expect(find.text('후 · 3 / 4'), findsOneWidget);
  });

  testWidgets('대표로는 대표가 될 수 있는 사진에만 있고, 누르면 그 칸의 맨 앞으로 옮긴다', (tester) async {
    final server = _Server();
    final app = _build(tester, server);
    await pushOnHome<Object?>(tester, app.setup, '/visits/101/photos/61');
    expect(
      find.bySemanticsLabel(AppStrings.makeCover),
      findsNothing,
      reason: '이미 대표',
    );

    await tester.drag(find.byType(PageView), const Offset(-400, 0));
    await settle(tester);
    expect(find.text('후 · 2 / 4'), findsOneWidget);

    await _tap(tester, find.bySemanticsLabel(AppStrings.makeCover));

    expect(_placed(server.puts.single), [
      (51, 'before', 0),
      (52, 'before', 1),
      (62, 'after', 0),
      (61, 'after', 1),
    ]);
    expect(find.text('후 · 1 / 4'), findsOneWidget);

    await tester.drag(find.byType(PageView), const Offset(-400, 0));
    await settle(tester);
    await tester.drag(find.byType(PageView), const Offset(-400, 0));
    await settle(tester);
    expect(find.text('전 · 3 / 4'), findsOneWidget);
    expect(
      find.bySemanticsLabel(AppStrings.makeCover),
      findsNothing,
      reason: '후 사진이 있으면 전 사진은 대표가 아니다',
    );
  });

  testWidgets('삭제는 물어본 뒤 그 사진만 뺀 전체 교체이고, 다음 사진을 보인다', (tester) async {
    final server = _Server();
    final app = _build(tester, server);
    await pushOnHome<Object?>(tester, app.setup, '/visits/101/photos/61');

    await _tap(tester, find.bySemanticsLabel(AppStrings.deletePhoto));
    expect(find.text(AppStrings.deletePhotoConfirm), findsOneWidget);
    await _tap(
      tester,
      find.byWidgetPredicate(
        (w) => w is AppButton && w.label == AppStrings.delete,
      ),
    );

    expect(_placed(server.puts.single), [
      (51, 'before', 0),
      (52, 'before', 1),
      (62, 'after', 0),
    ]);
    expect(find.text('후 · 1 / 3'), findsOneWidget);
  });

  testWidgets('삭제가 실패하면 보던 사진에 그대로 남고 오류를 알린다', (tester) async {
    final server = _Server(
      failure: const FakeResponse(
        statusCode: 422,
        data: {'code': 'VALIDATION_ERROR', 'message': '검증'},
      ),
    );
    final app = _build(tester, server);
    await pushOnHome<Object?>(tester, app.setup, '/visits/101/photos/61');

    await _tap(tester, find.bySemanticsLabel(AppStrings.deletePhoto));
    await _tap(
      tester,
      find.byWidgetPredicate(
        (w) => w is AppButton && w.label == AppStrings.delete,
      ),
    );

    expect(server.puts, hasLength(1));
    expect(find.text('후 · 1 / 4'), findsOneWidget);
    expect(find.text('입력한 내용을 확인해 주세요.'), findsOneWidget);
  });

  testWidgets('마지막 사진을 지우면 크게 보기를 닫는다', (tester) async {
    final server = _Server()
      ..media = [recordMediaJson(mediaId: 51, phase: 'before')];
    final app = _build(tester, server);
    final closed = await pushOnHome<Object?>(
      tester,
      app.setup,
      '/visits/101/photos/51',
    );

    await _tap(tester, find.bySemanticsLabel(AppStrings.deletePhoto));
    await _tap(
      tester,
      find.byWidgetPredicate(
        (w) => w is AppButton && w.label == AppStrings.delete,
      ),
    );

    expect(server.puts.single['media'], isEmpty);
    expect(closed.closed, isTrue);
  });

  testWidgets('그사이 대기열이 사진을 붙여 버전이 어긋나면(409) 다시 읽어 같은 바꾸기를 한 번 더 보낸다', (
    tester,
  ) async {
    final server = _Server(conflicts: 1);
    final app = _build(tester, server);
    await pushOnHome<Object?>(tester, app.setup, '/visits/101/photos/51');

    await _tap(tester, find.bySemanticsLabel(AppStrings.toAfter));

    expect(server.puts, hasLength(2));
    expect(server.puts.last['version'], 4);
    expect(_placed(server.puts.last), [
      (52, 'before', 0),
      (53, 'before', 1),
      (61, 'after', 0),
      (62, 'after', 1),
      (51, 'after', 2),
    ], reason: '붙은 사진 53 을 지우지 않는다');
    expect(find.byType(SnackBar), findsNothing);
    expect(find.text('후 · 3 / 5'), findsOneWidget);
  });

  testWidgets('다시 보낸 교체도 409 면 더 보내지 않고 새로 불러왔다고 알린다', (tester) async {
    final server = _Server(conflicts: 2);
    final app = _build(tester, server);
    await pushOnHome<Object?>(tester, app.setup, '/visits/101/photos/51');

    await _tap(tester, find.bySemanticsLabel(AppStrings.toAfter));

    expect(server.puts, hasLength(2));
    expect(find.text('다른 기기에서 기록이 먼저 바뀌었어요. 화면을 새로 불러왔어요.'), findsOneWidget);
  });

  testWidgets('예약됨으로 되돌린 방문은 기록을 바꿀 수 없어 원본 저장만 있다', (tester) async {
    final app = _build(tester, _Server(status: 'reserved'));
    await pushOnHome<Object?>(tester, app.setup, '/visits/101/photos/51');

    expect(find.bySemanticsLabel(AppStrings.saveOriginal), findsOneWidget);
    expect(find.bySemanticsLabel(AppStrings.toAfter), findsNothing);
    expect(find.bySemanticsLabel(AppStrings.deletePhoto), findsNothing);
  });

  testWidgets('영상 페이지에서 [다시 시도]를 누르면 상세를 다시 읽는다', (tester) async {
    final server = _Server()
      ..media = [
        recordMediaJson(
          mediaId: 71,
          phase: 'after',
          kind: 'video',
          durationSeconds: 31,
        ),
      ];
    final app = _build(tester, server);
    app.videos.failWith = ApiException(
      statusCode: 403,
      code: 'MEDIA_URL_EXPIRED',
      message: 'Failed to load video: 403',
    );
    await pushOnHome<Object?>(tester, app.setup, '/visits/101/photos/71');
    expect(server.reads, 1);

    await _tap(tester, find.bySemanticsLabel(AppStrings.playVideo));
    expect(find.text('보기 링크가 만료됐어요. 다시 불러올게요.'), findsOneWidget);

    app.videos.created.single.failWith = null;
    await _tap(tester, find.text(AppStrings.retry));

    expect(server.reads, 2, reason: '새 서명 URL 을 받으러 상세를 다시 읽는다');
    expect(app.videos.created.single.calls, [
      'open http://media.test/b/original/shops/3/71.jpg?sig=a',
      'open http://media.test/b/original/shops/3/71.jpg?sig=a',
      'play',
    ]);
  });

  testWidgets('페이지를 넘기면 앞 영상은 멈춘다', (tester) async {
    final server = _Server()
      ..media = [
        recordMediaJson(
          mediaId: 71,
          phase: 'after',
          kind: 'video',
          durationSeconds: 31,
        ),
        recordMediaJson(mediaId: 61, phase: 'after', sortOrder: 1),
      ];
    final app = _build(tester, server);
    await pushOnHome<Object?>(tester, app.setup, '/visits/101/photos/71');

    await _tap(tester, find.bySemanticsLabel(AppStrings.playVideo));
    final video = app.videos.created.single;
    expect(video.state.playing, isTrue);

    // 영상은 사진 뒤 — 앞(오른쪽으로 밀기)의 사진으로 넘긴다.
    expect(find.text('후 · 2 / 2'), findsOneWidget);
    await tester.drag(find.byType(PageView), const Offset(400, 0));
    await settle(tester);

    expect(find.text('후 · 1 / 2'), findsOneWidget);
    expect(video.calls, contains('pause'));
    expect(video.calls.last, 'dispose', reason: '보이지 않는 페이지는 해제한다');
  });
}

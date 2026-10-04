import 'dart:async';

import 'package:chagocnote/core/proxy/media_images.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_pick_tile.dart';
import 'package:chagocnote/features/visit/state/report_providers.dart';
import 'package:chagocnote/features/visit/state/upload_queue.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/upload_fakes.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

const _reportPath = '/v1/shops/3/visits/101/report';

/// 방문 101(두부, 완료)의 알림장 서버. 미리보기는 지금의 [media]·[careNote]·[link]·[settings]로 답한다.
/// PUT 은 받은 본문을 [puts]에 적고, 뺀 것을 반영해 링크를 만든다 — [putGate]가 있으면 그것이 끝날 때까지
/// 붙들고, [putError]가 있으면 그것으로 답한다.
class _Server {
  _Server({required this.media, this.careNote, bool live = false})
    : link = reportLinkJson(live: live);

  List<Map<String, dynamic>> media;
  String? careNote;
  Map<String, dynamic> link;
  Map<String, dynamic> settings = reportSettingsJson();
  FakeResponse? getError;
  FakeResponse? putError;
  Completer<void>? putGate;
  final puts = <Map<String, dynamic>>[];

  FakeResponse _preview() => FakeResponse(
    statusCode: 200,
    data: visitReportJson(
      media: media,
      careNote: careNote,
      link: link,
      settings: settings,
    ),
  );

  late final backend = VisitTestBackend({
    'GET $_reportPath': (o, b) => getError ?? _preview(),
    'PUT $_reportPath': (o, body) async {
      final sent = bodyOf(body);
      puts.add(sent);
      await putGate?.future;
      if (putError case final error?) return error;
      final hidden = sent['hidden_media_ids'] as List;
      media = [
        for (final m in media) {...m, 'hidden': hidden.contains(m['media_id'])},
      ];
      link = reportLinkJson(live: true);
      return _preview();
    },
    // [고치기]가 여는 기록 화면.
    'GET /v1/shops/3/visits/101': (o, b) => FakeResponse(
      statusCode: 200,
      data: visitDetailJson(
        visit: visitJson(status: 'completed'),
        record: recordJson(careNote: careNote),
      ),
    ),
  });
}

/// 목업 ②의 상태 — 다섯 중 하나(전 사진 2)를 뺐고, 후 사진 3 은 영상이다.
List<Map<String, dynamic>> _five() => [
  reportMediaJson(mediaId: 51),
  reportMediaJson(mediaId: 52),
  reportMediaJson(mediaId: 53, kind: 'video', durationSeconds: 18),
  reportMediaJson(mediaId: 54, phase: 'before'),
  reportMediaJson(mediaId: 55, phase: 'before', hidden: true),
];

const _note = '드라이할 때 조금 긴장했지만 끝까지 잘 참아 줬어요.';

/// 가짜 서버가 만드는 링크의 주소(픽스처의 가짜 주소).
final _url = reportLinkJson(live: true)['url'] as String;

class _App {
  _App(_Server server) {
    setup = CustomerTestSetup(
      server.backend.call,
      overrides: [
        todayProvider.overrideWithValue(DateTime(2026, 10, 2)),
        mediaImagesProvider.overrideWithValue(images),
        uploadQueueProvider.overrideWith(FakeUploadQueue.new),
      ],
    );
  }

  final images = FakeMediaImages();
  late final CustomerTestSetup setup;
}

Future<(_App, Closed<bool>)> _open(
  WidgetTester tester,
  _Server server, {
  bool picking = false,
  double height = 1400,
}) async {
  final app = _App(server);
  addTearDown(app.setup.container.dispose);
  useTallView(tester, height: height);
  final closed = await pushOnHome<bool>(
    tester,
    app.setup,
    '/visits/101/report${picking ? '?pick=1' : ''}',
  );
  return (app, closed);
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

bool _enabled(WidgetTester tester, String label) =>
    tester.widget<AppButton>(_button(label)).onPressed != null;

/// 격자의 타일 — 접근성 이름(전/후·순번, 뺀 것은 끝에 "뺌")으로 찾는다.
Finder _tile(String label) => find.bySemanticsLabel(label);

Future<void> _tap(WidgetTester tester, Finder finder) async {
  await tester.tap(finder);
  await settle(tester);
}

void main() {
  testWidgets('미디어·케어 메모·함께 보이는 항목·기간 안내를 보이고, 머리에 "5개 중 4개"를 센다', (
    tester,
  ) async {
    final server = _Server(media: _five(), careNote: _note);
    final (app, _) = await _open(tester, server);

    expect(find.byKey(ScreenKeys.reportPreview), findsOneWidget);
    expect(find.text('이렇게 보내요'), findsOneWidget);
    expect(find.text('5개 중 4개'), findsOneWidget);

    // 서버가 준 순서 그대로(후 → 전). 순번은 전·후를 따로 센다.
    expect(find.text('사진 · 영상 — 빼려면 누르세요'), findsOneWidget);
    for (final label in ['후 사진 1', '후 사진 2', '후 사진 3', '전 사진 1', '전 사진 2 뺌']) {
      expect(_tile(label), findsOneWidget, reason: label);
    }
    expect(find.text('뺌'), findsOneWidget);
    expect(find.byIcon(Icons.check), findsNWidgets(4));
    expect(find.text('0:18'), findsOneWidget);
    expect(app.images.urls, contains(thumbUrl(53)));

    expect(find.text(_note), findsOneWidget);
    expect(find.text('고치기'), findsOneWidget);

    expect(find.text('함께 보이는 항목'), findsOneWidget);
    expect(find.text('설정에서 바꿔요'), findsOneWidget);
    for (final label in ['메뉴 이름', '매장 정보', '금액 안 보임', '몸무게 안 보임']) {
      expect(find.bySemanticsLabel(label), findsOneWidget, reason: label);
    }

    // 오늘(10월 2일)에서 30일 뒤.
    expect(
      find.text('11월 1일까지 열려요. 보낸 뒤에 기록을 고치면 알림장에도 바로 반영돼요.'),
      findsOneWidget,
    );
    expect(_enabled(tester, '보내기'), isTrue);
    expect(_button(AppStrings.save), findsNothing);
  });

  testWidgets('타일을 누르면 빠지고 다시 누르면 되살아난다 — 수와 [보내기] 활성이 따라 바뀐다', (
    tester,
  ) async {
    final server = _Server(media: [reportMediaJson(mediaId: 51)]);
    await _open(tester, server);
    expect(find.text('1개 중 1개'), findsOneWidget);
    expect(find.text('케어 메모가 없어요.'), findsOneWidget);
    expect(_enabled(tester, '보내기'), isTrue);

    await _tap(tester, _tile('후 사진 1'));

    expect(_tile('후 사진 1 뺌'), findsOneWidget);
    expect(find.text('1개 중 0개'), findsOneWidget);
    expect(_enabled(tester, '보내기'), isFalse);

    await _tap(tester, _tile('후 사진 1 뺌'));

    expect(_tile('후 사진 1'), findsOneWidget);
    expect(find.text('1개 중 1개'), findsOneWidget);
    expect(_enabled(tester, '보내기'), isTrue);
    expect(server.puts, isEmpty);
  });

  testWidgets(
    '[보내기]는 직전에 다시 읽은 서버 상태 위에 누른 것만 덮어 보내고, 받은 링크를 공유 시트에 넘긴 뒤 닫힌다',
    (tester) async {
      final server = _Server(
        media: [
          reportMediaJson(mediaId: 1),
          reportMediaJson(mediaId: 2),
          reportMediaJson(mediaId: 3, hidden: true),
        ],
        careNote: _note,
      );
      final (app, closed) = await _open(tester, server);
      expect(find.text('3개 중 2개'), findsOneWidget);
      // 화면을 연 뒤 다른 기기에서 2 를 빼고 3 을 되살렸고, 대기열이 새 사진 4 를 붙였다.
      server.media = [
        reportMediaJson(mediaId: 1),
        reportMediaJson(mediaId: 2, hidden: true),
        reportMediaJson(mediaId: 3),
        reportMediaJson(mediaId: 4),
      ];

      await _tap(tester, _tile('후 사진 1'));
      await _tap(tester, _button('보내기'));

      expect(server.puts.single, {
        'hidden_media_ids': [1, 2],
      });
      expect(app.setup.shareSheet.shared, [_url]);
      // 아이패드의 말풍선이 붙을 자리 — 버튼의 화면 사각형.
      final origin = app.setup.shareSheet.origins.single;
      expect(origin.width, greaterThan(0));
      expect(origin.height, 44);
      expect(closed.closed, isTrue);
      expect(closed.value, isTrue);
    },
  );

  testWidgets('눌렀다가 되돌린 타일은 누르지 않은 것이다 — 그 사이 다른 기기에서 뺐으면 뺀 채로 보낸다', (
    tester,
  ) async {
    final server = _Server(
      media: [reportMediaJson(mediaId: 1), reportMediaJson(mediaId: 2)],
    );
    await _open(tester, server);

    await _tap(tester, _tile('후 사진 1'));
    await _tap(tester, _tile('후 사진 1 뺌'));
    server.media = [
      reportMediaJson(mediaId: 1, hidden: true),
      reportMediaJson(mediaId: 2),
    ];
    await _tap(tester, _button('보내기'));

    expect(server.puts.single, {
      'hidden_media_ids': [1],
    });
  });

  testWidgets('보여 줄 것이 없으면 [보내기]가 눌리지 않고 이유를 보인다', (tester) async {
    final server = _Server(media: [reportMediaJson(mediaId: 51, hidden: true)]);
    final (app, closed) = await _open(tester, server);
    const reason = '보여 줄 사진·영상이나 케어 메모가 있어야 보낼 수 있어요.';

    expect(find.text(reason), findsOneWidget);
    expect(_enabled(tester, '보내기'), isFalse);
    await _tap(tester, _button('보내기'));
    expect(server.puts, isEmpty);
    expect(closed.closed, isFalse);

    // 메모가 있으면 전부 빼도 보낼 수 있다.
    server.careNote = _note;
    app.setup.container.invalidate(visitReportProvider);
    await settle(tester);

    expect(find.text(reason), findsNothing);
    expect(_enabled(tester, '보내기'), isTrue);
    await _tap(tester, _button('보내기'));
    expect(server.puts.single, {
      'hidden_media_ids': [51],
    });
    expect(closed.closed, isTrue);
  });

  testWidgets('사진·영상이 없으면 격자 대신 안내 한 줄이고, 머리에 수를 세지 않는다', (tester) async {
    await _open(tester, _Server(media: [], careNote: _note));

    expect(find.text('붙인 사진·영상이 없어요.'), findsOneWidget);
    expect(find.textContaining('개 중'), findsNothing);
    expect(_enabled(tester, '보내기'), isTrue);
  });

  testWidgets('[보내기]를 빠르게 두 번 눌러도 한 번만 보내고 공유 시트도 한 번이다', (tester) async {
    final server = _Server(media: [reportMediaJson(mediaId: 51)])
      ..putGate = Completer<void>();
    final (app, closed) = await _open(tester, server);

    // 화면이 다시 그려지기 전에 한 번 더 누른다.
    await tester.tap(_button('보내기'));
    await tester.tap(_button('보내기'));
    await tester.pump(const Duration(milliseconds: 1));
    await tester.pump(const Duration(milliseconds: 1));
    expect(server.puts, hasLength(1));
    expect(tester.widget<AppButton>(_button('보내기')).busy, isTrue);

    // 보내는 동안에는 버튼도 타일도 [고치기]도 눌리지 않고, 뒤로 가기로도 닫히지 않는다.
    await tester.tap(_button('보내기'));
    await tester.tap(_tile('후 사진 1'));
    await tester.tap(find.text('고치기'));
    await tester.binding.handlePopRoute();
    await tester.tap(find.bySemanticsLabel(AppStrings.close));
    await tester.pump(const Duration(milliseconds: 1));
    expect(find.text('1개 중 1개'), findsOneWidget);
    expect(find.byKey(ScreenKeys.visitRecord), findsNothing);
    expect(closed.closed, isFalse);

    server.putGate!.complete();
    await settle(tester);

    expect(server.puts, hasLength(1));
    expect(app.setup.shareSheet.shared, [_url]);
    expect(closed.closed, isTrue);
  });

  testWidgets('보낼 사진 고르기(pick)는 [저장]이고 공유 시트를 열지 않는다 — 전부 빼도 저장할 수 있다', (
    tester,
  ) async {
    final server = _Server(media: [reportMediaJson(mediaId: 51)], live: true);
    final (app, closed) = await _open(tester, server, picking: true);
    expect(_button('보내기'), findsNothing);

    await _tap(tester, _tile('후 사진 1'));

    expect(find.text('1개 중 0개'), findsOneWidget);
    expect(find.textContaining('있어야 보낼 수 있어요'), findsNothing);
    expect(_enabled(tester, AppStrings.save), isTrue);
    await _tap(tester, _button(AppStrings.save));

    expect(server.puts.single, {
      'hidden_media_ids': [51],
    });
    expect(app.setup.shareSheet.shared, isEmpty);
    expect(closed.closed, isTrue);
    expect(closed.value, isTrue);
  });

  testWidgets('보낼 사진 고르기에서 [저장]을 눌렀는데 그 사이 링크가 닫혔으면 저장하지 않고 닫히며 "이미 닫힌 알림장이에요."를 알린다', (
    tester,
  ) async {
    final server = _Server(
      media: [reportMediaJson(mediaId: 51), reportMediaJson(mediaId: 52)],
      live: true,
    );
    final (app, closed) = await _open(tester, server, picking: true);
    // 화면을 열어 둔 사이 다른 기기에서 링크를 끊었다.
    server.link = reportLinkJson();
    await _tap(tester, _tile('후 사진 1'));

    await _tap(tester, _button(AppStrings.save));

    expect(server.puts, isEmpty);
    expect(app.setup.shareSheet.shared, isEmpty);
    expect(closed.closed, isTrue);
    expect(closed.value, isNot(isTrue));
    expect(find.text('이미 닫힌 알림장이에요.'), findsOneWidget);
  });

  testWidgets('서버가 거절하면(422 REPORT_EMPTY) 문구를 보이고 닫지 않는다 — 누른 것은 그대로다', (
    tester,
  ) async {
    final server =
        _Server(
            media: [reportMediaJson(mediaId: 51), reportMediaJson(mediaId: 52)],
          )
          ..putError = const FakeResponse(
            statusCode: 422,
            data: {'code': 'REPORT_EMPTY', 'message': 'x'},
          );
    final (app, closed) = await _open(tester, server);
    await _tap(tester, _tile('후 사진 1'));

    await _tap(tester, _button('보내기'));

    expect(find.text('보여 줄 사진·영상이나 케어 메모가 있어야 보낼 수 있어요.'), findsOneWidget);
    expect(closed.closed, isFalse);
    expect(app.setup.shareSheet.shared, isEmpty);
    // 실패하면 미리보기를 다시 읽는다 — 서버는 51 을 아직 보이는 것으로 주지만 화면은 누른 대로다.
    expect(app.setup.calls.where((c) => c == 'GET $_reportPath'), hasLength(3));
    expect(_tile('후 사진 1 뺌'), findsOneWidget);
    expect(find.text('2개 중 1개'), findsOneWidget);
    expect(_enabled(tester, '보내기'), isTrue);
  });

  // 채널 오류(PlatformException)와 네이티브 쪽이 없는 경우(MissingPluginException) 둘 다.
  for (final error in [PlatformException(code: 'NO_VIEW'), MissingPluginException()]) {
    testWidgets('공유 시트가 실패해도(${error.runtimeType}) 닫히고 안내를 보인다', (tester) async {
      final server = _Server(media: [reportMediaJson(mediaId: 51)]);
      final (app, closed) = await _open(tester, server);
      app.setup.shareSheet.error = error;

      await _tap(tester, _button('보내기'));

      // 링크는 이미 만들어졌다 — 방문 상세의 [다시 공유]로 다시 낼 수 있다.
      expect(server.puts, hasLength(1));
      expect(closed.closed, isTrue);
      expect(closed.value, isTrue);
      expect(
        find.text('공유 화면을 열지 못했어요. 방문 화면의 [다시 공유]로 다시 보낼 수 있어요.'),
        findsOneWidget,
      );
    });
  }

  testWidgets('[고치기]는 기록 화면을 열고, 돌아오면 케어 메모를 다시 읽되 누른 것은 그대로다', (
    tester,
  ) async {
    final server = _Server(
      media: [reportMediaJson(mediaId: 51), reportMediaJson(mediaId: 52)],
      careNote: '처음 메모',
    );
    await _open(tester, server);
    await _tap(tester, _tile('후 사진 1'));

    await _tap(tester, find.text('고치기'));
    expect(find.byKey(ScreenKeys.visitRecord), findsOneWidget);
    // 기록 화면에서 메모를 고쳐 저장했다.
    server.careNote = '고친 메모';
    await tester.binding.handlePopRoute();
    await settle(tester);

    expect(find.byKey(ScreenKeys.visitRecord), findsNothing);
    expect(find.text('고친 메모'), findsOneWidget);
    expect(find.text('처음 메모'), findsNothing);
    expect(_tile('후 사진 1 뺌'), findsOneWidget);
    expect(find.text('2개 중 1개'), findsOneWidget);
  });

  testWidgets('기록이 없는 방문(409 VISIT_NO_RECORD_YET)은 처음 실패 화면이다', (tester) async {
    final server = _Server(media: [])
      ..getError = const FakeResponse(
        statusCode: 409,
        data: {'code': 'VISIT_NO_RECORD_YET', 'message': 'x'},
      );
    await _open(tester, server);

    expect(find.text('미용을 시작한 방문에만 기록을 쓸 수 있어요.'), findsOneWidget);
    expect(_button('보내기'), findsNothing);
    expect(find.text('이렇게 보내요'), findsOneWidget);
  });

  testWidgets('함께 보이는 항목은 설정을 따른다 — 끈 것은 "안 보임"', (tester) async {
    final server = _Server(media: [reportMediaJson(mediaId: 51)])
      ..settings = reportSettingsJson(showMenus: false, showWeight: true);
    await _open(tester, server);

    for (final label in ['메뉴 이름 안 보임', '매장 정보', '금액 안 보임', '몸무게']) {
      expect(find.bySemanticsLabel(label), findsOneWidget, reason: label);
    }
  });

  testWidgets('무기한이면 "계속 열려 있어요", 7일이면 오늘에서 7일 뒤 날짜, 살아 있는 링크는 그 링크의 기한', (
    tester,
  ) async {
    final server = _Server(media: [reportMediaJson(mediaId: 51)])
      ..settings = reportSettingsJson(linkDays: null);
    final (app, _) = await _open(tester, server);
    Future<void> reload() async {
      app.setup.container.invalidate(visitReportProvider);
      await settle(tester);
    }

    expect(find.textContaining('계속 열려 있어요.'), findsOneWidget);

    server.settings = reportSettingsJson(linkDays: 7);
    await reload();
    expect(find.textContaining('10월 9일까지 열려요.'), findsOneWidget);

    // 이미 보낸 링크는 설정이 아니라 그 링크의 기한을 따른다.
    server.link = reportLinkJson(
      live: true,
      expiresAt: '2026-10-20T15:30:00+09:00',
    );
    await reload();
    expect(find.textContaining('10월 20일까지 열려요.'), findsOneWidget);

    server.link = reportLinkJson(live: true, expiresAt: null);
    await reload();
    expect(find.textContaining('계속 열려 있어요.'), findsOneWidget);
  });

  /// 사진 30개와 케어 메모 — 폰 화면(390×844)에 다 들어가지 않는다.
  _Server manyPhotos() => _Server(
    media: [for (var i = 1; i <= 30; i++) reportMediaJson(mediaId: i)],
    careNote: _note,
  );

  testWidgets('사진이 많아도 [보내기]는 스크롤 없이 화면 안에 있다 — 격자의 끝은 화면 밖이다', (tester) async {
    final server = manyPhotos();
    await _open(tester, server, height: 844);

    final button = tester.getRect(_button('보내기'));
    expect(button.top, greaterThanOrEqualTo(0));
    expect(button.bottom, lessThanOrEqualTo(844));
    expect(
      tester.getRect(find.byType(AppPickTile).last).top,
      greaterThan(844),
    );

    // 스크롤하지 않고 바로 눌러 보낸다.
    await tester.tap(_button('보내기'));
    await settle(tester);
    expect(server.puts, hasLength(1));
  });

  testWidgets('내용을 끝까지 스크롤해도 [보내기]의 자리는 그대로다', (tester) async {
    await _open(tester, manyPhotos(), height: 844);
    final before = tester.getRect(_button('보내기'));

    await tester.drag(find.byType(ListView), const Offset(0, -5000));
    await tester.pumpAndSettle();

    expect(
      tester.getRect(find.byType(AppPickTile).last).bottom,
      lessThan(before.top),
    );
    expect(tester.getRect(_button('보내기')), before);
  });

  testWidgets('고르기 모드의 [저장]도 같은 자리에 고정이다', (tester) async {
    await _open(tester, manyPhotos(), picking: true, height: 844);
    final before = tester.getRect(_button(AppStrings.save));

    expect(before.bottom, lessThanOrEqualTo(844));
    expect(
      tester.getRect(find.byType(AppPickTile).last).top,
      greaterThan(844),
    );
    await tester.drag(find.byType(ListView), const Offset(0, -5000));
    await tester.pumpAndSettle();
    expect(tester.getRect(_button(AppStrings.save)), before);
  });

  testWidgets('미리보기 골든', (tester) async {
    final server = _Server(media: _five(), careNote: _note);
    final (app, _) = await _open(tester, server);
    await tester.runAsync(
      () => precacheImage(
        app.images.image,
        tester.element(find.byKey(ScreenKeys.reportPreview)),
      ),
    );
    tester.view.physicalSize = const Size(390, 844);
    await tester.pumpAndSettle();

    await expectLater(
      find.byKey(ScreenKeys.reportPreview),
      matchesGoldenFile('goldens/report_preview.png'),
    );
  });
}

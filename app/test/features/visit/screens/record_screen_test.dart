import 'dart:async';

import 'package:chagocnote/core/proxy/media_images.dart';
import 'package:chagocnote/core/proxy/media_picker.dart';
import 'package:chagocnote/core/proxy/speech_recognizer.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/design/widgets/app_back_button.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_mic_button.dart';
import 'package:chagocnote/design/widgets/dictation_text_editing_controller.dart';
import 'package:chagocnote/design/widgets/pressable.dart';
import 'package:chagocnote/features/visit/api/record_models.dart';
import 'package:chagocnote/features/visit/state/upload_job.dart';
import 'package:chagocnote/features/visit/state/upload_queue.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/upload_fakes.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

/// 두부(101, 미용 중, 예약 메뉴 목욕)의 기록 화면 서버. [withBori]면 보리(102)가 같은 묶음·같은 상태다.
/// 기록 PUT 은 [putResponses]를 앞에서부터 쓰고, 다 쓰면 받은 대로 저장했다고 답한다.
class _Server {
  _Server({this.record, this.withBori = false, this.ownerOnly = false}) {
    backend = VisitTestBackend({
      'GET /v1/shops/3/visits/101': (o, b) {
        detailReads++;
        return FakeResponse(
          statusCode: 200,
          data: visitDetailJson(
            visit: visitJson(status: status, ownerOnly: ownerOnly),
            group: [
              if (withBori)
                visitJson(
                  visitId: 102,
                  status: status,
                  pet: visitPetJson(petId: 12, name: '보리'),
                ),
            ],
            record: record,
          ),
        );
      },
      'GET /v1/shops/3/menus': (o, b) => FakeResponse(
        statusCode: 200,
        data: {
          'items': [
            menuJson(menuId: 1, name: '목욕', sortOrder: 1, price: 30000),
            menuJson(menuId: 2, name: '위생', sortOrder: 2),
            menuJson(menuId: 4, name: '전체 미용', sortOrder: 3, price: 55000),
          ],
        },
      ),
      'PUT /v1/shops/3/visits/101/record': (o, body) {
        final sent = bodyOf(body);
        puts.add(sent);
        if (putResponses.isNotEmpty) return putResponses.removeAt(0);
        return FakeResponse(statusCode: 200, data: recordJson(version: 9));
      },
      'POST /v1/shops/3/visits/transitions': (o, body) {
        transitions.add(bodyOf(body));
        status = 'completed';
        return FakeResponse(
          statusCode: 200,
          data: {
            'visits': [visitJson(status: 'completed')],
          },
        );
      },
    });
  }

  Map<String, dynamic>? record;
  String status = 'in_progress';
  final bool withBori;
  final bool ownerOnly;
  int detailReads = 0;
  final puts = <Map<String, dynamic>>[];
  final putResponses = <FakeResponse>[];
  final transitions = <Map<String, dynamic>>[];
  late final VisitTestBackend backend;
}

class _App {
  _App(this.server, {List<UploadJob> uploads = const []})
    : queue = FakeUploadQueue(uploads) {
    setup = CustomerTestSetup(
      server.backend.call,
      overrides: [
        todayProvider.overrideWithValue(DateTime(2026, 10, 2)),
        uploadQueueProvider.overrideWith(() => queue),
        mediaImagesProvider.overrideWithValue(images),
        mediaPickerProvider.overrideWithValue(picker),
      ],
    );
  }

  final _Server server;
  final FakeUploadQueue queue;
  final images = FakeMediaImages();
  final picker = FakeMediaPicker();
  late final CustomerTestSetup setup;
}

Future<(_App, Closed<bool>)> _open(
  WidgetTester tester,
  _Server server, {
  bool completing = false,
  List<UploadJob> uploads = const [],
}) async {
  final app = _App(server, uploads: uploads);
  addTearDown(app.setup.container.dispose);
  useTallView(tester, height: 1800);
  final closed = await pushOnHome<bool>(
    tester,
    app.setup,
    '/visits/101/record${completing ? '?complete=1' : ''}',
  );
  return (app, closed);
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

Finder _field(String key) => find.byKey(ValueKey(key));

String _text(WidgetTester tester, String key) =>
    tester.widget<TextField>(_field(key)).controller!.text;

Future<void> _tap(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.tap(finder);
  await settle(tester);
}

Finder _mic(String label) => find.byWidgetPredicate(
  (w) => w is AppMicButton && w.semanticLabel == '$label ${AppStrings.micLabel}',
);

bool _listening(WidgetTester tester, String label) =>
    tester.widget<AppMicButton>(_mic(label)).listening;

DictationTextEditingController _controller(WidgetTester tester, String key) =>
    tester.widget<TextField>(_field(key)).controller!
        as DictationTextEditingController;

/// 마이크를 누른다. 듣는 동안은 점이 깜빡여 settle 할 수 없다 — 몇 번만 그린다.
Future<void> _tapMic(WidgetTester tester, String label) async {
  await tester.ensureVisible(_mic(label));
  await tester.tap(_mic(label));
  await tester.pump();
  await tester.pump();
}

Map<String, dynamic> _savedRecord() => recordJson(
  weightKg: 4.0,
  careNote: '발바닥 각질',
  internalNote: '예민함',
  paymentMethod: 'transfer',
  totalAmount: 50000,
  items: [
    {'menu_id': 4, 'name': '전체 미용', 'amount': 55000},
  ],
  media: [
    recordMediaJson(mediaId: 51, phase: 'before', sortOrder: 0),
    recordMediaJson(mediaId: 52, phase: 'before', sortOrder: 1),
    recordMediaJson(mediaId: 53, phase: 'after', sortOrder: 0),
  ],
  version: 3,
);

UploadJob _job(
  String id, {
  bool running = false,
  int failures = 0,
  String? stoppedCode,
  MediaKind kind = MediaKind.photo,
  UploadStage stage = UploadStage.prepared,
}) => UploadJob(
      id: id,
      userId: 1,
      shopId: 3,
      visitId: 101,
      phase: MediaPhase.after,
      stage: stage,
      progress: 0.5,
      running: running,
      failures: failures,
      stoppedCode: stoppedCode,
      kind: kind,
    );

/// 붙은 영상 [n]편이 든 기록.
Map<String, dynamic> _videoRecord(int n, {int? durationSeconds}) => recordJson(
  media: [
    for (var i = 0; i < n; i++)
      recordMediaJson(
        mediaId: 200 + i,
        sortOrder: i,
        kind: 'video',
        durationSeconds: durationSeconds,
      ),
  ],
  version: 3,
);

void main() {
  testWidgets(
    '완료 흐름: 비어 있으면 몸무게·예약 메뉴와 정가·총액을 채우고, 완료하기는 기록을 저장한 뒤 같은 묶음을 완료하고 닫힌다',
    (tester) async {
      final server = _Server(withBori: true);
      final (_, closed) = await _open(tester, server, completing: true);

      expect(find.byKey(ScreenKeys.visitRecord), findsOneWidget);
      expect(find.text(AppStrings.completeRecordTitle), findsOneWidget);
      expect(find.text('4.2'), findsOneWidget);
      expect(_text(tester, 'amount-1'), '30000');
      expect(_text(tester, 'total'), '30000');

      await _tap(tester, find.bySemanticsLabel(AppStrings.paymentCard));
      await tester.enterText(_field('careNote'), '  발바닥 각질  ');
      await _tap(tester, _button(AppStrings.completeWithRecord));

      expect(server.puts.single, {
        'weight_kg': 4.2,
        'care_note': '발바닥 각질',
        'internal_note': null,
        'payment_method': 'card',
        'total_amount': 30000,
        'items': [
          {'menu_id': 1, 'amount': 30000},
        ],
        'media': <Object>[],
      });
      expect(server.transitions.single, {
        'visit_ids': [101, 102],
        'action': 'complete',
      });
      expect(closed.closed, isTrue);
      expect(closed.value, isTrue);
    },
  );

  testWidgets('금액을 바꾸면 총액이 항목 합을 따라가고, 총액을 직접 고친 뒤에는 따라가지 않는다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, find.bySemanticsLabel('위생'));
    expect(_text(tester, 'amount-2'), '');
    expect(_text(tester, 'total'), '30000');
    await tester.enterText(_field('amount-2'), '10000');
    await settle(tester);
    expect(_text(tester, 'total'), '40000');

    await tester.enterText(_field('total'), '35000');
    await tester.enterText(_field('amount-1'), '32000');
    await settle(tester);
    expect(_text(tester, 'total'), '35000');

    await _tap(tester, find.bySemanticsLabel('목욕'));
    await _tap(tester, _button(AppStrings.save));

    expect(server.puts.single['items'], [
      {'menu_id': 2, 'amount': 10000},
    ]);
    expect(server.puts.single['total_amount'], 35000);
    expect(server.transitions, isEmpty);
  });

  testWidgets('정가 없는 메뉴만 고르면 총액은 비어 있고 금액은 0원으로 보낸다', (tester) async {
    final server = _Server()
      ..record = recordJson(media: [recordMediaJson()], version: 2);
    await _open(tester, server);
    await _tap(tester, find.bySemanticsLabel('목욕'));
    await _tap(tester, find.bySemanticsLabel('위생'));

    expect(_text(tester, 'total'), '');
    await _tap(tester, _button(AppStrings.save));

    expect(server.puts.single['items'], [
      {'menu_id': 2, 'amount': 0},
    ]);
    expect(server.puts.single['total_amount'], isNull);
    expect(server.puts.single['version'], 2);
  });

  testWidgets('적어 둔 기록은 그대로 보이고, 사진을 누르면 전/후가 바뀌고 빼면 보내지 않는다 — 읽은 버전으로 저장한다', (
    tester,
  ) async {
    final server = _Server(record: _savedRecord());
    final (app, closed) = await _open(tester, server);

    expect(find.text('4'), findsOneWidget);
    expect(_text(tester, 'amount-4'), '55000');
    expect(_text(tester, 'total'), '50000');
    expect(_text(tester, 'careNote'), '발바닥 각질');
    expect(_text(tester, 'internalNote'), '예민함');
    expect(app.images.urls, contains(contains('thumb/shops/3/53.jpg')));

    await _tap(tester, find.bySemanticsLabel('전 사진 2'));
    await _tap(
      tester,
      find.bySemanticsLabel('${AppStrings.removePhoto} 후 사진 2'),
    );
    await tester.enterText(_field('amount-4'), '60000');
    await _tap(tester, _button(AppStrings.save));

    final sent = server.puts.single;
    expect(sent['version'], 3);
    expect(sent['weight_kg'], 4.0);
    expect(sent['payment_method'], 'transfer');
    expect(sent['total_amount'], 50000);
    expect(sent['media'], [
      {'media_id': 51, 'phase': 'before', 'sort_order': 0},
      {'media_id': 52, 'phase': 'after', 'sort_order': 0},
    ]);
    expect(closed.value, isFalse);
  });

  testWidgets(
    '그 사이 붙은 사진으로 버전이 어긋나면(409) 다시 읽어 새 사진만 더하고 한 번 더 보낸다 — 고친 칸은 그대로',
    (tester) async {
      final server = _Server(
        record: recordJson(
          careNote: '처음 메모',
          media: [recordMediaJson(mediaId: 51)],
          version: 3,
        ),
      );
      server.putResponses.add(
        const FakeResponse(
          statusCode: 409,
          data: {'code': 'RECORD_VERSION_CONFLICT', 'message': 'x'},
        ),
      );
      final (_, closed) = await _open(tester, server);
      await tester.enterText(_field('careNote'), '고친 메모');
      // 대기열이 60번을 덧붙여 서버 기록은 버전 4가 됐다.
      server.record = recordJson(
        careNote: '처음 메모',
        media: [
          recordMediaJson(mediaId: 51),
          recordMediaJson(mediaId: 60, phase: 'after'),
        ],
        version: 4,
      );

      await _tap(tester, _button(AppStrings.save));

      expect(server.puts, hasLength(2));
      expect(server.puts.last['version'], 4);
      expect(server.puts.last['care_note'], '고친 메모');
      expect(server.puts.last['media'], [
        {'media_id': 51, 'phase': 'before', 'sort_order': 0},
        {'media_id': 60, 'phase': 'after', 'sort_order': 0},
      ]);
      expect(closed.closed, isTrue);
    },
  );

  testWidgets('두 번째도 어긋나면 문구를 보이고 화면에 남는다', (tester) async {
    final server = _Server(record: recordJson(careNote: '메모', version: 3));
    const conflict = FakeResponse(
      statusCode: 409,
      data: {'code': 'RECORD_VERSION_CONFLICT', 'message': 'x'},
    );
    server.putResponses.addAll([conflict, conflict]);
    final (_, closed) = await _open(tester, server);

    await _tap(tester, _button(AppStrings.save));

    expect(server.puts, hasLength(2));
    expect(find.textContaining('기록이 먼저 바뀌었어요'), findsOneWidget);
    expect(closed.closed, isFalse);
  });

  testWidgets('어긋나 다시 읽는데 그것마저 실패해도 쓰던 폼은 남고 문구만 보인다', (tester) async {
    final server = _Server(record: recordJson(careNote: '메모', version: 3));
    server.putResponses.add(
      const FakeResponse(
        statusCode: 409,
        data: {'code': 'RECORD_VERSION_CONFLICT', 'message': 'x'},
      ),
    );
    final ok = server.backend.routes['GET /v1/shops/3/visits/101']!;
    server.backend.routes['GET /v1/shops/3/visits/101'] = (o, b) =>
        server.detailReads > 0
        ? const FakeResponse(statusCode: 503, data: 'x')
        : ok(o, b);
    final (_, closed) = await _open(tester, server);
    await tester.enterText(find.widgetWithText(TextField, '메모'), '고쳐 쓴 메모');

    await _tap(tester, _button(AppStrings.save));

    expect(find.text('고쳐 쓴 메모'), findsOneWidget, reason: '쓰던 폼이 오류 화면으로 바뀌지 않는다');
    expect(find.textContaining('서버에 잠시 문제가 있어요'), findsOneWidget);
    expect(closed.closed, isFalse);
  });

  testWidgets('나중에 적고 완료는 기록을 보내지 않고 완료만 한다', (tester) async {
    final server = _Server();
    final (_, closed) = await _open(tester, server, completing: true);

    await _tap(tester, _button(AppStrings.completeWithoutRecord));

    expect(server.puts, isEmpty);
    expect(server.transitions.single['action'], 'complete');
    expect(closed.value, isTrue);
  });

  testWidgets('보호자만의 방문은 몸무게 칸이 없다', (tester) async {
    await _open(tester, _Server(ownerOnly: true));

    expect(find.text(AppStrings.weightLabel), findsNothing);
  });

  testWidgets('몸무게가 틀리면 보내지 않고 칸 아래에 알린다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await tester.enterText(find.widgetWithText(TextField, '4.2'), '0');
    await _tap(tester, _button(AppStrings.save));

    expect(find.text(AppStrings.weightInvalid), findsOneWidget);
    expect(server.puts, isEmpty);
  });

  testWidgets('예약됨에서 바로 완료할 때 몸무게가 틀리면 완료 전이도 보내지 않는다', (tester) async {
    final server = _Server()..status = 'reserved';
    final (_, closed) = await _open(tester, server, completing: true);

    await tester.enterText(find.widgetWithText(TextField, '4.2'), '0');
    await _tap(tester, _button(AppStrings.completeWithRecord));

    expect(find.text(AppStrings.weightInvalid), findsOneWidget);
    expect(server.transitions, isEmpty);
    expect(server.puts, isEmpty);
    expect(closed.closed, isFalse);
  });

  testWidgets('저장 중에는 시스템 뒤로 가기도 뒤로 버튼도 닫지 않는다 — 저장이 끝나면 완료까지 하고 닫힌다', (
    tester,
  ) async {
    final server = _Server();
    final put = Completer<FakeResponse>();
    server.backend.routes['PUT /v1/shops/3/visits/101/record'] = (o, b) =>
        put.future;
    final (_, closed) = await _open(tester, server, completing: true);

    await tester.ensureVisible(_button(AppStrings.completeWithRecord));
    await tester.tap(_button(AppStrings.completeWithRecord));
    await tester.pump(const Duration(milliseconds: 1));
    await tester.binding.handlePopRoute();
    await tester.pump(const Duration(milliseconds: 1));
    expect(closed.closed, isFalse);
    await tester.tap(find.byType(AppBackButton), warnIfMissed: false);
    await tester.pump(const Duration(milliseconds: 1));
    expect(closed.closed, isFalse);
    expect(find.byKey(ScreenKeys.visitRecord), findsOneWidget);

    put.complete(FakeResponse(statusCode: 200, data: recordJson(version: 9)));
    await settle(tester);

    expect(server.transitions.single['action'], 'complete');
    expect(closed.closed, isTrue);
    expect(closed.value, isTrue);
  });

  testWidgets('올리는 중인 사진은 진행 링, 실패해 기다리는 사진은 "대기 중"이고 빼기를 누르면 대기열에서 뺀다', (
    tester,
  ) async {
    final server = _Server();
    final (app, _) = await _open(
      tester,
      server,
      uploads: [_job('j1', running: true), _job('j2', failures: 2)],
    );

    expect(find.bySemanticsLabel(AppStrings.uploading), findsOneWidget);
    expect(find.text(AppStrings.uploadWaiting), findsOneWidget);
    await _tap(tester, find.bySemanticsLabel(AppStrings.removeUpload).last);

    expect(app.queue.removed, ['j2']);
  });

  testWidgets('멈춘 사진은 느낌표이고, 누르면 이유와 [다시 시도]·[올리기 취소]를 보인다', (tester) async {
    final server = _Server();
    final (app, _) = await _open(
      tester,
      server,
      uploads: [
        _job('j1', stoppedCode: 'MEDIA_LIMIT_EXCEEDED'),
        _job('j2', stoppedCode: 'VISIT_NOT_FOUND'),
      ],
    );
    expect(find.byIcon(Icons.priority_high), findsNWidgets(2));
    expect(find.text(AppStrings.uploadWaiting), findsNothing);

    await _tap(tester, find.bySemanticsLabel(AppStrings.uploadStopped).first);
    expect(find.text('방문 하나에 사진은 30장, 영상은 3편까지 붙일 수 있어요.'), findsOneWidget);
    await _tap(tester, find.text(AppStrings.retry));
    expect(app.queue.retried, ['j1']);

    await _tap(tester, find.bySemanticsLabel(AppStrings.uploadStopped).last);
    expect(find.text('방문을 찾을 수 없어요. 이미 지워졌을 수 있어요.'), findsOneWidget);
    await _tap(tester, find.text(AppStrings.removeUpload).last);
    expect(app.queue.removed, ['j2']);
    expect(app.queue.retried, ['j1']);
  });

  testWidgets(
    '사진 추가는 전/후를 고르고 앨범에서 고른 사진을 대기열에 넣는다 — 한도는 30장에서 서버에 붙은 사진(폼에서 뺀 것 포함)과 대기열을 뺀 것',
    (tester) async {
      final server = _Server(record: _savedRecord());
      final (app, _) = await _open(
        tester,
        server,
        uploads: [_job('j1', failures: 1)],
      );
      app.picker.picked = ['/picked/a.jpg', '/picked/b.jpg'];

      // _tap 의 ensureVisible 은 사진 줄을 옆으로 밀어 [사진 추가]를 가린다 — 보이는 채로 누른다.
      await tester.tap(
        find.bySemanticsLabel('${AppStrings.removePhoto} 전 사진 1'),
      );
      await settle(tester);
      await _tap(tester, find.bySemanticsLabel(AppStrings.addPhoto));
      await _tap(tester, find.text(AppStrings.phaseBefore).last);
      await _tap(tester, _button(AppStrings.pickFromAlbum));

      expect(app.picker.limits, [26]);
      expect(app.queue.added.single.visitId, 101);
      expect(app.queue.added.single.phase, MediaPhase.before);
      expect(app.queue.added.single.sources, [
        '/picked/a.jpg',
        '/picked/b.jpg',
      ]);
    },
  );

  testWidgets('사진 30장과 영상 3편이 다 차면 시트도 선택기도 없이 한도 문구를 보인다', (tester) async {
    final server = _Server(
      record: recordJson(
        media: [
          for (var i = 0; i < 29; i++)
            recordMediaJson(mediaId: 100 + i, sortOrder: i),
          for (var i = 0; i < 3; i++)
            recordMediaJson(mediaId: 200 + i, sortOrder: 29 + i, kind: 'video'),
        ],
        version: 3,
      ),
    );
    final (app, _) = await _open(tester, server, uploads: [_job('j1')]);

    await _tap(tester, find.bySemanticsLabel(AppStrings.addPhoto));

    expect(find.text('방문 하나에 사진은 30장, 영상은 3편까지 붙일 수 있어요.'), findsOneWidget);
    expect(_button(AppStrings.takePhoto), findsNothing);
    expect(app.picker.limits, isEmpty);
    expect(app.queue.added, isEmpty);
  });

  testWidgets('선택기가 남은 자리보다 많이 돌려주면 남은 만큼만 대기열에 넣는다', (tester) async {
    final server = _Server(
      record: recordJson(
        media: [
          for (var i = 0; i < 28; i++)
            recordMediaJson(mediaId: 100 + i, sortOrder: i),
        ],
        version: 3,
      ),
    );
    final (app, _) = await _open(tester, server);
    app.picker.picked = ['/picked/a.jpg', '/picked/b.jpg', '/picked/c.jpg'];

    await _tap(tester, find.bySemanticsLabel(AppStrings.addPhoto));
    await _tap(tester, _button(AppStrings.pickFromAlbum));

    expect(app.picker.limits, [2]);
    expect(app.queue.added.single.sources, ['/picked/a.jpg', '/picked/b.jpg']);
  });

  testWidgets('추가 시트에 영상 고르기·찍기가 있고, 앨범 영상을 고르면 대기열에 넣는다', (tester) async {
    final server = _Server();
    final (app, _) = await _open(tester, server);
    app.picker
      ..pickedVideo = '/picked/v.mov'
      ..takenVideo = '/taken/v.mov';

    await _tap(tester, find.bySemanticsLabel(AppStrings.addPhoto));
    expect(_button(AppStrings.pickFromAlbum), findsOneWidget);
    expect(_button(AppStrings.takePhoto), findsOneWidget);
    expect(_button(AppStrings.takeVideo), findsOneWidget);
    await _tap(tester, _button(AppStrings.pickVideo));

    expect(app.queue.addedVideos.single.visitId, 101);
    expect(app.queue.addedVideos.single.phase, MediaPhase.after);
    expect(app.queue.addedVideos.single.source, '/picked/v.mov');
    expect(app.queue.added, isEmpty);

    await _tap(tester, find.bySemanticsLabel(AppStrings.addPhoto));
    await _tap(tester, _button(AppStrings.takeVideo));

    expect(app.picker.videoMaxSeconds, [60]);
    expect(app.queue.addedVideos.last.source, '/taken/v.mov');
  });

  testWidgets('60초를 넘긴 영상은 앞부분만 올렸다고 스낵바로 알린다', (tester) async {
    final server = _Server();
    final (app, _) = await _open(tester, server);
    app.picker.pickedVideo = '/picked/long.mov';
    app.queue.videoOutcome = VideoAddOutcome.trimmed;

    await _tap(tester, find.bySemanticsLabel(AppStrings.addPhoto));
    await _tap(tester, _button(AppStrings.pickVideo));

    expect(find.text('60초까지만 올릴 수 있어 앞부분 60초를 올렸어요.'), findsOneWidget);
  });

  testWidgets('올릴 수 없는 영상은 문구만 보이고 타일은 없다', (tester) async {
    final server = _Server();
    final (app, _) = await _open(tester, server);
    app.picker.pickedVideo = '/picked/broken.mov';
    app.queue.videoOutcome = VideoAddOutcome.unsupported;

    await _tap(tester, find.bySemanticsLabel(AppStrings.addPhoto));
    await _tap(tester, _button(AppStrings.pickVideo));

    expect(find.text('이 영상은 올릴 수 없어요.'), findsOneWidget);
    expect(find.byIcon(Icons.play_arrow_rounded), findsNothing);
  });

  testWidgets('영상이 3편이면 영상 항목은 비활성이고 누르면 한도 문구다', (tester) async {
    final server = _Server(record: _videoRecord(2));
    final (app, _) = await _open(
      tester,
      server,
      uploads: [_job('v1', kind: MediaKind.video, failures: 1)],
    );
    app.picker.pickedVideo = '/picked/v.mov';

    await tester.tap(find.bySemanticsLabel(AppStrings.addPhoto));
    await settle(tester);

    // 사진은 남아 누를 수 있고, 영상 둘은 회색이다.
    expect(tester.widget<AppButton>(_button(AppStrings.pickFromAlbum)).onPressed, isNotNull);
    expect(tester.widget<AppButton>(_button(AppStrings.pickVideo)).onPressed, isNull);
    expect(tester.widget<AppButton>(_button(AppStrings.takeVideo)).onPressed, isNull);
    await _tap(
      tester,
      find
          .ancestor(
            of: _button(AppStrings.pickVideo),
            matching: find.byType(Pressable),
          )
          .first,
    );

    expect(find.text('방문 하나에 사진은 30장, 영상은 3편까지 붙일 수 있어요.'), findsOneWidget);
    expect(app.queue.addedVideos, isEmpty);
  });

  testWidgets('영상 타일에는 재생 표시와 길이가 보인다', (tester) async {
    final server = _Server(record: _videoRecord(1, durationSeconds: 42));
    await _open(
      tester,
      server,
      // 압축 중이라 길이를 아직 모른다 — 재생 표시만.
      uploads: [
        _job('v1', kind: MediaKind.video, stage: UploadStage.preparing),
      ],
    );

    expect(find.byIcon(Icons.play_arrow_rounded), findsNWidgets(2));
    expect(find.text('0:42'), findsOneWidget);
  });

  testWidgets('200MB 를 넘어 멈춘 항목의 시트에는 [다시 시도]가 없다', (tester) async {
    final server = _Server();
    final (app, _) = await _open(
      tester,
      server,
      uploads: [
        _job('v1', kind: MediaKind.video, stoppedCode: 'MEDIA_TOO_LARGE'),
      ],
    );

    await _tap(tester, find.bySemanticsLabel(AppStrings.uploadStopped));

    expect(find.text('사진은 20MB, 영상은 200MB까지 올릴 수 있어요.'), findsOneWidget);
    expect(find.text(AppStrings.retry), findsNothing);
    await _tap(tester, find.text(AppStrings.removeUpload).last);
    expect(app.queue.removed, ['v1']);
  });

  testWidgets('대기열이 사진을 붙여 상세를 다시 읽으면 새 사진이 폼에 들어오고, 저장에 함께 간다', (
    tester,
  ) async {
    final server = _Server(
      record: recordJson(media: [recordMediaJson(mediaId: 51)], version: 3),
    );
    final (app, _) = await _open(tester, server);
    server.record = recordJson(
      media: [
        recordMediaJson(mediaId: 51),
        recordMediaJson(mediaId: 61, phase: 'after'),
      ],
      version: 4,
    );

    app.setup.container.invalidate(visitDetailProvider);
    await settle(tester);

    expect(find.bySemanticsLabel('후 사진 1'), findsOneWidget);
    server.putResponses.add(
      FakeResponse(statusCode: 200, data: recordJson(version: 5)),
    );
    await _tap(tester, _button(AppStrings.save));
    expect(
      (server.puts.single['media'] as List).map((m) => (m as Map)['media_id']),
      [51, 61],
    );
  });

  group('말로 기록하기', () {
    testWidgets('케어 메모의 마이크를 누르면 듣기 시작하고, partial 이 커서 자리에 회색으로, final 이 굳어 들어간다', (
      tester,
    ) async {
      final server = _Server(record: recordJson(careNote: '앞뒤', version: 3));
      final (app, _) = await _open(tester, server);
      final speech = app.setup.speech;
      final care = _controller(tester, 'careNote');
      care.selection = const TextSelection.collapsed(offset: 1);

      await _tapMic(tester, AppStrings.careNoteLabel);
      expect(_listening(tester, AppStrings.careNoteLabel), isTrue);
      expect(_listening(tester, AppStrings.internalNoteLabel), isFalse);
      expect(speech.starts, ['ko-KR']);

      speech.emitPartial('안녕');
      await tester.pump();
      expect(care.text, '앞안녕뒤');
      expect(care.pending, const TextRange(start: 1, end: 3));

      speech.emitFinal('안녕하세요');
      await tester.pump();
      expect(care.text, '앞안녕하세요뒤');
      expect(care.pending, isNull);

      await _tapMic(tester, AppStrings.careNoteLabel);
      expect(_listening(tester, AppStrings.careNoteLabel), isFalse);
      expect(speech.stops, 1);
      await _tap(tester, _button(AppStrings.save));
      expect(server.puts.single['care_note'], '앞안녕하세요뒤');
    });

    testWidgets('듣는 중에 내부 메모의 마이크를 누르면 앞 것이 끝나고 뒤 것이 시작한다', (tester) async {
      final (app, _) = await _open(tester, _Server());
      final speech = app.setup.speech;

      await _tapMic(tester, AppStrings.careNoteLabel);
      speech.emitPartial('발바닥');
      await tester.pump();
      await _tapMic(tester, AppStrings.internalNoteLabel);

      expect(_listening(tester, AppStrings.careNoteLabel), isFalse);
      expect(_listening(tester, AppStrings.internalNoteLabel), isTrue);
      // 앞 칸의 cancel 이 뒤 칸의 start 보다 먼저다 — 늦으면 뒤 칸의 네이티브 세션을 끊는다.
      expect(speech.calls, ['start', 'cancel', 'start']);
      expect(_text(tester, 'careNote'), '발바닥');
      expect(_controller(tester, 'careNote').pending, isNull);

      speech.emitFinal('예민함');
      await tester.pump();
      expect(_text(tester, 'careNote'), '발바닥');
      expect(_text(tester, 'internalNote'), '예민함');
      await _tapMic(tester, AppStrings.internalNoteLabel);
    });

    testWidgets('지원하지 않는 기기면 안내 스낵바가 뜨고 시작하지 않는다', (tester) async {
      final (app, _) = await _open(tester, _Server());
      app.setup.speech.availabilityResult = const SpeechAvailability(
        supported: false,
        reason: SpeechUnsupported.device,
      );

      await _tap(tester, _mic(AppStrings.careNoteLabel));

      expect(find.text(AppStrings.dictationUnsupported), findsOneWidget);
      expect(app.setup.speech.starts, isEmpty);
      expect(_listening(tester, AppStrings.careNoteLabel), isFalse);
    });

    testWidgets('권한을 거부하면 안내와 [설정 열기]가 뜨고 누르면 설정을 연다', (tester) async {
      final (app, _) = await _open(tester, _Server());
      app.setup.speech.permissionResult = SpeechPermission.denied;

      await _tap(tester, _mic(AppStrings.careNoteLabel));

      expect(find.text(AppStrings.dictationDenied), findsOneWidget);
      expect(app.setup.speech.starts, isEmpty);
      await _tap(tester, find.text(AppStrings.openSettings));
      expect(app.setup.speech.settingsOpened, 1);
    });

    testWidgets('아무 말도 못 알아들으면 문구가 뜬다', (tester) async {
      final (app, _) = await _open(tester, _Server());

      await _tapMic(tester, AppStrings.careNoteLabel);
      app.setup.speech.emitError(SpeechErrorCode.noSpeech);
      await settle(tester);

      expect(find.text(AppStrings.dictationNoSpeech), findsOneWidget);
      expect(_listening(tester, AppStrings.careNoteLabel), isFalse);
      expect(_text(tester, 'careNote'), '');
    });

    testWidgets('다른 칸을 누르면 듣기가 끝난다', (tester) async {
      final (app, _) = await _open(tester, _Server());

      await _tapMic(tester, AppStrings.careNoteLabel);
      await tester.tap(_field('internalNote'));
      await settle(tester);

      expect(app.setup.speech.cancels, 1);
      expect(_listening(tester, AppStrings.careNoteLabel), isFalse);
    });

    testWidgets('화면을 나가면 cancel 한다', (tester) async {
      final (app, closed) = await _open(tester, _Server());

      await _tapMic(tester, AppStrings.careNoteLabel);
      await tester.binding.handlePopRoute();
      await settle(tester);

      expect(closed.closed, isTrue);
      expect(app.setup.speech.cancels, 1);
    });

    testWidgets('포커스를 잃었다는 알림 없이 화면이 사라져도 cancel 한다', (tester) async {
      final (app, _) = await _open(tester, _Server());

      await _tapMic(tester, AppStrings.careNoteLabel);
      // 뒤로 가기는 포커스가 먼저 떠나 칸의 리스너가 끝낸다 — 앱째 내려 dispose 만 남긴다.
      await tester.pumpWidget(const SizedBox());

      expect(app.setup.speech.cancels, 1);
    });
  });

  testWidgets('기록 화면 골든', (tester) async {
    final server = _Server(record: _savedRecord());
    final (app, _) = await _open(
      tester,
      server,
      completing: true,
      uploads: [_job('j1', running: true)],
    );
    await tester.runAsync(
      () => precacheImage(
        app.images.image,
        tester.element(find.byKey(ScreenKeys.visitRecord)),
      ),
    );
    tester.view.physicalSize = const Size(390, 1400);
    await tester.pumpAndSettle();

    await expectLater(
      find.byKey(ScreenKeys.visitRecord),
      matchesGoldenFile('goldens/record_screen.png'),
    );
  });
}

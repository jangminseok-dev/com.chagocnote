import 'dart:io';
import 'dart:math';
import 'dart:ui' as ui;

import 'package:chagocnote/core/proxy/photo_renditions.dart';
import 'package:flutter_test/flutter_test.dart';

/// 크기만 맞는 PNG 를 쓴다(내용은 상관없다).
Future<void> _writeImage(String path, int width, int height) async {
  final recorder = ui.PictureRecorder();
  ui.Canvas(recorder).drawRect(
    ui.Rect.fromLTWH(0, 0, width.toDouble(), height.toDouble()),
    ui.Paint()..color = const ui.Color(0xFF808080),
  );
  final image = await recorder.endRecording().toImage(width, height);
  final png = await image.toByteData(format: ui.ImageByteFormat.png);
  image.dispose();
  await File(path).writeAsBytes(png!.buffer.asUint8List());
}

typedef _Call = ({
  String source,
  String target,
  int minWidth,
  int minHeight,
  int quality,
});

/// 플러그인 대역 — 첫 단계는 [sourceSize] 그대로, 그다음은 안드로이드 플러그인과 같은 규칙으로 줄인 크기를 쓴다.
({CompressFile compress, List<_Call> calls}) _fakeCompress(
  (int, int) sourceSize,
) {
  final calls = <_Call>[];
  Future<void> compress(
    String source,
    String target, {
    required int minWidth,
    required int minHeight,
    required int quality,
  }) async {
    calls.add((
      source: source,
      target: target,
      minWidth: minWidth,
      minHeight: minHeight,
      quality: quality,
    ));
    final (w, h) = sourceSize;
    final scale = max(1.0, min(w / minWidth, h / minHeight));
    await _writeImage(target, (w / scale).floor(), (h / scale).floor());
  }

  return (compress: compress, calls: calls);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('긴 변 쪽에 목표 길이, 짧은 변 쪽에 1 을 준다', () {
    expect(renditionBox(4000, 3000, 3000), (3000, 1));
    expect(renditionBox(3000, 4000, 1080), (1, 1080));
    expect(renditionBox(500, 500, 400), (400, 1));
  });

  group('CompressPhotoRenditionMaker', () {
    late Directory dir;
    setUp(
      () async => dir = await Directory.systemTemp.createTemp('renditions'),
    );
    tearDown(() async => dir.delete(recursive: true));

    test(
      '방향을 적용한 사본에서 긴 변 3000·1080·400 을 품질 85·80·75 로 만들고 사본은 지운다',
      () async {
        final fake = _fakeCompress((3600, 1200));
        final out = Directory('${dir.path}/job');

        final made = await CompressPhotoRenditionMaker(
          compress: fake.compress,
        ).make('/picked/IMG_1.HEIC', out);

        final upright = '${out.path}/upright.jpg';
        expect(
          fake.calls.map(
            (c) => (c.source, c.target, c.minWidth, c.minHeight, c.quality),
          ),
          [
            ('/picked/IMG_1.HEIC', upright, 100000, 100000, 95),
            (upright, '${out.path}/original.jpg', 3000, 1, 85),
            (upright, '${out.path}/display.jpg', 1080, 1, 80),
            (upright, '${out.path}/thumb.jpg', 400, 1, 75),
          ],
        );
        expect((made.width, made.height), (3000, 1000));
        expect(
          [
            made.original,
            made.display,
            made.thumb,
          ].every((p) => File(p).existsSync()),
          isTrue,
        );
        expect(File(upright).existsSync(), isFalse);
      },
    );

    test('세로 사진은 세로가 긴 변이고, 작은 사진은 키우지 않는다', () async {
      final fake = _fakeCompress((900, 1600));

      final made = await CompressPhotoRenditionMaker(
        compress: fake.compress,
      ).make('/p.jpg', dir);

      expect(fake.calls[1].minWidth, 1);
      expect(fake.calls[1].minHeight, 3000);
      expect((made.width, made.height), (900, 1600));
    });

    test('변환이 실패해도 사본을 남기지 않는다', () async {
      var n = 0;
      Future<void> compress(
        String s,
        String t, {
        required int minWidth,
        required int minHeight,
        required int quality,
      }) async {
        if (n++ == 0) return _writeImage(t, 10, 10);
        throw StateError('변환 실패');
      }

      await expectLater(
        CompressPhotoRenditionMaker(compress: compress).make('/p.jpg', dir),
        throwsStateError,
      );
      expect(File('${dir.path}/upright.jpg').existsSync(), isFalse);
    });
  });
}

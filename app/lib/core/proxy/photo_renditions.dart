import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 사진 한 장에서 만든 올릴 파일 셋(설계 7.2). 가로·세로는 원본 렌디션의 값이다.
class PhotoRenditions {
  const PhotoRenditions({
    required this.original,
    required this.display,
    required this.thumb,
    required this.width,
    required this.height,
  });

  final String original;
  final String display;
  final String thumb;
  final int width;
  final int height;
}

/// 렌디션 만들기 — 화면·대기열이 압축 플러그인을 직접 부르지 않게 감싼 자리.
abstract class PhotoRenditionMaker {
  /// [source]를 읽어 [outDir]에 `original.jpg`·`display.jpg`·`thumb.jpg`를 쓴다.
  Future<PhotoRenditions> make(String source, Directory outDir);
}

/// 긴 변의 길이(설계 7.2)와 JPEG 품질.
const originalLongSide = 3000;
const displayLongSide = 1080;
const thumbLongSide = 400;
const originalQuality = 85;
const displayQuality = 80;
const thumbQuality = 75;

/// 압축 플러그인에 줄 (minWidth, minHeight) — 긴 변이 [longSide]가 되게 한다(작으면 키우지 않는다).
///
/// 플러그인은 두 값 중 한쪽에 맞춰 비율을 정한다(iOS 는 가로세로 비율로 고르고, 안드로이드는 작은 쪽을
/// 고른다). 짧은 변 쪽을 1로 주면 두 플랫폼 모두 긴 변 쪽 값으로 줄인다.
(int, int) renditionBox(int width, int height, int longSide) =>
    width >= height ? (longSide, 1) : (1, longSide);

/// 줄이지 않는 상자 — 방향만 픽셀에 적용하고 EXIF 를 지우는 첫 단계에 쓴다.
const _noResize = 100000;

typedef CompressFile =
    Future<void> Function(
      String source,
      String target, {
      required int minWidth,
      required int minHeight,
      required int quality,
    });

Future<void> _compressWithPlugin(
  String source,
  String target, {
  required int minWidth,
  required int minHeight,
  required int quality,
}) async {
  // keepExif: false 로 GPS 를 포함한 EXIF 를 지우고, autoCorrectionAngle 로 방향을 픽셀에 적용한다.
  final out = await FlutterImageCompress.compressAndGetFile(
    source,
    target,
    minWidth: minWidth,
    minHeight: minHeight,
    quality: quality,
    format: CompressFormat.jpeg,
    keepExif: false,
    autoCorrectionAngle: true,
  );
  if (out == null) throw StateError('사진을 변환하지 못했습니다.');
}

/// 머리만 읽어 가로·세로를 잰다(픽셀을 풀지 않는다).
Future<(int, int)> readImageSize(String path) async {
  final buffer = await ui.ImmutableBuffer.fromFilePath(path);
  final descriptor = await ui.ImageDescriptor.encoded(buffer);
  final size = (descriptor.width, descriptor.height);
  descriptor.dispose();
  buffer.dispose();
  return size;
}

/// 먼저 원래 크기 그대로 방향을 적용하고 EXIF 를 지운 JPEG 를 만든다(HEIC 도 여기서 JPEG 가 된다).
/// 그 파일의 가로·세로로 긴 변을 알아낸 뒤 렌디션 셋을 만들고 첫 파일은 지운다.
///
/// 설계 7.2 의 프로그레시브 JPEG 는 플러그인이 지원하지 않아 기본(baseline) JPEG 다(결정 기록 007).
class CompressPhotoRenditionMaker implements PhotoRenditionMaker {
  const CompressPhotoRenditionMaker({this._compress = _compressWithPlugin});

  final CompressFile _compress;

  @override
  Future<PhotoRenditions> make(String source, Directory outDir) async {
    await outDir.create(recursive: true);
    final upright = '${outDir.path}/upright.jpg';
    await _compress(
      source,
      upright,
      minWidth: _noResize,
      minHeight: _noResize,
      quality: 95,
    );
    try {
      final (w, h) = await readImageSize(upright);
      Future<String> render(String name, int longSide, int quality) async {
        final target = '${outDir.path}/$name.jpg';
        final (minWidth, minHeight) = renditionBox(w, h, longSide);
        await _compress(
          upright,
          target,
          minWidth: minWidth,
          minHeight: minHeight,
          quality: quality,
        );
        return target;
      }

      final original = await render(
        'original',
        originalLongSide,
        originalQuality,
      );
      final display = await render('display', displayLongSide, displayQuality);
      final thumb = await render('thumb', thumbLongSide, thumbQuality);
      final (width, height) = await readImageSize(original);
      return PhotoRenditions(
        original: original,
        display: display,
        thumb: thumb,
        width: width,
        height: height,
      );
    } finally {
      await _deleteQuietly(upright);
    }
  }
}

Future<void> _deleteQuietly(String path) async {
  try {
    await File(path).delete();
  } on FileSystemException {
    // 이미 없다.
  }
}

final photoRenditionMakerProvider = Provider<PhotoRenditionMaker>(
  (ref) => const CompressPhotoRenditionMaker(),
);

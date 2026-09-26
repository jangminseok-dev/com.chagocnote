import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';

import '../error/api_exception.dart';

/// 큰 파일(영상 원본)을 임시 파일로 받는다. 이미지 캐시(`MediaImages`)를 거치지 않는다 — mp4 는 수십 MB 라
/// 캐시에 두지 않는다(④-3a 설계 5.1). 받은 파일은 부른 쪽이 쓰고 지운다.
abstract class MediaFiles {
  /// [url]을 임시 폴더의 `video-<밀리초><suffix>` 로 받아 그 경로를 준다. 실패는 [ApiException].
  Future<String> download(String url, {required String suffix});
}

/// 서명 URL 전용 Dio 로 받는다 — `UploadClient` 와 같은 방식(인증 헤더 없음, 연결·응답 대기만 제한).
class DioMediaFiles implements MediaFiles {
  DioMediaFiles({Dio? dio})
    : _dio = dio ?? Dio(BaseOptions(connectTimeout: connectTimeout));

  static const connectTimeout = Duration(seconds: 10);
  static const receiveTimeout = Duration(seconds: 30);

  final Dio _dio;

  @override
  Future<String> download(String url, {required String suffix}) async {
    final dir = await getTemporaryDirectory();
    final path =
        '${dir.path}/video-${DateTime.now().millisecondsSinceEpoch}$suffix';
    try {
      await _dio.download(
        url,
        path,
        options: Options(receiveTimeout: receiveTimeout),
      );
    } on DioException catch (e) {
      // 받다 만 파일을 남기지 않는다.
      final partial = File(path);
      if (partial.existsSync()) await partial.delete();
      throw ApiException.fromDioException(e);
    }
    return path;
  }
}

final mediaFilesProvider = Provider<MediaFiles>((ref) => DioMediaFiles());

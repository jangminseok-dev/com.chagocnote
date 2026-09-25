import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_cache_manager/flutter_cache_manager.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 서명 URL 사진을 기기에 캐시해 보여 주는 자리. 화면은 이 프로바이더에서 [ImageProvider]만 받는다.
abstract class MediaImages {
  ImageProvider of(String url);

  /// 원본(약 2MB)은 표시용과 따로 작은 캐시에 둔다 — 크게 보기가 표시용 캐시를 밀어내지 않게.
  ImageProvider original(String url);

  /// 원본 파일을 기기에 받아 그 경로를 돌려준다(원본 저장). [original]과 같은 캐시·같은 키라 크게 보기에서
  /// 본 원본은 다시 받지 않는다.
  Future<String> fileOf(String url);
}

/// 캐시 키 — 서명(쿼리)을 뺀 객체 주소. 서명 URL 은 하루마다 바뀌지만(설계 7.3) 객체 키는
/// 사진·렌디션마다 하나라, 같은 사진은 날이 바뀌어도 다시 받지 않는다.
String mediaCacheKey(String url) {
  final uri = Uri.parse(url);
  return '${uri.host}${uri.path}';
}

/// 캐시는 처음 사진을 보일 때 만든다 — 만들 때 캐시 폴더를 찾으므로, 사진 없는 화면(과 그 테스트)은
/// 파일 시스템을 건드리지 않는다.
class CachedMediaImages implements MediaImages {
  CachedMediaImages([this._cache, this._originals]);

  BaseCacheManager? _cache;
  BaseCacheManager? _originals;

  BaseCacheManager get _manager => _cache ??= CacheManager(
    Config('chagocnote-media', maxNrOfCacheObjects: mediaCacheMaxObjects),
  );

  BaseCacheManager get _originalManager => _originals ??= CacheManager(
    Config(
      'chagocnote-originals',
      maxNrOfCacheObjects: originalCacheMaxObjects,
    ),
  );

  @override
  ImageProvider of(String url) => CachedNetworkImageProvider(
    url,
    cacheKey: mediaCacheKey(url),
    cacheManager: _manager,
  );

  @override
  ImageProvider original(String url) => CachedNetworkImageProvider(
    url,
    cacheKey: mediaCacheKey(url),
    cacheManager: _originalManager,
  );

  @override
  Future<String> fileOf(String url) async =>
      (await _originalManager.getSingleFile(url, key: mediaCacheKey(url))).path;
}

/// 썸네일·표시용 사진 캐시 상한. 캐시 패키지는 바이트가 아니라 개수로만 제한한다 — 썸네일(약 30KB)·표시용(약 250KB)이
/// 대부분이라 1500개면 설계 10.3 의 500MB 안쪽이다(결정 기록 007). 30일 안 본 사진은 지운다.
const mediaCacheMaxObjects = 1500;

/// 원본 캐시 상한 — 원본은 약 2MB 라 40장(약 80MB)만 둔다.
const originalCacheMaxObjects = 40;

final mediaImagesProvider = Provider<MediaImages>((ref) => CachedMediaImages());

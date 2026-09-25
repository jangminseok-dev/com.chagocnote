import 'package:cached_network_image/cached_network_image.dart';
import 'package:chagocnote/core/proxy/media_images.dart';
import 'package:flutter_cache_manager/flutter_cache_manager.dart';
import 'package:flutter_test/flutter_test.dart';

class _Cache implements BaseCacheManager {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  const today = 'https://media.example/chagocnote-media/thumb/shops/1/51.jpg?X-Amz-Date=20260925T040000Z&X-Amz-Signature=aa';
  const tomorrow = 'https://media.example/chagocnote-media/thumb/shops/1/51.jpg?X-Amz-Date=20260926T040000Z&X-Amz-Signature=bb';

  test('캐시 키는 서명을 뺀 객체 주소다 — 날이 바뀌어 서명이 달라도 같은 사진은 같은 키', () {
    expect(mediaCacheKey(today), 'media.example/chagocnote-media/thumb/shops/1/51.jpg');
    expect(mediaCacheKey(tomorrow), mediaCacheKey(today));
    expect(
      mediaCacheKey('https://media.example/chagocnote-media/display/shops/1/51.jpg?X-Amz-Signature=aa'),
      isNot(mediaCacheKey(today)),
    );
  });

  test('CachedMediaImages 는 그 키와 사진 캐시로 읽는다', () {
    final cache = _Cache();

    final image = CachedMediaImages(cache).of(today) as CachedNetworkImageProvider;

    expect(image.url, today);
    expect(image.cacheKey, mediaCacheKey(today));
    expect(image.cacheManager, same(cache));
  });
}

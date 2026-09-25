import 'package:cached_network_image/cached_network_image.dart';
import 'package:chagocnote/core/proxy/media_images.dart';
import 'package:flutter_cache_manager/flutter_cache_manager.dart';
import 'package:flutter_test/flutter_test.dart';

class _Cache implements BaseCacheManager {
  final asked = <(String, String?)>[];

  // getSingleFile 의 File 은 `package:file` 의 것이라, 그 패키지를 들이지 않고 캐시 패키지의 메모리 파일로 돌려준다.
  @override
  dynamic noSuchMethod(Invocation invocation) {
    if (invocation.memberName == #getSingleFile) {
      final url = invocation.positionalArguments.single as String;
      final key = invocation.namedArguments[#key] as String?;
      asked.add((url, key));
      return MemoryCacheSystem().createFile('cached.jpg');
    }
    return super.noSuchMethod(invocation);
  }
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

  test('원본은 표시용과 다른 작은 캐시로 보이고, 원본 파일도 그 캐시에서 같은 키로 받는다 — 크게 보기에서 본 원본은 다시 받지 않는다', () async {
    final cache = _Cache();
    final originals = _Cache();
    final images = CachedMediaImages(cache, originals);

    final image = images.original(today) as CachedNetworkImageProvider;
    final path = await images.fileOf(today);

    expect(image.url, today);
    expect(image.cacheKey, mediaCacheKey(today));
    expect(image.cacheManager, same(originals));
    expect(originals.asked.single, (today, mediaCacheKey(today)));
    expect(cache.asked, isEmpty);
    expect(path, endsWith('/cached.jpg'));
  });
}

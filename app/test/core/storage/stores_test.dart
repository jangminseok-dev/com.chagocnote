import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('토큰을 저장하고 읽고 지운다', () async {
    final store = MemoryTokenStore();
    expect(await store.readAccess(), isNull);
    await store.save(access: 'a', refresh: 'r');
    expect([await store.readAccess(), await store.readRefresh()], ['a', 'r']);
    await store.clear();
    expect([await store.readAccess(), await store.readRefresh()], [null, null]);
  });

  test('마지막으로 고른 매장을 기억하고 지운다', () async {
    final prefs = MemoryPrefsStore();
    expect(await prefs.readLastShopId(), isNull);
    await prefs.writeLastShopId(3);
    expect(await prefs.readLastShopId(), 3);
    await prefs.clear();
    expect(await prefs.readLastShopId(), isNull);
  });

  test('키로 읽고 쓴다 — 설정이 늘어도 저장소 인터페이스는 그대로다', () async {
    final prefs = MemoryPrefsStore();
    expect(await prefs.read('anything'), isNull);
    await prefs.write('anything', 'value');
    expect(await prefs.read('anything'), 'value');
  });

  test('보기 방식 같은 기기 설정은 clear 가 지우지 않는다', () async {
    final prefs = MemoryPrefsStore();
    await prefs.write(PrefsKeys.customerViewMode, 'grid');
    await prefs.write(PrefsKeys.dayViewMode, 'timeline');
    await prefs.writeLastShopId(3);
    await prefs.clear();
    expect(await prefs.read(PrefsKeys.customerViewMode), 'grid');
    expect(await prefs.read(PrefsKeys.dayViewMode), 'timeline');
    expect(await prefs.readLastShopId(), isNull);
  });
}

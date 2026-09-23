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

  test('고객 목록 보기 방식은 기억하고, 로그아웃 정리(clear)로 지워지지 않는다', () async {
    final prefs = MemoryPrefsStore();
    expect(await prefs.readCustomerViewMode(), isNull);
    await prefs.writeCustomerViewMode('grid');
    await prefs.clear();
    expect(await prefs.readCustomerViewMode(), 'grid');
  });
}

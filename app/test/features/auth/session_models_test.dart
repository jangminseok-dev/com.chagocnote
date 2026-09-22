import 'package:chagocnote/features/auth/state/session.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ShopMembership', () {
    test('서버가 주는 스네이크케이스 JSON을 그대로 읽는다', () {
      final shop = ShopMembership.fromJson({
        'shop_id': 7,
        'shop_name': 'Hiss Haus',
        'role': 'owner',
      });

      expect(shop.shopId, 7);
      expect(shop.shopName, 'Hiss Haus');
      expect(shop.role, 'owner');
    });

    test('role 이 owner 이면 isOwner 가 true 다', () {
      const owner = ShopMembership(shopId: 1, shopName: 'A', role: 'owner');
      const staff = ShopMembership(shopId: 2, shopName: 'B', role: 'staff');

      expect(owner.isOwner, isTrue);
      expect(staff.isOwner, isFalse);
    });
  });

  group('Me', () {
    test('서버가 주는 스네이크케이스 JSON을 그대로 읽는다', () {
      final me = Me.fromJson({
        'id': 42,
        'display_name': '민석',
        'profile_image_url': 'https://example.com/a.png',
        'identities': ['apple', 'kakao'],
        'shops': [
          {'shop_id': 1, 'shop_name': 'A매장', 'role': 'owner'},
        ],
      });

      expect(me.id, 42);
      expect(me.displayName, '민석');
      expect(me.profileImageUrl, 'https://example.com/a.png');
      expect(me.identities, ['apple', 'kakao']);
      expect(me.shops, hasLength(1));
      expect(me.shops.single.shopName, 'A매장');
    });

    test('profile_image_url 이 null 이어도 파싱된다', () {
      final me = Me.fromJson({
        'id': 1,
        'display_name': '민석',
        'profile_image_url': null,
        'identities': <String>[],
        'shops': <Map<String, dynamic>>[],
      });

      expect(me.profileImageUrl, isNull);
      expect(me.shops, isEmpty);
    });
  });

  group('SignedIn.selectedShop', () {
    const ownerA = ShopMembership(shopId: 1, shopName: 'A매장', role: 'owner');
    const staffB = ShopMembership(shopId: 2, shopName: 'B매장', role: 'staff');
    final me = Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: const ['apple'],
      shops: [ownerA, staffB],
    );

    test('selectedShopId 와 일치하는 매장을 돌려준다', () {
      final signedIn = SignedIn(me: me, selectedShopId: staffB.shopId);
      expect(signedIn.selectedShop, staffB);
    });

    test('selectedShopId 가 null 이면 null 이다', () {
      final signedIn = SignedIn(me: me, selectedShopId: null);
      expect(signedIn.selectedShop, isNull);
    });

    test('selectedShopId 가 소속 목록에 없으면 null 이다', () {
      final signedIn = SignedIn(me: me, selectedShopId: 999);
      expect(signedIn.selectedShop, isNull);
    });
  });

  test('SignedOut 의 sessionExpired 기본값은 false 다', () {
    expect(const SignedOut().sessionExpired, isFalse);
    expect(const SignedOut(sessionExpired: true).sessionExpired, isTrue);
  });
}

import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/shop_selection.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_session_gateway.dart';

const _ownerA = ShopMembership(shopId: 1, shopName: 'A매장', role: 'owner');
const _staffB = ShopMembership(shopId: 2, shopName: 'B매장', role: 'staff');

Me _me({List<ShopMembership> shops = const [], String displayName = '민석'}) =>
    Me(
      id: 7,
      displayName: displayName,
      profileImageUrl: null,
      identities: const ['apple'],
      shops: shops,
    );

Future<ProviderContainer> _signedIn(FakeSessionGateway gateway) async {
  final container = ProviderContainer(
    overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
  );
  addTearDown(container.dispose);
  await container.read(sessionControllerProvider.future);
  return container;
}

void main() {
  test('매장이 하나면 그 매장의 ID·이름·역할·수를 준다', () async {
    final container = await _signedIn(
      FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]),
    );
    expect(container.read(selectedShopIdProvider), 1);
    expect(container.read(shopNameProvider), 'A매장');
    expect(container.read(isOwnerProvider), isTrue);
    expect(container.read(shopCountProvider), 1);
    expect(container.read(currentUserIdProvider), 7);
  });

  test('로그아웃이면 매장 값이 비어 있다', () async {
    final container = await _signedIn(FakeSessionGateway()..meOnRestore = null);
    expect(container.read(selectedShopIdProvider), isNull);
    expect(container.read(shopNameProvider), '');
    expect(container.read(isOwnerProvider), isFalse);
    expect(container.read(shopCountProvider), 0);
    expect(container.read(currentUserIdProvider), isNull);
  });

  test('직원 매장을 고르면 사장이 아니다', () async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(shops: [_ownerA, _staffB])
      ..lastShopId = 2;
    final container = await _signedIn(gateway);
    expect(container.read(selectedShopIdProvider), 2);
    expect(container.read(isOwnerProvider), isFalse);
    expect(container.read(shopNameProvider), 'B매장');
  });

  test('Me 가 갱신돼도 값이 같으면 파생 프로바이더는 다시 알리지 않는다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final container = await _signedIn(gateway);
    var shopIdNotified = 0;
    var nameNotified = 0;
    container.listen(selectedShopIdProvider, (_, _) => shopIdNotified++);
    container.listen(shopNameProvider, (_, _) => nameNotified++);

    // 표시 이름만 바뀐 새 Me — 매장 값은 그대로다.
    gateway.meOnRefresh = _me(shops: [_ownerA], displayName: '민석2');
    await container.read(sessionControllerProvider.notifier).reloadMe();
    // 파생 프로바이더의 알림은 다음 이벤트 루프에서 전달된다.
    await container.pump();

    expect(shopIdNotified, 0);
    expect(nameNotified, 0);
  });

  test('매장 이름이 바뀌면 이름 프로바이더만 알린다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final container = await _signedIn(gateway);
    var shopIdNotified = 0;
    var nameNotified = 0;
    container.listen(selectedShopIdProvider, (_, _) => shopIdNotified++);
    container.listen(shopNameProvider, (_, _) => nameNotified++);

    gateway.meOnRefresh = _me(
      shops: const [
        ShopMembership(shopId: 1, shopName: 'A매장(이전)', role: 'owner'),
      ],
    );
    await container.read(sessionControllerProvider.notifier).reloadMe();
    // 파생 프로바이더의 알림은 다음 이벤트 루프에서 전달된다.
    await container.pump();

    expect(shopIdNotified, 0);
    expect(nameNotified, 1);
    expect(container.read(shopNameProvider), 'A매장(이전)');
  });
}

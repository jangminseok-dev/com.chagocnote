import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/session_gateway.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_session_gateway.dart';

const _ownerA = ShopMembership(shopId: 1, shopName: 'A매장', role: 'owner');
const _staffB = ShopMembership(shopId: 2, shopName: 'B매장', role: 'staff');

Me _me({List<ShopMembership> shops = const [], String name = '민석'}) => Me(
      id: 1,
      displayName: name,
      profileImageUrl: null,
      identities: const ['apple'],
      shops: shops,
    );

ProviderContainer _containerWith(SessionGateway gateway) => ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
    );

void main() {
  group('매장 선택 규칙 (복원)', () {
    test('복원할 세션이 없으면 SignedOut 이 된다', () async {
      final gateway = FakeSessionGateway()..meOnRestore = null;
      final container = _containerWith(gateway);

      final session = await container.read(sessionControllerProvider.future);

      expect(session, isA<SignedOut>());
      expect((session as SignedOut).sessionExpired, isFalse);
    });

    test('매장이 없는 사용자는 selectedShopId 가 null 인 SignedIn 이 된다', () async {
      final gateway = FakeSessionGateway()..meOnRestore = _me(shops: const []);
      final container = _containerWith(gateway);

      final session = await container.read(sessionControllerProvider.future);

      final signedIn = session as SignedIn;
      expect(signedIn.me.shops, isEmpty);
      expect(signedIn.selectedShopId, isNull);
    });

    test('매장이 정확히 하나면 자동으로 선택된다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA])
        ..lastShopId = null;
      final container = _containerWith(gateway);

      final session = await container.read(sessionControllerProvider.future);

      expect((session as SignedIn).selectedShopId, _ownerA.shopId);
    });

    test('기억해둔 매장 id 가 아직 소속 목록에 있으면 그걸 선택한다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA, _staffB])
        ..lastShopId = _staffB.shopId;
      final container = _containerWith(gateway);

      final session = await container.read(sessionControllerProvider.future);

      expect((session as SignedIn).selectedShopId, _staffB.shopId);
    });

    test('매장이 둘 이상인데 기억해둔 id 가 없거나 무효하면 선택하지 않는다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA, _staffB])
        ..lastShopId = 999;
      final container = _containerWith(gateway);

      final session = await container.read(sessionControllerProvider.future);

      expect((session as SignedIn).selectedShopId, isNull);
    });
  });

  group('signIn', () {
    test('성공하면 SignedIn 상태로 바뀌고 매장 선택 규칙이 적용된다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = null
        ..meOnSignIn = _me(shops: [_ownerA]);
      final container = _containerWith(gateway);
      await container.read(sessionControllerProvider.future);

      final notifier = container.read(sessionControllerProvider.notifier);
      const credential = SocialCredential(provider: 'apple', token: 't');
      await notifier.signIn(credential);

      expect(gateway.receivedCredential, credential);
      final state = container.read(sessionControllerProvider);
      expect((state.value as SignedIn).selectedShopId, _ownerA.shopId);
    });

    test('실패하면 상태는 그대로 SignedOut 이고 예외가 그대로 올라온다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = null
        ..signInError = Exception('로그인 실패');
      final container = _containerWith(gateway);
      await container.read(sessionControllerProvider.future);

      final notifier = container.read(sessionControllerProvider.notifier);
      await expectLater(
        notifier.signIn(const SocialCredential(provider: 'apple', token: 't')),
        throwsA(isA<Exception>()),
      );

      final state = container.read(sessionControllerProvider);
      expect(state.hasError, isFalse);
      expect(state.value, isA<SignedOut>());
    });
  });

  test('signOut 을 호출하면 게이트웨이의 signOut 을 부르고 SignedOut 이 된다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final container = _containerWith(gateway);
    await container.read(sessionControllerProvider.future);

    final notifier = container.read(sessionControllerProvider.notifier);
    await notifier.signOut();

    expect(gateway.signOutCalled, isTrue);
    expect(container.read(sessionControllerProvider).value, isA<SignedOut>());
  });

  group('selectShop', () {
    test('선택한 매장을 저장하고 상태를 갱신한다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA, _staffB])
        ..lastShopId = null;
      final container = _containerWith(gateway);
      await container.read(sessionControllerProvider.future);

      final notifier = container.read(sessionControllerProvider.notifier);
      await notifier.selectShop(_staffB.shopId);

      expect(gateway.writtenShopId, _staffB.shopId);
      final signedIn = container.read(sessionControllerProvider).value as SignedIn;
      expect(signedIn.selectedShopId, _staffB.shopId);
    });

    test('소속되지 않은 매장 id 는 무시한다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA])
        ..lastShopId = null;
      final container = _containerWith(gateway);
      await container.read(sessionControllerProvider.future);

      final notifier = container.read(sessionControllerProvider.notifier);
      await notifier.selectShop(999);

      expect(gateway.writtenShopId, isNull);
      final signedIn = container.read(sessionControllerProvider).value as SignedIn;
      expect(signedIn.selectedShopId, _ownerA.shopId);
    });
  });

  group('reloadMe', () {
    test('성공하면 me 를 갱신한다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA], name: '이전이름')
        ..meOnRefresh = _me(shops: [_ownerA], name: '새이름');
      final container = _containerWith(gateway);
      await container.read(sessionControllerProvider.future);

      final notifier = container.read(sessionControllerProvider.notifier);
      await notifier.reloadMe();

      final signedIn = container.read(sessionControllerProvider).value as SignedIn;
      expect(signedIn.me.displayName, '새이름');
    });

    test('선택된 매장이 사라졌으면 다시 규칙을 적용해 미선택으로 되돌린다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA, _staffB])
        ..lastShopId = _staffB.shopId;
      final container = _containerWith(gateway);
      await container.read(sessionControllerProvider.future);
      expect(
        (container.read(sessionControllerProvider).value as SignedIn).selectedShopId,
        _staffB.shopId,
      );

      // staffB 매장에서 빠졌다 — 이제 ownerA 하나뿐이라 자동 선택된다.
      gateway.meOnRefresh = _me(shops: [_ownerA]);
      final notifier = container.read(sessionControllerProvider.notifier);
      await notifier.reloadMe();

      final signedIn = container.read(sessionControllerProvider).value as SignedIn;
      expect(signedIn.selectedShopId, _ownerA.shopId);
    });

    test('실패하면 상태를 그대로 두고 예외를 다시 던진다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA])
        ..refreshMeError = Exception('갱신 실패');
      final container = _containerWith(gateway);
      await container.read(sessionControllerProvider.future);
      final before = container.read(sessionControllerProvider).value;

      final notifier = container.read(sessionControllerProvider.notifier);
      await expectLater(notifier.reloadMe(), throwsA(isA<Exception>()));

      expect(container.read(sessionControllerProvider).value, before);
    });
  });

  test('endSession 은 즉시 sessionExpired 가 true 인 SignedOut 으로 만든다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final container = _containerWith(gateway);
    await container.read(sessionControllerProvider.future);

    final notifier = container.read(sessionControllerProvider.notifier);
    notifier.endSession();

    final state = container.read(sessionControllerProvider).value as SignedOut;
    expect(state.sessionExpired, isTrue);
  });

  group('재시도 끄기', () {
    testWidgets(
      'ProviderContainer.test(retry: (_, __) => null) 이면 '
      'build() 가 실패해도 정확히 한 번만 호출된다',
      (tester) async {
        final gateway = FakeSessionGateway()..restoreError = Exception('복원 실패');
        final container = ProviderContainer.test(
          retry: (retryCount, error) => null,
          overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
        );

        container.listen(sessionControllerProvider, (previous, next) {});
        expect(gateway.restoreCallCount, 1);

        await tester.pump(const Duration(seconds: 10));
        expect(gateway.restoreCallCount, 1);
      },
    );

    testWidgets(
      'retry 옵션 없이 기본값을 쓰면 build() 가 실패했을 때 여러 번 재시도된다',
      (tester) async {
        final gateway = FakeSessionGateway()..restoreError = Exception('복원 실패');
        final container = ProviderContainer.test(
          overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
        );

        container.listen(sessionControllerProvider, (previous, next) {});
        expect(gateway.restoreCallCount, 1);

        // defaultRetry: 200ms * 2^n 지수 백오프.
        await tester.pump(const Duration(milliseconds: 250));
        expect(gateway.restoreCallCount, greaterThan(1));

        // defaultRetry 는 최대 10번까지 Timer 를 예약해 둔다. 테스트가
        // "펜딩 타이머 없음" 불변조건에 걸리지 않도록 명시적으로 정리한다.
        container.dispose();
      },
    );
  });
}

import 'dart:async';

import 'package:chagocnote/core/proxy/network_watcher.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_test/flutter_test.dart';

/// [Connectivity] 대역 — 쓰는 멤버 둘(`onConnectivityChanged`·`checkConnectivity`)만 흉내 낸다.
class _FakeConnectivity implements Connectivity {
  final _controller = StreamController<List<ConnectivityResult>>.broadcast();

  @override
  Stream<List<ConnectivityResult>> get onConnectivityChanged =>
      _controller.stream;

  @override
  Future<List<ConnectivityResult>> checkConnectivity() async =>
      const [ConnectivityResult.wifi];
}

void main() {
  test('끊겼다가 이어질 때만 알린다 — 처음 상태·연결 바뀜·계속 끊김은 신호가 아니다', () async {
    const none = [ConnectivityResult.none];
    const wifi = [ConnectivityResult.wifi];
    const mobile = [ConnectivityResult.mobile];
    final changes = Stream.fromIterable([
      wifi,
      mobile,
      none,
      none,
      wifi,
      none,
      mobile,
    ]);

    expect(await restoredFrom(changes).length, 2);
  });

  test('처음부터 끊겨 있다가 이어지면 알린다', () async {
    final changes = Stream.fromIterable([
      [ConnectivityResult.none],
      [ConnectivityResult.none, ConnectivityResult.vpn],
    ]);

    expect(await restoredFrom(changes).length, 1);
  });

  test('먼저 구독한 쪽이 끊김을 본 뒤에 구독한 쪽도 이어짐 신호를 받는다', () async {
    final connectivity = _FakeConnectivity();
    final watcher = ConnectivityNetworkWatcher(connectivity);

    final a = <void>[];
    final subA = watcher.restored.listen(a.add);

    connectivity._controller.add(const [ConnectivityResult.wifi]);
    await Future<void>.delayed(Duration.zero);
    connectivity._controller.add(const [ConnectivityResult.none]);
    await Future<void>.delayed(Duration.zero);

    final b = <void>[];
    final subB = watcher.restored.listen(b.add);

    connectivity._controller.add(const [ConnectivityResult.wifi]);
    await Future<void>.delayed(Duration.zero);

    expect(a.length, 1);
    expect(b.length, 1);

    await subA.cancel();
    await subB.cancel();
  });
}

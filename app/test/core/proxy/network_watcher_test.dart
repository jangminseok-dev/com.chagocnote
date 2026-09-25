import 'package:chagocnote/core/proxy/network_watcher.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_test/flutter_test.dart';

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
}

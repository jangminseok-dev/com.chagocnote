import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// "인터넷이 돌아왔다" 신호 — 대기열이 기다리지 않고 바로 다시 해 보게 한다(설계 10.2).
abstract class NetworkWatcher {
  /// 끊겼다가 다시 이어질 때마다 한 번.
  Stream<void> get restored;
}

class ConnectivityNetworkWatcher implements NetworkWatcher {
  ConnectivityNetworkWatcher([Connectivity? connectivity])
    : _connectivity = connectivity ?? Connectivity();

  final Connectivity _connectivity;

  @override
  Stream<void> get restored =>
      restoredFrom(_connectivity.onConnectivityChanged);
}

/// 연결 상태 변화에서 "끊김 → 이어짐"만 고른다. 처음 받은 상태는 신호가 아니다.
Stream<void> restoredFrom(Stream<List<ConnectivityResult>> changes) async* {
  var offline = false;
  await for (final results in changes) {
    final nowOffline = results.every((r) => r == ConnectivityResult.none);
    if (offline && !nowOffline) yield null;
    offline = nowOffline;
  }
}

final networkWatcherProvider = Provider<NetworkWatcher>(
  (ref) => ConnectivityNetworkWatcher(),
);

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

  // EventChannel 은 첫 Dart 구독자에게만 네이티브의 현재 상태를 준다. 업로드 대기열이
  // 앱에서 이미 그 첫 구독자라, 여기서 매번 새로 만들면 오류 뒤에야 구독하는 AsyncBody 는
  // 현재 상태를 못 받아 끊김을 놓친다. 그래서 끊김 추적을 앱에서 하나만 만들어 공유한다.
  @override
  late final Stream<void> restored = restoredFrom(
    _connectivity.onConnectivityChanged,
  ).asBroadcastStream();
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

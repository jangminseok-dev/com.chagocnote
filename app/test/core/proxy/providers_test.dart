import 'package:chagocnote/core/proxy/providers.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  // 타임아웃이 없으면 서버가 응답하지 않을 때 갱신·restore·signOut 이 수 분
  // 멈추고, 갱신 타임아웃 뒤 "다시 시도" 경로(S2)가 실기기에서 성립하지 않는다.
  for (final entry in <String, Provider<Dio>>{
    'dioProvider': dioProvider,
    'refreshDioProvider': refreshDioProvider,
  }.entries) {
    test('${entry.key} 는 연결 10초·수신 15초·송신 15초 타임아웃을 건다', () {
      final container = ProviderContainer.test();
      final options = container.read(entry.value).options;

      expect(options.connectTimeout, const Duration(seconds: 10));
      expect(options.receiveTimeout, const Duration(seconds: 15));
      expect(options.sendTimeout, const Duration(seconds: 15));
    });
  }
}

import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/proxy/upload_client.dart';
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

  test('uploadDioProvider 는 인터셉터가 없고 연결 타임아웃만 건다 — 송신 타임아웃은 큰 영상을 끊는다', () {
    final container = ProviderContainer.test();
    final dio = container.read(uploadDioProvider);

    expect(
      dio.interceptors.whereType<InterceptorsWrapper>(),
      isEmpty,
      reason: 'ApiClient 의 토큰 인터셉터(InterceptorsWrapper)가 붙으면 안 된다',
    );
    expect(dio.options.connectTimeout, const Duration(seconds: 10));
    expect(dio.options.sendTimeout, isNull);
  });

  test('uploadClientProvider 는 uploadDioProvider 의 Dio 를 쓴다', () {
    final container = ProviderContainer.test();
    expect(container.read(uploadClientProvider), isA<UploadClient>());
  });
}

import 'dart:convert';
import 'dart:typed_data';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/auth/api/auth_api.dart';
import 'package:chagocnote/features/auth/api/me_api.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session_gateway.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_http_client_adapter.dart';

const _meJson = {
  'id': 1,
  'display_name': '민석',
  'profile_image_url': null,
  'identities': ['apple'],
  'shops': <Map<String, dynamic>>[],
};

void main() {
  group('restore', () {
    test('저장된 리프레시 토큰이 없으면 HTTP 호출 없이 null 을 반환한다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        fail('토큰이 없는데 요청이 나갔다: ${options.path}');
      });
      final tokenStore = MemoryTokenStore();
      final gateway = _buildGateway(adapter: adapter, tokenStore: tokenStore);

      final me = await gateway.restore();

      expect(me, isNull);
      expect(adapter.requests, isEmpty);
    });

    test('토큰이 있으면 /v1/me 를 호출해 Me 를 반환한다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        expect(options.path, '/v1/me');
        return const FakeResponse(statusCode: 200, data: _meJson);
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'access-1', refresh: 'refresh-1');
      final gateway = _buildGateway(adapter: adapter, tokenStore: tokenStore);

      final me = await gateway.restore();

      expect(me?.displayName, '민석');
    });

    test('/v1/me 가 401, 리프레시도 401 이면 null 을 반환하고 토큰을 지운다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '리프레시 토큰 만료'},
          );
        }
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '액세스 토큰 만료'},
        );
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'also-expired');
      final gateway = _buildGateway(adapter: adapter, tokenStore: tokenStore);

      final me = await gateway.restore();

      expect(me, isNull);
      expect(await tokenStore.readAccess(), isNull);
      expect(await tokenStore.readRefresh(), isNull);
    });

    test('/v1/me 가 403 ACCOUNT_SUSPENDED 면 null 을 반환하고 토큰을 지운다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        return const FakeResponse(
          statusCode: 403,
          data: {'code': 'ACCOUNT_SUSPENDED', 'message': '정지된 계정'},
        );
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'access-1', refresh: 'refresh-1');
      final gateway = _buildGateway(adapter: adapter, tokenStore: tokenStore);

      final me = await gateway.restore();

      expect(me, isNull);
      expect(await tokenStore.readAccess(), isNull);
      expect(await tokenStore.readRefresh(), isNull);
    });

    test('연결 오류가 나면 NETWORK 예외를 다시 던지고 토큰은 그대로 둔다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        throw DioException.connectionTimeout(
          timeout: const Duration(seconds: 5),
          requestOptions: options,
        );
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'access-1', refresh: 'refresh-1');
      final gateway = _buildGateway(adapter: adapter, tokenStore: tokenStore);

      await expectLater(
        gateway.restore(),
        throwsA(isA<ApiException>().having((e) => e.code, 'code', 'NETWORK')),
      );
      expect(await tokenStore.readAccess(), 'access-1');
      expect(await tokenStore.readRefresh(), 'refresh-1');
    });
  });

  group('signIn', () {
    test(
      '토큰을 먼저 저장한 뒤 /v1/me 를 요청하고, '
      '/v1/auth/social 요청에는 인증 헤더가 없으며 빈 필드는 생략된다',
      () async {
        final adapter = FakeHttpClientAdapter((options, body) {
          if (options.path == '/v1/auth/social') {
            expect(options.headers.containsKey('Authorization'), isFalse);
            final payload = jsonDecode(utf8.decode(body!)) as Map;
            expect(payload.keys, {'provider', 'token'});
            expect(payload['provider'], 'apple');
            expect(payload['token'], 'id-token');
            return const FakeResponse(
              statusCode: 200,
              data: {
                'access_token': 'new-access',
                'refresh_token': 'new-refresh',
                'token_type': 'bearer',
                'expires_in': 3600,
                'user_id': 1,
                'is_new_user': false,
              },
            );
          }
          expect(options.path, '/v1/me');
          expect(options.headers['Authorization'], 'Bearer new-access');
          return const FakeResponse(statusCode: 200, data: _meJson);
        });
        final tokenStore = MemoryTokenStore();
        final gateway = _buildGateway(adapter: adapter, tokenStore: tokenStore);

        final me = await gateway.signIn(
          const SocialCredential(provider: 'apple', token: 'id-token'),
        );

        expect(me.displayName, '민석');
        expect(await tokenStore.readAccess(), 'new-access');
        expect(await tokenStore.readRefresh(), 'new-refresh');
      },
    );
  });

  group('signOut', () {
    test('저장된 리프레시 토큰으로 로그아웃을 호출하고 토큰·설정을 지운다', () async {
      Uint8List? logoutBody;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/logout') {
          logoutBody = body;
        }
        return const FakeResponse(statusCode: 204);
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'access-1', refresh: 'refresh-1');
      final prefsStore = MemoryPrefsStore()..writeLastShopId(9);
      final gateway = _buildGateway(
        adapter: adapter,
        tokenStore: tokenStore,
        prefsStore: prefsStore,
      );

      await gateway.signOut();

      expect(
        jsonDecode(utf8.decode(logoutBody!)),
        {'refresh_token': 'refresh-1'},
      );
      expect(await tokenStore.readAccess(), isNull);
      expect(await tokenStore.readRefresh(), isNull);
      expect(await prefsStore.readLastShopId(), isNull);
    });

    test('로그아웃 호출이 네트워크 오류로 실패해도 토큰·설정은 지워진다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        throw DioException.connectionTimeout(
          timeout: const Duration(seconds: 5),
          requestOptions: options,
        );
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'access-1', refresh: 'refresh-1');
      final prefsStore = MemoryPrefsStore()..writeLastShopId(9);
      final gateway = _buildGateway(
        adapter: adapter,
        tokenStore: tokenStore,
        prefsStore: prefsStore,
      );

      await gateway.signOut();

      expect(await tokenStore.readAccess(), isNull);
      expect(await tokenStore.readRefresh(), isNull);
      expect(await prefsStore.readLastShopId(), isNull);
    });
  });
}

HttpSessionGateway _buildGateway({
  required FakeHttpClientAdapter adapter,
  required TokenStore tokenStore,
  PrefsStore? prefsStore,
}) {
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final client = ApiClient(tokenStore: tokenStore, dio: dio, refreshDio: refreshDio);
  return HttpSessionGateway(
    authApi: AuthApi(client),
    meApi: MeApi(client),
    tokenStore: tokenStore,
    prefsStore: prefsStore ?? MemoryPrefsStore(),
  );
}

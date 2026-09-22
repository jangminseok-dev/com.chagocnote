import 'dart:convert';
import 'dart:typed_data';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_http_client_adapter.dart';

void main() {
  group('happy path', () {
    test('보호된 요청에는 저장된 액세스 토큰이 Authorization 헤더로 붙는다', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'old-access', refresh: 'old-refresh');
      final adapter = FakeHttpClientAdapter((options, body) {
        expect(options.headers['Authorization'], 'Bearer old-access');
        return const FakeResponse(statusCode: 200, data: {'ok': true});
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      final result = await client.get('/protected');

      expect(result, {'ok': true});
      expect(adapter.requests, hasLength(1));
    });

    test('public 요청에는 Authorization 헤더가 붙지 않는다', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'old-access', refresh: 'old-refresh');
      final adapter = FakeHttpClientAdapter((options, body) {
        expect(options.headers.containsKey('Authorization'), isFalse);
        return const FakeResponse(statusCode: 200, data: {'ok': true});
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      final result = await client.post(
        '/v1/auth/social',
        data: {'idToken': 'x'},
        public: true,
      );

      expect(result, {'ok': true});
    });
  });

  group('리프레시', () {
    test('401 UNAUTHENTICATED → 리프레시 → 원 요청 재시도 성공', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      var refreshCalls = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          refreshCalls++;
          final payload = jsonDecode(utf8.decode(body!)) as Map;
          expect(payload['refresh_token'], 'refresh-1');
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'new-access',
              'refresh_token': 'new-refresh',
              'token_type': 'bearer',
              'expires_in': 3600,
            },
          );
        }
        final auth = options.headers['Authorization'];
        if (auth == 'Bearer expired') {
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '토큰이 만료되었습니다.'},
          );
        }
        expect(auth, 'Bearer new-access');
        return const FakeResponse(statusCode: 200, data: {'ok': true});
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      final result = await client.get('/protected');

      expect(result, {'ok': true});
      expect(refreshCalls, 1);
      expect(await tokenStore.readAccess(), 'new-access');
      expect(await tokenStore.readRefresh(), 'new-refresh');
    });

    test('동시에 3개 요청이 401을 받아도 리프레시는 한 번만 나간다', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      var refreshCalls = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          refreshCalls++;
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'new-access',
              'refresh_token': 'new-refresh',
              'token_type': 'bearer',
              'expires_in': 3600,
            },
          );
        }
        final auth = options.headers['Authorization'];
        if (auth == 'Bearer expired') {
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '토큰이 만료되었습니다.'},
          );
        }
        return const FakeResponse(statusCode: 200, data: {'ok': true});
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      final results = await Future.wait([
        client.get('/protected'),
        client.get('/protected'),
        client.get('/protected'),
      ]);

      expect(results, everyElement({'ok': true}));
      expect(refreshCalls, 1);
    });

    test('재시도 요청이 다시 401을 받으면 에러로 끝나고 두 번째 리프레시는 없다', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      var refreshCalls = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          refreshCalls++;
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'new-access',
              'refresh_token': 'new-refresh',
              'token_type': 'bearer',
              'expires_in': 3600,
            },
          );
        }
        // 재시도해도 계속 401 (예: 다른 이유로 여전히 거부됨).
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '여전히 거부됨'},
        );
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      await expectLater(
        client.get('/protected'),
        throwsA(
          isA<ApiException>()
              .having((e) => e.code, 'code', 'UNAUTHENTICATED')
              .having((e) => e.statusCode, 'statusCode', 401),
        ),
      );
      expect(refreshCalls, 1);
    });

    test('리프레시가 401을 받으면 토큰을 지우고 onSessionEnded를 한 번만 부르며 원 요청들은 실패한다',
        () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'stolen-refresh');
      var sessionEndedCalls = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '리프레시 토큰 재사용 탐지'},
          );
        }
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '토큰이 만료되었습니다.'},
        );
      });
      final client = _buildClient(
        tokenStore: tokenStore,
        adapter: adapter,
        onSessionEnded: () => sessionEndedCalls++,
      );

      final expectations = [
        expectLater(
          client.get('/a'),
          throwsA(
            isA<ApiException>().having((e) => e.code, 'code', 'UNAUTHENTICATED'),
          ),
        ),
        expectLater(
          client.get('/b'),
          throwsA(
            isA<ApiException>().having((e) => e.code, 'code', 'UNAUTHENTICATED'),
          ),
        ),
        expectLater(
          client.get('/c'),
          throwsA(
            isA<ApiException>().having((e) => e.code, 'code', 'UNAUTHENTICATED'),
          ),
        ),
      ];
      await Future.wait(expectations);

      expect(sessionEndedCalls, 1);
      expect(await tokenStore.readAccess(), isNull);
      expect(await tokenStore.readRefresh(), isNull);
    });

    test('리프레시가 게이트웨이 오류(502·503·504)면 토큰을 지우지 않고 세션도 끝내지 않는다',
        () async {
      for (final status in [502, 503, 504]) {
        final tokenStore = MemoryTokenStore()
          ..save(access: 'expired', refresh: 'refresh-1');
        var refreshCalls = 0;
        var sessionEndedCalls = 0;
        final adapter = FakeHttpClientAdapter((options, body) {
          if (options.path == '/v1/auth/refresh') {
            refreshCalls++;
            return FakeResponse(statusCode: status, data: 'Bad Gateway');
          }
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '토큰이 만료되었습니다.'},
          );
        });
        final client = _buildClient(
          tokenStore: tokenStore,
          adapter: adapter,
          onSessionEnded: () => sessionEndedCalls++,
        );

        await expectLater(
          client.get('/protected'),
          throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', status)),
        );

        expect(refreshCalls, 1, reason: '$status');
        expect(sessionEndedCalls, 0, reason: '$status');
        expect(await tokenStore.readRefresh(), 'refresh-1', reason: '$status');
      }
    });

    test('리프레시가 500이면 토큰이 이미 소모됐을 수 있으므로 이 기기만 로그아웃한다', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      var sessionEndedCalls = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          return const FakeResponse(
            statusCode: 500,
            data: {'code': 'INTERNAL_ERROR', 'message': '서버 오류'},
          );
        }
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '토큰이 만료되었습니다.'},
        );
      });
      final client = _buildClient(
        tokenStore: tokenStore,
        adapter: adapter,
        onSessionEnded: () => sessionEndedCalls++,
      );

      await expectLater(client.get('/protected'), throwsA(isA<ApiException>()));

      expect(sessionEndedCalls, 1);
      expect(await tokenStore.readRefresh(), isNull);
    });

    test('리프레시가 타임아웃되면 토큰은 유지되고 원 요청은 NETWORK 에러로 끝나며 리프레시는 한 번만 나간다',
        () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      var refreshCalls = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          refreshCalls++;
          throw DioException.connectionTimeout(
            timeout: const Duration(seconds: 5),
            requestOptions: options,
          );
        }
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '토큰이 만료되었습니다.'},
        );
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      await expectLater(
        client.get('/protected'),
        throwsA(
          isA<ApiException>()
              .having((e) => e.code, 'code', 'NETWORK')
              .having((e) => e.isNetwork, 'isNetwork', isTrue),
        ),
      );

      expect(refreshCalls, 1);
      expect(await tokenStore.readAccess(), 'expired');
      expect(await tokenStore.readRefresh(), 'refresh-1');
    });
  });

  group('에러 바디 파싱', () {
    test('{code,message} JSON 바디는 그대로 ApiException으로 파싱된다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        return const FakeResponse(
          statusCode: 403,
          data: {'code': 'ACCOUNT_SUSPENDED', 'message': '정지된 계정입니다.'},
        );
      });
      final client = _buildClient(
        tokenStore: MemoryTokenStore(),
        adapter: adapter,
      );

      await expectLater(
        client.get('/x', public: true),
        throwsA(
          isA<ApiException>()
              .having((e) => e.statusCode, 'statusCode', 403)
              .having((e) => e.code, 'code', 'ACCOUNT_SUSPENDED')
              .having((e) => e.message, 'message', '정지된 계정입니다.'),
        ),
      );
    });

    test('JSON이 아닌 에러 바디는 HTTP_ERROR로 대체된다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        return const FakeResponse(statusCode: 500, data: 'internal error');
      });
      final client = _buildClient(
        tokenStore: MemoryTokenStore(),
        adapter: adapter,
      );

      await expectLater(
        client.get('/x', public: true),
        throwsA(
          isA<ApiException>()
              .having((e) => e.statusCode, 'statusCode', 500)
              .having((e) => e.code, 'code', 'HTTP_ERROR'),
        ),
      );
    });
  });

  group('DELETE 바디', () {
    test('DELETE 요청이 JSON 바디를 실제로 보낸다', () async {
      Uint8List? capturedBody;
      String? capturedContentType;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.method == 'DELETE') {
          capturedBody = body;
          capturedContentType = options.headers['content-type'] as String?;
        }
        return const FakeResponse(statusCode: 200, data: {'ok': true});
      });
      final client = _buildClient(
        tokenStore: MemoryTokenStore(),
        adapter: adapter,
      );

      final result = await client.delete(
        '/v1/auth/account',
        data: {'confirm_close_shops': true},
        public: true,
      );

      expect(result, {'ok': true});
      expect(capturedBody, isNotNull);
      expect(
        jsonDecode(utf8.decode(capturedBody!)),
        {'confirm_close_shops': true},
      );
      expect(capturedContentType, contains('application/json'));
    });
  });
}

ApiClient _buildClient({
  required TokenStore tokenStore,
  required FakeHttpClientAdapter adapter,
  void Function()? onSessionEnded,
}) {
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  return ApiClient(
    tokenStore: tokenStore,
    onSessionEnded: onSessionEnded,
    dio: dio,
    refreshDio: refreshDio,
  );
}

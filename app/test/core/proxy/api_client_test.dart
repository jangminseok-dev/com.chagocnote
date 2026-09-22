import 'dart:async';
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

  group('리프레시 — 검토 수정(fix round 1)', () {
    test(
        '갱신이 진행되는 동안 다른 경로로 세션이 끝나면(로그아웃) 갱신 응답이 늦게 와도 '
        '새 토큰을 저장하지 않는다', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'stolen-refresh');
      var sessionEndedCalls = 0;
      // 갱신 요청이 이미 옛 리프레시 토큰을 읽어 네트워크로 나간 뒤(=이
      // completer가 끝난 뒤)에만 로그아웃이 일어나게 해, "요청을 보낸 뒤
      // 응답을 받기 전에 세션이 끝난" 경합을 결정적으로 재현한다.
      final refreshRequested = Completer<void>();
      final refreshGate = Completer<void>();
      final adapter = FakeHttpClientAdapter((options, body) async {
        if (options.path == '/v1/auth/refresh') {
          refreshRequested.complete();
          await refreshGate.future;
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

      final pending = client.get('/protected');
      await refreshRequested.future;
      await tokenStore.clear();
      refreshGate.complete();

      await expectLater(
        pending,
        throwsA(
          isA<ApiException>().having((e) => e.code, 'code', 'UNAUTHENTICATED'),
        ),
      );
      expect(sessionEndedCalls, 0, reason: '세션을 끝낸 쪽이 이미 알렸다');
      expect(await tokenStore.readRefresh(), isNull);
      expect(await tokenStore.readAccess(), isNull);
    });

    test('갱신이 401로 끝난 뒤 이미 나가 있던 요청의 401이 늦게 와도 onSessionEnded는 합계 1번',
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

      // 첫 요청이 갱신을 마치고(세션 종료) 토큰을 지운 뒤에, 옛 토큰으로
      // 각각 온전히 끝날 때까지 순서대로 기다린다 — 단일 비행 필드가 매번
      // 초기화되므로, /b·/c는 /a가 이미 지운 토큰을 보고 "리프레시 토큰
      // 없음" 경로를 각자 새로 탄다. 이 경로가 매번 onSessionEnded를 부르면
      // 안 된다(이미 끝난 세션이다).
      for (final path in ['/a', '/b', '/c']) {
        await expectLater(
          client.get(path),
          throwsA(
            isA<ApiException>()
                .having((e) => e.code, 'code', 'UNAUTHENTICATED'),
          ),
        );
      }

      expect(sessionEndedCalls, 1);
    });

    test('리프레시 토큰이 없는 상태의 보호된 요청이 401을 받아도 onSessionEnded를 부르지 않는다',
        () async {
      final tokenStore = MemoryTokenStore();
      var sessionEndedCalls = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
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
        throwsA(
          isA<ApiException>().having((e) => e.code, 'code', 'UNAUTHENTICATED'),
        ),
      );

      expect(sessionEndedCalls, 0);
    });

    test('갱신이 타임아웃된 뒤 다음 요청은 갱신을 새로 시도한다(단일 비행 필드가 초기화된다)',
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

      await expectLater(client.get('/a'), throwsA(isA<ApiException>()));
      await expectLater(client.get('/b'), throwsA(isA<ApiException>()));

      expect(refreshCalls, 2);
    });

    test('갱신 성공 뒤 다시 401이 오면 두 번째 갱신이 나간다(단일 비행 필드가 초기화된다)',
        () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      var refreshCalls = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          refreshCalls++;
          return FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'access-$refreshCalls',
              'refresh_token': 'refresh-$refreshCalls',
              'token_type': 'bearer',
              'expires_in': 3600,
            },
          );
        }
        final auth = options.headers['Authorization'];
        if (auth == 'Bearer access-2') {
          return const FakeResponse(statusCode: 200, data: {'ok': true});
        }
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '토큰이 만료되었습니다.'},
        );
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      await expectLater(client.get('/a'), throwsA(isA<ApiException>()));
      final second = await client.get('/b');

      expect(second, {'ok': true});
      expect(refreshCalls, 2);
    });

    test(
        '갱신이 진행되는 동안 다른 경로가 새 토큰을 저장하고 갱신이 401로 끝나면, 새 토큰이 남고 '
        'onSessionEnded는 0번이며 원 요청은 새 토큰으로 재시도된다', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'stolen-refresh');
      var sessionEndedCalls = 0;
      // 갱신 요청이 옛 리프레시 토큰으로 이미 나간 뒤(=이 completer가 끝난
      // 뒤)에만 다른 경로(예: 로그인 수단 해제)가 새 토큰을 저장하게 해,
      // "갱신 응답을 기다리는 동안 다른 경로가 먼저 새 토큰을 저장한" 경합을
      // 결정적으로 재현한다.
      final refreshRequested = Completer<void>();
      final refreshGate = Completer<void>();
      final adapter = FakeHttpClientAdapter((options, body) async {
        if (options.path == '/v1/auth/refresh') {
          refreshRequested.complete();
          await refreshGate.future;
          // 서버가 이 갱신(옛 리프레시 토큰)은 거절한다 — 그사이 다른 경로가
          // 이미 새 토큰을 발급받아 저장했다.
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '리프레시 토큰 재사용 탐지'},
          );
        }
        final auth = options.headers['Authorization'];
        if (auth == 'Bearer new-access') {
          return const FakeResponse(statusCode: 200, data: {'ok': true});
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

      final pending = client.get('/protected');
      await refreshRequested.future;
      // 다른 경로(로그인 수단 해제 등)가 갱신 응답보다 먼저 새 토큰을 저장한다.
      await tokenStore.save(access: 'new-access', refresh: 'new-refresh');
      refreshGate.complete();

      final result = await pending;

      expect(result, {'ok': true});
      expect(sessionEndedCalls, 0);
      expect(await tokenStore.readAccess(), 'new-access');
      expect(await tokenStore.readRefresh(), 'new-refresh');
    });
  });

  group('리프레시 — 최종 검토 수정', () {
    test(
        '갱신 200 이 오는 동안 다른 경로가 새 토큰을 저장했으면, 갱신 응답을 저장하지 않고 '
        '원 요청을 새 토큰으로 한 번 재시도한다(E)', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      var sessionEndedCalls = 0;
      final refreshRequested = Completer<void>();
      final refreshGate = Completer<void>();
      final adapter = FakeHttpClientAdapter((options, body) async {
        if (options.path == '/v1/auth/refresh') {
          refreshRequested.complete();
          await refreshGate.future;
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'refreshed-access',
              'refresh_token': 'refreshed-refresh',
              'token_type': 'bearer',
              'expires_in': 3600,
            },
          );
        }
        final auth = options.headers['Authorization'];
        if (auth == 'Bearer other-access') {
          return const FakeResponse(statusCode: 200, data: {'ok': true});
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

      final pending = client.get('/protected');
      await refreshRequested.future;
      // 다른 경로(로그인 수단 해제 등)가 갱신 응답보다 먼저 새 토큰을 저장한다.
      await tokenStore.save(access: 'other-access', refresh: 'other-refresh');
      refreshGate.complete();

      final result = await pending;

      expect(result, {'ok': true});
      expect(sessionEndedCalls, 0);
      expect(await tokenStore.readAccess(), 'other-access');
      expect(await tokenStore.readRefresh(), 'other-refresh');
      final protectedRequests =
          adapter.requests.where((r) => r.path == '/protected').toList();
      expect(protectedRequests, hasLength(2));
      expect(
        protectedRequests.last.headers['Authorization'],
        'Bearer other-access',
      );
    });

    test(
        '갱신이 401 로 끝나는 동안 다른 경로가 세션을 끝냈으면(저장소 null) 헤더 없는 재시도를 '
        '보내지 않고 UNAUTHENTICATED 로 끝난다(E)', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      var sessionEndedCalls = 0;
      final refreshRequested = Completer<void>();
      final refreshGate = Completer<void>();
      final adapter = FakeHttpClientAdapter((options, body) async {
        if (options.path == '/v1/auth/refresh') {
          refreshRequested.complete();
          await refreshGate.future;
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

      final pending = client.get('/protected');
      await refreshRequested.future;
      await tokenStore.clear();
      refreshGate.complete();

      await expectLater(
        pending,
        throwsA(
          isA<ApiException>()
              .having((e) => e.code, 'code', 'UNAUTHENTICATED')
              .having((e) => e.sessionEnded, 'sessionEnded', isFalse),
        ),
      );
      expect(sessionEndedCalls, 0, reason: '세션을 끝낸 쪽이 이미 알렸다');
      expect(
        adapter.requests.where((r) => r.path == '/protected'),
        hasLength(1),
        reason: '헤더 없는 재시도가 나가면 안 된다',
      );
    });

    test('갱신이 401 로 세션을 끝내면 원 요청의 예외에 sessionEnded 가 실린다(B)', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      final adapter = FakeHttpClientAdapter((options, body) {
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '거절'},
        );
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      await expectLater(
        client.get('/protected'),
        throwsA(
          isA<ApiException>()
              .having((e) => e.statusCode, 'statusCode', 401)
              .having((e) => e.sessionEnded, 'sessionEnded', isTrue),
        ),
      );
    });

    test('갱신 없이 끝난 401(리프레시 토큰 없음)은 sessionEnded 가 false 다(B)', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '거절'},
        );
      });
      final client = _buildClient(tokenStore: MemoryTokenStore(), adapter: adapter);

      await expectLater(
        client.get('/protected'),
        throwsA(
          isA<ApiException>()
              .having((e) => e.statusCode, 'statusCode', 401)
              .having((e) => e.sessionEnded, 'sessionEnded', isFalse),
        ),
      );
    });

    test('갱신이 200 인데 본문에 토큰이 없으면 원 요청이 오류로 끝난다(F1 — 영원히 걸리지 않는다)',
        () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          return const FakeResponse(statusCode: 200, data: {'unexpected': true});
        }
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '토큰이 만료되었습니다.'},
        );
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      // dio 5.11 은 인터셉터 안의 비동기 예외를 스스로 붙잡지만, 그 결과는
      // 응답 없는 오류라 NETWORK 로 보인다(사용자에게 "연결을 확인하세요"가
      // 뜬다). ApiClient 가 직접 잡아 HTTP_ERROR 로 끝내야 한다.
      await expectLater(
        client.get('/protected').timeout(const Duration(seconds: 2)),
        throwsA(
          isA<ApiException>()
              .having((e) => e.code, 'code', 'HTTP_ERROR')
              .having((e) => e.sessionEnded, 'sessionEnded', isFalse),
        ),
      );
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

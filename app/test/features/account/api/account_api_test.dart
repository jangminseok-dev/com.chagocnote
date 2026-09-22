// AccountApi를 실제 네트워크 없이(FakeHttpClientAdapter) 검증한다. Riverpod은
// 필요 없다 — API 클래스 하나만 직접 구성해서 쓴다.
import 'dart:convert';
import 'dart:typed_data';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/account/api/account_api.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';

AccountApi _build(FakeHandler handle, {TokenStore? tokenStore}) {
  final adapter = FakeHttpClientAdapter(handle);
  // 리프레시 요청은 별도의 Dio 인스턴스로 보내야 한다 — 같은 인스턴스를
  // 재사용하면 인터셉터를 함께 타서, 리프레시 요청 자체가 401을 받았을 때
  // 다시 리프레시를 시도하는 재귀에 빠진다(`ApiClient`의 문서 주석 참고).
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = tokenStore ?? (MemoryTokenStore()
    ..save(access: 'old-access', refresh: 'old-refresh'));
  final client = ApiClient(tokenStore: store, dio: dio, refreshDio: refreshDio);
  return AccountApi(client: client, tokenStore: store);
}

void main() {
  group('link', () {
    test('display_name 없는 자격 증명은 그대로 본문으로 보내고 identities 를 돌려준다', () async {
      Map<String, dynamic>? sentBody;
      final api = _build((options, body) {
        sentBody = jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;
        return const FakeResponse(
          statusCode: 200,
          data: {
            'identities': ['apple', 'kakao'],
          },
        );
      });

      final identities = await api.link(
        const SocialCredential(provider: 'kakao', token: 'tok'),
      );

      expect(sentBody, {'provider': 'kakao', 'token': 'tok'});
      expect(identities, ['apple', 'kakao']);
    });

    test('display_name 이 있는 자격 증명은 연결 요청 본문에서 뺀다', () async {
      Map<String, dynamic>? sentBody;
      final api = _build((options, body) {
        sentBody = jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;
        return const FakeResponse(
          statusCode: 200,
          data: {
            'identities': ['apple'],
          },
        );
      });

      await api.link(
        const SocialCredential(
          provider: 'apple',
          token: 'tok',
          authorizationCode: 'code',
          nonce: 'nonce',
          displayName: '민석',
        ),
      );

      expect(sentBody, {
        'provider': 'apple',
        'token': 'tok',
        'authorization_code': 'code',
        'nonce': 'nonce',
      });
    });

    test('409 IDENTITY_ALREADY_LINKED 는 그대로 던진다', () async {
      final api = _build((options, body) {
        return const FakeResponse(
          statusCode: 409,
          data: {'code': 'IDENTITY_ALREADY_LINKED', 'message': '다른 계정'},
        );
      });

      await expectLater(
        api.link(const SocialCredential(provider: 'kakao', token: 'tok')),
        throwsA(
          isA<ApiException>().having((e) => e.code, 'code', 'IDENTITY_ALREADY_LINKED'),
        ),
      );
    });
  });

  group('unlink', () {
    test('응답의 새 토큰을 먼저 저장한 뒤 identities 를 돌려준다(S5)', () async {
      final store = MemoryTokenStore()
        ..save(access: 'old-access', refresh: 'old-refresh');
      final api = _build((options, body) {
        expect(options.method, 'DELETE');
        expect(options.path, '/v1/auth/identities/kakao');
        return const FakeResponse(
          statusCode: 200,
          data: {
            'identities': ['apple'],
            'access_token': 'new-access',
            'refresh_token': 'new-refresh',
            'token_type': 'Bearer',
            'expires_in': 3600,
          },
        );
      }, tokenStore: store);

      final identities = await api.unlink('kakao');

      expect(identities, ['apple']);
      expect(await store.readAccess(), 'new-access');
      expect(await store.readRefresh(), 'new-refresh');
    });

    test('404 IDENTITY_NOT_FOUND 는 토큰을 바꾸지 않고 그대로 던진다', () async {
      final store = MemoryTokenStore()
        ..save(access: 'old-access', refresh: 'old-refresh');
      final api = _build((options, body) {
        return const FakeResponse(
          statusCode: 404,
          data: {'code': 'IDENTITY_NOT_FOUND', 'message': '없음'},
        );
      }, tokenStore: store);

      await expectLater(
        api.unlink('kakao'),
        throwsA(isA<ApiException>().having((e) => e.code, 'code', 'IDENTITY_NOT_FOUND')),
      );
      expect(await store.readAccess(), 'old-access');
    });
  });

  group('withdraw', () {
    test('confirmCloseShops 가 false 면 본문 없이 보낸다', () async {
      Uint8List? sentBody;
      final api = _build((options, body) {
        expect(options.method, 'DELETE');
        expect(options.path, '/v1/auth/account');
        sentBody = body;
        return const FakeResponse(statusCode: 204);
      });

      await api.withdraw();

      expect(sentBody, isNull);
    });

    test('confirmCloseShops 가 true 면 JSON 불리언 본문을 보낸다', () async {
      Map<String, dynamic>? sentBody;
      String? contentType;
      final api = _build((options, body) {
        sentBody = jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;
        contentType = options.headers['content-type'] as String?;
        return const FakeResponse(statusCode: 204);
      });

      await api.withdraw(confirmCloseShops: true);

      expect(sentBody, {'confirm_close_shops': true});
      expect(contentType, contains('application/json'));
    });

    test('204 는 정상 종료다', () async {
      final api = _build((options, body) => const FakeResponse(statusCode: 204));
      await expectLater(api.withdraw(), completes);
    });

    test('401 은 이미 완료된 탈퇴로 보고 정상 종료한다(S12)', () async {
      final api = _build(
        (options, body) => const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '이미 탈퇴됨'},
        ),
      );

      await expectLater(api.withdraw(), completes);
    });

    test('409 OWNERSHIP_TRANSFER_REQUIRED 는 그대로 던진다', () async {
      final api = _build(
        (options, body) => const FakeResponse(
          statusCode: 409,
          data: {'code': 'OWNERSHIP_TRANSFER_REQUIRED', 'message': '소유권 이전 필요'},
        ),
      );

      await expectLater(
        api.withdraw(),
        throwsA(
          isA<ApiException>().having(
            (e) => e.code,
            'code',
            'OWNERSHIP_TRANSFER_REQUIRED',
          ),
        ),
      );
    });

    test('409 SHOP_CLOSE_CONFIRM_REQUIRED 는 그대로 던진다', () async {
      final api = _build(
        (options, body) => const FakeResponse(
          statusCode: 409,
          data: {'code': 'SHOP_CLOSE_CONFIRM_REQUIRED', 'message': '매장 닫힘 확인 필요'},
        ),
      );

      await expectLater(
        api.withdraw(),
        throwsA(
          isA<ApiException>().having(
            (e) => e.code,
            'code',
            'SHOP_CLOSE_CONFIRM_REQUIRED',
          ),
        ),
      );
    });
  });
}

// 순수 Dart 헬퍼라 SDK/플랫폼 채널 없이 바로 검증한다.
import 'package:chagocnote/features/auth/api/apple_nonce.dart';
import 'package:flutter_test/flutter_test.dart';

final _base64UrlSafe = RegExp(r'^[A-Za-z0-9_-]+$');

void main() {
  group('hashNonce', () {
    test('알려진 입력의 SHA-256 16진수 해시와 일치한다', () {
      expect(
        hashNonce('abc'),
        'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
      );
    });
  });

  group('newRawNonce', () {
    test('두 번 호출한 값은 서로 다르다', () {
      expect(newRawNonce(), isNot(newRawNonce()));
    });

    test('URL-safe 문자만 쓰고 패딩(=)이 없다', () {
      final raw = newRawNonce();
      expect(_base64UrlSafe.hasMatch(raw), isTrue);
      expect(raw.contains('='), isFalse);
    });

    test('32바이트를 base64url로 인코딩한 길이다(패딩 제외 43자)', () {
      expect(newRawNonce().length, 43);
    });
  });
}

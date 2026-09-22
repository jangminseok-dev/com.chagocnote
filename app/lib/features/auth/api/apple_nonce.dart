import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';

/// Apple 로그인의 재생 공격(replay attack) 방지용 nonce 헬퍼.
///
/// 서버는 `sha256(rawNonce).hexdigest() == idToken.nonce`를 검증한다 —
/// Apple에는 원문 nonce의 SHA-256 16진수 해시를 건네고([hashNonce]), 서버에는
/// 원문 nonce를 그대로 보낸다([newRawNonce]가 만든 값).

/// URL-safe한 원문 nonce를 만든다. `Random.secure()`로 뽑은 32바이트를
/// base64url로 인코딩하되, 패딩(`=`)은 뗀다.
String newRawNonce({int length = 32}) {
  final random = Random.secure();
  final bytes = Uint8List.fromList(
    List<int>.generate(length, (_) => random.nextInt(256)),
  );
  return base64Url.encode(bytes).replaceAll('=', '');
}

/// [raw] nonce의 SHA-256 16진수 해시.
String hashNonce(String raw) => sha256.convert(utf8.encode(raw)).toString();

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// 기기에 남기는 작은 설정. 키로 읽고 쓴다 — 항목이 늘어도 인터페이스와 구현 둘을
/// 고치지 않는다(설정마다 read/write 쌍을 늘리던 것을 대신한다).
///
/// 저장소 패키지를 늘리지 않으려고 보안 저장소를 같이 쓴다.
abstract class PrefsStore {
  Future<String?> read(String key);
  Future<void> write(String key, String value);

  /// 마지막으로 고른 매장을 지운다(로그아웃·탈퇴). 보기 방식 같은 기기 설정은 남긴다.
  Future<void> clear();
}

/// 잘 알려진 키. 새 설정은 여기에 키만 더한다.
abstract final class PrefsKeys {
  static const lastShopId = 'last_shop_id';

  /// 고객 목록 보기 방식('list' | 'grid').
  static const customerViewMode = 'customer_view_mode';

  /// 하루 화면 보기 방식('list' | 'timeline').
  static const dayViewMode = 'day_view_mode';
}

/// 마지막으로 고른 매장 — 정수로 읽고 쓴다.
extension LastShopPrefs on PrefsStore {
  Future<int?> readLastShopId() async =>
      int.tryParse(await read(PrefsKeys.lastShopId) ?? '');

  Future<void> writeLastShopId(int shopId) =>
      write(PrefsKeys.lastShopId, '$shopId');
}

class SecurePrefsStore implements PrefsStore {
  SecurePrefsStore([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  @override
  Future<String?> read(String key) => _storage.read(key: key);

  @override
  Future<void> write(String key, String value) =>
      _storage.write(key: key, value: value);

  @override
  Future<void> clear() => _storage.delete(key: PrefsKeys.lastShopId);
}

class MemoryPrefsStore implements PrefsStore {
  final _values = <String, String>{};

  @override
  Future<String?> read(String key) async => _values[key];

  @override
  Future<void> write(String key, String value) async => _values[key] = value;

  @override
  Future<void> clear() async => _values.remove(PrefsKeys.lastShopId);
}

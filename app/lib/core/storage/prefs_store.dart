import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// 기기에 남기는 작은 설정. 지금은 "마지막으로 고른 매장" 하나다.
///
/// 저장소 패키지를 늘리지 않으려고 보안 저장소를 같이 쓴다.
abstract class PrefsStore {
  Future<int?> readLastShopId();
  Future<void> writeLastShopId(int shopId);
  Future<void> clear();
}

class SecurePrefsStore implements PrefsStore {
  SecurePrefsStore([FlutterSecureStorage? storage])
      : _storage = storage ?? const FlutterSecureStorage();

  static const _lastShopKey = 'last_shop_id';
  final FlutterSecureStorage _storage;

  @override
  Future<int?> readLastShopId() async => int.tryParse(await _storage.read(key: _lastShopKey) ?? '');

  @override
  Future<void> writeLastShopId(int shopId) => _storage.write(key: _lastShopKey, value: '$shopId');

  @override
  Future<void> clear() => _storage.delete(key: _lastShopKey);
}

class MemoryPrefsStore implements PrefsStore {
  int? _lastShopId;

  @override
  Future<int?> readLastShopId() async => _lastShopId;

  @override
  Future<void> writeLastShopId(int shopId) async => _lastShopId = shopId;

  @override
  Future<void> clear() async => _lastShopId = null;
}

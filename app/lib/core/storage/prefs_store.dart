import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// 기기에 남기는 작은 설정. "마지막으로 고른 매장"과 "고객 목록·하루 화면 보기 방식"이다.
///
/// 저장소 패키지를 늘리지 않으려고 보안 저장소를 같이 쓴다.
abstract class PrefsStore {
  Future<int?> readLastShopId();
  Future<void> writeLastShopId(int shopId);

  /// 고객 목록 보기 방식('list' | 'grid'). 기기 설정이라 [clear]가 지우지 않는다.
  Future<String?> readCustomerViewMode();
  Future<void> writeCustomerViewMode(String mode);

  /// 하루 화면 보기 방식('list' | 'timeline'). 기기 설정이라 [clear]가 지우지 않는다.
  Future<String?> readDayViewMode();
  Future<void> writeDayViewMode(String mode);

  /// 마지막으로 고른 매장을 지운다(로그아웃·탈퇴).
  Future<void> clear();
}

class SecurePrefsStore implements PrefsStore {
  SecurePrefsStore([FlutterSecureStorage? storage])
      : _storage = storage ?? const FlutterSecureStorage();

  static const _lastShopKey = 'last_shop_id';
  static const _customerViewModeKey = 'customer_view_mode';
  static const _dayViewModeKey = 'day_view_mode';
  final FlutterSecureStorage _storage;

  @override
  Future<int?> readLastShopId() async => int.tryParse(await _storage.read(key: _lastShopKey) ?? '');

  @override
  Future<void> writeLastShopId(int shopId) => _storage.write(key: _lastShopKey, value: '$shopId');

  @override
  Future<String?> readCustomerViewMode() => _storage.read(key: _customerViewModeKey);

  @override
  Future<void> writeCustomerViewMode(String mode) =>
      _storage.write(key: _customerViewModeKey, value: mode);

  @override
  Future<String?> readDayViewMode() => _storage.read(key: _dayViewModeKey);

  @override
  Future<void> writeDayViewMode(String mode) =>
      _storage.write(key: _dayViewModeKey, value: mode);

  @override
  Future<void> clear() => _storage.delete(key: _lastShopKey);
}

class MemoryPrefsStore implements PrefsStore {
  int? _lastShopId;
  String? _customerViewMode;
  String? _dayViewMode;

  @override
  Future<int?> readLastShopId() async => _lastShopId;

  @override
  Future<void> writeLastShopId(int shopId) async => _lastShopId = shopId;

  @override
  Future<String?> readCustomerViewMode() async => _customerViewMode;

  @override
  Future<void> writeCustomerViewMode(String mode) async => _customerViewMode = mode;

  @override
  Future<String?> readDayViewMode() async => _dayViewMode;

  @override
  Future<void> writeDayViewMode(String mode) async => _dayViewMode = mode;

  @override
  Future<void> clear() async => _lastShopId = null;
}

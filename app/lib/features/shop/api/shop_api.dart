import '../../../core/proxy/api_client.dart';

/// 매장 멤버 한 명.
class ShopMember {
  const ShopMember({
    required this.memberId,
    required this.userId,
    required this.displayName,
    required this.profileImageUrl,
    required this.role,
    required this.joinedAt,
  });

  factory ShopMember.fromJson(Map<String, dynamic> json) => ShopMember(
        memberId: json['member_id'] as int,
        userId: json['user_id'] as int,
        displayName: json['display_name'] as String,
        profileImageUrl: json['profile_image_url'] as String?,
        role: json['role'] as String,
        joinedAt: DateTime.parse(json['joined_at'] as String),
      );

  final int memberId;
  final int userId;
  final String displayName;
  final String? profileImageUrl;

  /// 'owner' | 'staff'
  final String role;
  final DateTime joinedAt;

  bool get isOwner => role == 'owner';
}

/// 새로 만든 초대 코드. 코드 값이 로그에 찍히지 않도록 `toString`을
/// 오버라이드하지 않는다.
class CreatedInvite {
  const CreatedInvite({
    required this.code,
    required this.role,
    required this.expiresAt,
  });

  factory CreatedInvite.fromJson(Map<String, dynamic> json) => CreatedInvite(
        code: json['code'] as String,
        role: json['role'] as String,
        expiresAt: DateTime.parse(json['expires_at'] as String),
      );

  final String code;
  final String role;
  final DateTime expiresAt;
}

/// 매장 정보.
class ShopSettings {
  const ShopSettings({
    required this.shopId,
    required this.name,
    required this.businessType,
    required this.phone,
    required this.address,
    required this.timezone,
  });

  factory ShopSettings.fromJson(Map<String, dynamic> json) => ShopSettings(
        shopId: json['shop_id'] as int,
        name: json['name'] as String,
        businessType: json['business_type'] as String,
        phone: json['phone'] as String?,
        address: json['address'] as String?,
        timezone: json['timezone'] as String,
      );

  final int shopId;
  final String name;
  final String businessType;
  final String? phone;
  final String? address;
  final String timezone;
}

/// 매장 범위 API — 멤버 관리, 초대, 매장 정보.
class ShopApi {
  ShopApi(this._client);

  final ApiClient _client;

  Future<List<ShopMember>> members(int shopId) async {
    final data = await _client.get('/v1/shops/$shopId/members') as List;
    return data
        .map((e) => ShopMember.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<CreatedInvite> createInvite(int shopId) async {
    final data =
        await _client.post('/v1/shops/$shopId/invites') as Map<String, dynamic>;
    return CreatedInvite.fromJson(data);
  }

  Future<void> changeRole(int shopId, int memberId, String role) {
    return _client.patch(
      '/v1/shops/$shopId/members/$memberId',
      data: {'role': role},
    );
  }

  Future<void> removeMember(int shopId, int memberId) {
    return _client.delete('/v1/shops/$shopId/members/$memberId');
  }

  Future<ShopSettings> settings(int shopId) async {
    final data = await _client.get('/v1/shops/$shopId/settings')
        as Map<String, dynamic>;
    return ShopSettings.fromJson(data);
  }

  Future<ShopSettings> updateSettings(
    int shopId, {
    required String name,
    String? phone,
    String? address,
  }) async {
    final data = await _client.put(
      '/v1/shops/$shopId/settings',
      data: {'name': name, 'phone': phone, 'address': address},
    ) as Map<String, dynamic>;
    return ShopSettings.fromJson(data);
  }
}

import '../../../core/proxy/api_client.dart';

/// 초대 코드 수락 결과.
class InviteAccepted {
  const InviteAccepted({
    required this.shopId,
    required this.shopName,
    required this.role,
    required this.memberId,
  });

  factory InviteAccepted.fromJson(Map<String, dynamic> json) =>
      InviteAccepted(
        shopId: json['shop_id'] as int,
        shopName: json['shop_name'] as String,
        role: json['role'] as String,
        memberId: json['member_id'] as int,
      );

  final int shopId;
  final String shopName;
  final String role;
  final int memberId;
}

/// 초대 코드 수락 API.
class InviteApi {
  InviteApi(this._client);

  final ApiClient _client;

  Future<InviteAccepted> accept(String code) async {
    final data = await _client.post(
      '/v1/invites/accept',
      data: {'code': code},
    ) as Map<String, dynamic>;
    return InviteAccepted.fromJson(data);
  }
}

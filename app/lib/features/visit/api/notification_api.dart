import '../../../core/proxy/api_client.dart';
import 'notification_models.dart';

/// 알림톡 API(⑥ 설계 7절, 결정 기록 009 의 계약). 경로는 모두 `/v1/shops/{shopId}` 아래다.
class NotificationApi {
  NotificationApi(this._client);

  final ApiClient _client;

  NotificationOverview _overview(Object? data) =>
      NotificationOverview.fromJson(data as Map<String, dynamic>);

  /// 채널 상태·설정·종류별 템플릿 상태. 소속이면 읽는다.
  Future<NotificationOverview> overview(int shopId) async =>
      _overview(await _client.get('/v1/shops/$shopId/notification'));

  /// 채널 관리자의 카카오톡으로 인증번호를 보낸다. 입력값은 서버도 저장하지 않는다 — 연동 때 다시 보낸다.
  Future<void> requestChannelToken(
    int shopId, {
    required String searchId,
    required String adminPhone,
    required String categoryCode,
  }) async {
    await _client.post(
      '/v1/shops/$shopId/notification/channel/token',
      data: {
        'search_id': searchId,
        'admin_phone': adminPhone,
        'category_code': categoryCode,
      },
    );
  }

  /// 인증번호로 채널을 연동한다. 설정 기본값과 템플릿 다섯이 함께 생긴다.
  Future<NotificationOverview> linkChannel(
    int shopId, {
    required String searchId,
    required String adminPhone,
    required String categoryCode,
    required String token,
  }) async => _overview(
    await _client.post(
      '/v1/shops/$shopId/notification/channel',
      data: {
        'search_id': searchId,
        'admin_phone': adminPhone,
        'category_code': categoryCode,
        'token': token,
      },
    ),
  );

  /// 연동 해제 — 예정된 알림이 모두 취소된다.
  Future<void> unlinkChannel(int shopId) async {
    await _client.delete('/v1/shops/$shopId/notification/channel');
  }

  /// 설정 전체 교체(아홉 칸 — `NotificationOverview.settingsBody`).
  Future<NotificationOverview> updateSettings(
    int shopId,
    Map<String, dynamic> body,
  ) async => _overview(
    await _client.put('/v1/shops/$shopId/notification/settings', data: body),
  );

  /// 문자 대체의 발신번호로 인증번호를 보낸다.
  Future<void> requestSenderVerification(int shopId, String phone) async {
    await _client.post(
      '/v1/shops/$shopId/notification/sender/verification',
      data: {'phone': phone},
    );
  }

  Future<NotificationOverview> confirmSender(
    int shopId, {
    required String phone,
    required String code,
  }) async => _overview(
    await _client.post(
      '/v1/shops/$shopId/notification/sender',
      data: {'phone': phone, 'code': code},
    ),
  );

  /// 방문의 알림 줄, 최신순. 다른 매장·없는 방문이면 빈 목록이다(404 가 아니다).
  Future<List<NotificationMessage>> forVisit(int shopId, int visitId) async =>
      NotificationMessage.listFromJson(
        await _client.get('/v1/shops/$shopId/visits/$visitId/notifications')
            as Map<String, dynamic>,
      );

  /// 그 종류의 가장 최근 줄을 지금 다시 보낸다. 새 줄의 ID.
  Future<int> resend(int shopId, int visitId, NotificationKind kind) async {
    final created =
        await _client.post(
              '/v1/shops/$shopId/visits/$visitId/notifications/${kind.wire}/resend',
            )
            as Map<String, dynamic>;
    return created['message_id'] as int;
  }

  /// 줄 하나의 지금 상태. 모르는 종류·상태면 null.
  Future<NotificationMessage?> message(int shopId, int messageId) async =>
      NotificationMessage.tryFromJson(
        await _client.get('/v1/shops/$shopId/notifications/$messageId')
            as Map<String, dynamic>,
      );
}

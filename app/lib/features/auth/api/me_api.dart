import '../../../core/proxy/api_client.dart';
import '../state/session.dart';

/// 로그인한 사용자 본인 정보를 가져오는 API.
class MeApi {
  MeApi(this._client);

  final ApiClient _client;

  Future<Me> fetch() async {
    final data = await _client.get('/v1/me') as Map<String, dynamic>;
    return Me.fromJson(data);
  }
}

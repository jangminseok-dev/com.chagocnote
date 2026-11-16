import '../../../core/proxy/api_client.dart';
import 'consent_models.dart';
import 'form_settings_models.dart';

/// 서류 설정 API(⑪-B). 읽기는 매장 멤버, 바꾸기는 사장(`shop:update`)이다.
class FormSettingsApi {
  FormSettingsApi(this._client);

  final ApiClient _client;

  Future<FormSettings> settings(int shopId) async =>
      FormSettings.fromJson(await _client.get('/v1/shops/$shopId/form-settings') as Map<String, dynamic>);

  /// 전체 교체. 범위 밖의 값·규칙에 어긋난 글은 422.
  Future<FormSettings> updateSettings(int shopId, FormSettings settings) async => FormSettings.fromJson(
    await _client.put('/v1/shops/$shopId/form-settings', data: settings.toJson()) as Map<String, dynamic>,
  );

  /// 동의서의 토막 셋 — 문서의 순서.
  Future<List<ConsentTextPart>> consentTexts(int shopId) async {
    final data = await _client.get('/v1/shops/$shopId/consent-texts') as Map<String, dynamic>;
    return [for (final raw in data['parts'] as List) ?ConsentTextPart.tryParse(raw)];
  }

  /// 토막의 글을 고친다. [body] 가 `null` 이면 기본 글로 되돌린다. 그 뒤의 서명부터 새 글이다.
  Future<ConsentTextPart> updateConsentText(int shopId, ConsentPart part, String? body) async =>
      ConsentTextPart.tryParse(
        await _client.put('/v1/shops/$shopId/consent-texts/${part.name}', data: {'body': body}),
      )!;
}

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/plugs/care_marks_plug.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/consent_models.dart';
import '../api/form_settings_api.dart';
import '../api/form_settings_models.dart';
import 'consent_providers.dart';
import 'form_settings_providers.dart';

/// 서류 설정 쓰기(⑪-B) — 기준값·보내는 글, 동의서의 글.
///
/// **성공하든 실패하든** 설정을 다시 읽게 한다 — 화면은 낙관적으로 그리지 않고 다시 읽은 값으로 그린다.
/// 기준값(노령 나이·동의 기한)이 바뀌면 방문의 "확인할 것"이 달라지므로 방문 쪽에도 알린다.
class FormSettingsCommands {
  FormSettingsCommands(this._ref);

  final Ref _ref;

  FormSettingsApi get _api => _ref.read(formSettingsApiProvider);

  Future<FormSettings> update(int shopId, FormSettings settings) async {
    try {
      return await runShopScoped(_ref, () => _api.updateSettings(shopId, settings));
    } finally {
      _ref.invalidate(formSettingsProvider);
      _ref.invalidate(consentDocumentProvider);
      _ref.read(careMarksChangedPlugProvider)();
    }
  }

  /// 토막의 글을 고친다. [body] 가 `null` 이면 기본 글로 되돌린다.
  Future<ConsentTextPart> updateText(int shopId, ConsentPart part, String? body) async {
    try {
      return await runShopScoped(_ref, () => _api.updateConsentText(shopId, part, body));
    } finally {
      _ref.invalidate(consentTextsProvider);
      _ref.invalidate(consentDocumentProvider);
    }
  }
}

final formSettingsCommandsProvider = Provider<FormSettingsCommands>(FormSettingsCommands.new);

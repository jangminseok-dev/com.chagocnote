import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/form_settings_api.dart';
import '../api/form_settings_models.dart';

final formSettingsApiProvider = Provider<FormSettingsApi>((ref) => FormSettingsApi(ref.watch(apiClientProvider)));

/// 매장의 서류 설정. 바꾸면 `FormSettingsCommands` 가 다시 읽게 한다.
final formSettingsProvider = FutureProvider.autoDispose.family<FormSettings, int>(
  (ref, shopId) => runShopScoped(ref, () => ref.read(formSettingsApiProvider).settings(shopId)),
);

/// 동의서의 토막 셋 — 지금 글과 기본 글.
final consentTextsProvider = FutureProvider.autoDispose.family<List<ConsentTextPart>, int>(
  (ref, shopId) => runShopScoped(ref, () => ref.read(formSettingsApiProvider).consentTexts(shopId)),
);

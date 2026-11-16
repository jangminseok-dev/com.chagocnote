import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/report_api.dart';
import '../api/report_models.dart';
import 'visit_providers.dart';

final reportApiProvider = Provider<ReportApi>(
  (ref) => ReportApi(ref.watch(apiClientProvider)),
);

/// 알림장 미리보기. 보내기·끊기·설정 변경이 끝나면 `ReportCommands`가 다시 불러오게 한다.
final visitReportProvider = FutureProvider.autoDispose
    .family<VisitReportPreview, VisitKey>(
      (ref, key) => runShopScoped(
        ref,
        () => ref.read(reportApiProvider).preview(key.shopId, key.visitId),
      ),
    );

final reportSettingsProvider = FutureProvider.autoDispose
    .family<ReportSettings, int>(
      (ref, shopId) => runShopScoped(
        ref,
        () => ref.read(reportApiProvider).settings(shopId),
      ),
    );

/// 가족과 함께 보기 설정(⑫) — 알림장 설정 화면이 알림장 설정과 따로 읽는다.
final guardianSettingsProvider = FutureProvider.autoDispose
    .family<GuardianSettings, int>(
      (ref, shopId) => runShopScoped(
        ref,
        () => ref.read(reportApiProvider).guardianSettings(shopId),
      ),
    );

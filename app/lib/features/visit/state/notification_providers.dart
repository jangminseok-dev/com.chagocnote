import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/notification_api.dart';
import '../api/notification_models.dart';
import 'visit_providers.dart';

final notificationApiProvider = Provider<NotificationApi>(
  (ref) => NotificationApi(ref.watch(apiClientProvider)),
);

/// 알림톡 한눈에 보기(채널·설정·템플릿). 설정·연동 쓰기가 끝나면 `NotificationCommands`가 다시 불러오게
/// 한다.
final notificationOverviewProvider = FutureProvider.autoDispose
    .family<NotificationOverview, int>(
      (ref, shopId) => runShopScoped(
        ref,
        () => ref.read(notificationApiProvider).overview(shopId),
      ),
    );

/// 방문의 알림 줄(최신순). **방문 상세를 따라 다시 읽는다** — 예약 변경·취소·당겨 새로고침이 상세를
/// 무효화하면 내역도 따라온다(알림 줄은 방문의 이벤트로 생기고 거둬진다).
final visitNotificationsProvider = FutureProvider.autoDispose
    .family<List<NotificationMessage>, VisitKey>((ref, key) async {
      await ref.watch(visitDetailProvider(key).future);
      return runShopScoped(
        ref,
        () =>
            ref.read(notificationApiProvider).forVisit(key.shopId, key.visitId),
      );
    });

/// 결과를 다시 보기 전의 기다림(1초). 테스트가 바꿔 끼운다.
final notificationPollWaitProvider = Provider<Future<void> Function()>(
  (ref) =>
      () => Future<void>.delayed(const Duration(seconds: 1)),
);

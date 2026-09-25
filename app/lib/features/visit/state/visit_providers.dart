import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/media_api.dart';
import '../api/visit_api.dart';
import '../api/visit_models.dart';

final mediaApiProvider = Provider<MediaApi>(
  (ref) => MediaApi(ref.watch(apiClientProvider)),
);

final visitApiProvider = Provider<VisitApi>(
  (ref) => VisitApi(ref.watch(apiClientProvider)),
);

typedef DayKey = ({int shopId, DateTime date});
typedef MonthKey = ({int shopId, DateTime month});
typedef VisitKey = ({int shopId, int visitId});
typedef MenusKey = ({int shopId, bool includeArchived});

/// 시간 칸 조회 조건. [exclude]는 옮길 방문 ID 를 쉼표로 이은 문자열이다 —
/// 목록은 값으로 비교되지 않아 family 키가 매번 달라진다.
typedef SlotsKey = ({
  int shopId,
  DateTime date,
  int duration,
  String? at,
  String exclude,
});

/// 모든 조회는 화면을 떠나면 버리고(autoDispose) 매장 범위 공통 처리를 거친다.
/// 쓰기가 끝나면 `VisitCommands`가 다시 불러오게 한다.
final dayVisitsProvider = FutureProvider.autoDispose.family<DayVisits, DayKey>(
  (ref, key) => runShopScoped(
    ref,
    () => ref.read(visitApiProvider).day(key.shopId, key.date),
  ),
);

/// 월 요약. 키의 [MonthKey.month]는 그달 1일이어야 한다([monthKeyOf]).
final calendarMonthProvider = FutureProvider.autoDispose
    .family<CalendarMonth, MonthKey>(
      (ref, key) => runShopScoped(
        ref,
        () => ref.read(visitApiProvider).calendar(key.shopId, key.month),
      ),
    );

MonthKey monthKeyOf(int shopId, DateTime date) =>
    (shopId: shopId, month: DateTime(date.year, date.month));

final visitSlotsProvider = FutureProvider.autoDispose
    .family<VisitSlots, SlotsKey>(
      (ref, key) => runShopScoped(
        ref,
        () => ref
            .read(visitApiProvider)
            .slots(
              key.shopId,
              date: key.date,
              durationMinutes: key.duration,
              at: key.at,
              exclude: [
                for (final id in key.exclude.split(','))
                  if (id.isNotEmpty) int.parse(id),
              ],
            ),
      ),
    );

/// 카톡 글의 해석(③-A3). 글이 키다 — 같은 글은 한 번만 묻고, 화면을 떠나면
/// 버린다. 서버는 저장하지 않는다.
final visitDraftProvider = FutureProvider.autoDispose
    .family<VisitDraft, ({int shopId, String text})>(
      (ref, key) => runShopScoped(
        ref,
        () => ref.read(visitApiProvider).parseDraft(key.shopId, key.text),
      ),
    );

final visitDetailProvider = FutureProvider.autoDispose
    .family<VisitDetail, VisitKey>(
      (ref, key) => runShopScoped(
        ref,
        () => ref.read(visitApiProvider).detail(key.shopId, key.visitId),
      ),
    );

final visitSettingsProvider = FutureProvider.autoDispose
    .family<VisitSettings, int>(
      (ref, shopId) =>
          runShopScoped(ref, () => ref.read(visitApiProvider).settings(shopId)),
    );

final menusProvider = FutureProvider.autoDispose.family<List<Menu>, MenusKey>(
  (ref, key) => runShopScoped(
    ref,
    () => ref
        .read(visitApiProvider)
        .menus(key.shopId, includeArchived: key.includeArchived),
  ),
);

/// 오늘부터 1년 안의 임시 휴무.
final closedDatesProvider = FutureProvider.autoDispose
    .family<List<ClosedDate>, ({int shopId, DateTime from})>(
      (ref, key) => runShopScoped(
        ref,
        () => ref
            .read(visitApiProvider)
            .closedDates(
              key.shopId,
              from: key.from,
              to: DateTime(key.from.year + 1, key.from.month, key.from.day),
            ),
      ),
    );

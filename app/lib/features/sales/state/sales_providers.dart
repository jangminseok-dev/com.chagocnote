import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../../../core/time/shop_time.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/sales_api.dart';
import '../api/sales_models.dart';

final salesApiProvider = Provider<SalesApi>(
  (ref) => SalesApi(ref.watch(apiClientProvider)),
);

/// 요약 조회 조건. [anchor]는 `2026-11-14` 꼴의 글자다 — 값으로 비교되게.
typedef SalesKey = ({int shopId, SalesSpan span, String anchor});

/// 기간의 매출 요약. 화면을 떠나면 버린다(autoDispose) — 돌아오면 새로 읽는다.
final salesSummaryProvider = FutureProvider.autoDispose
    .family<SalesSummary, SalesKey>(
      (ref, key) => runShopScoped(
        ref,
        () => ref
            .read(salesApiProvider)
            .summary(key.shopId, key.span, parseDay(key.anchor)),
      ),
    );

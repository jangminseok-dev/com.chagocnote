import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/customer_api.dart';
import '../api/customer_models.dart';

final customerApiProvider = Provider<CustomerApi>(
  (ref) => CustomerApi(ref.watch(apiClientProvider)),
);

typedef PetKey = ({int shopId, int petId});
typedef CustomerKey = ({int shopId, int customerId});

/// 반려동물 상세. 화면을 떠나면 버린다(autoDispose) — 오류에 갇히지 않게 한다.
/// 쓰기가 끝나면 `CustomerCommands`가 다시 불러오게 한다.
final petDetailProvider = FutureProvider.autoDispose.family<PetDetail, PetKey>(
  (ref, key) => runShopScoped(
    ref,
    () => ref.read(customerApiProvider).pet(key.shopId, key.petId),
  ),
);

/// 고객 상세(전체 번호가 들어 있는 유일한 조회). 반려동물 상세의 보호자 탭과
/// 보호자 수정 화면이 쓴다.
final customerDetailProvider = FutureProvider.autoDispose
    .family<CustomerDetail, CustomerKey>(
      (ref, key) => runShopScoped(
        ref,
        () =>
            ref.read(customerApiProvider).customer(key.shopId, key.customerId),
      ),
    );

/// 고객 카드의 보호자 계정 연결. 반려동물 상세의 보호자 탭이 고객 상세와 따로
/// 읽는다 — 읽지 못해도 탭의 나머지는 그대로 보인다.
final guardianLinkProvider = FutureProvider.autoDispose
    .family<GuardianLink, CustomerKey>(
      (ref, key) => runShopScoped(
        ref,
        () => ref
            .read(customerApiProvider)
            .guardianLink(key.shopId, key.customerId),
      ),
    );

/// 정해진 질병 종류(칩 순서대로).
final conditionTypesProvider = FutureProvider.autoDispose
    .family<List<ConditionType>, int>(
      (ref, shopId) => runShopScoped(
        ref,
        () => ref.read(customerApiProvider).conditionTypes(shopId),
      ),
    );

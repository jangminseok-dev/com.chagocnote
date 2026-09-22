import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shop/state/shop_errors.dart';
import '../api/customer_api.dart';
import '../api/customer_models.dart';
import 'customer_list_controller.dart';
import 'customer_providers.dart';

/// 고객·반려동물 쓰기와 번호 조회. 모든 호출은 매장 범위 공통 처리
/// (`NOT_A_MEMBER` → 내 정보 재조회)를 거친다.
///
/// 쓰기가 끝나면 보고 있는 목록과 상세를 다시 불러오게 한다. 지운 대상의
/// 상세는 다시 부르지 않는다 — 부르면 404 가 화면에 잠깐 보인다.
class CustomerCommands {
  CustomerCommands(this._ref);

  final Ref _ref;

  CustomerApi get _api => _ref.read(customerApiProvider);

  Future<CustomerLookup?> lookup(int shopId, String phoneDigits) =>
      runShopScoped(_ref, () => _api.lookup(shopId, phoneDigits));

  Future<CustomerDetail> register(
    int shopId, {
    required CustomerFields customer,
    required PetFields pet,
  }) => _write(() => _api.register(shopId, customer: customer, pet: pet));

  Future<CustomerDetail> updateCustomer(
    int shopId,
    int customerId,
    CustomerFields fields,
  ) => _write(() => _api.updateCustomer(shopId, customerId, fields));

  Future<PetDetail> addPet(int shopId, int customerId, PetFields fields) =>
      _write(() => _api.addPet(shopId, customerId, fields));

  Future<PetDetail> updatePet(int shopId, int petId, PetFields fields) =>
      _write(() => _api.updatePet(shopId, petId, fields));

  Future<PetDetail> markPassedAway(int shopId, int petId) =>
      _write(() => _api.markPassedAway(shopId, petId));

  Future<PetDetail> unmarkPassedAway(int shopId, int petId) =>
      _write(() => _api.unmarkPassedAway(shopId, petId));

  /// 반려동물 삭제. 지운 아이의 상세는 다시 부르지 않고, 보호자 상세는 다시 부른다.
  Future<void> deletePet(int shopId, int petId) =>
      _write(() => _api.deletePet(shopId, petId), refreshPets: false);

  /// 고객 익명화 삭제. 그 고객의 상세는 모두 사라지므로 목록만 다시 부른다.
  Future<void> deleteCustomer(int shopId, int customerId) => _write(
    () => _api.deleteCustomer(shopId, customerId),
    refreshPets: false,
    refreshCustomers: false,
  );

  Future<T> _write<T>(
    Future<T> Function() action, {
    bool refreshPets = true,
    bool refreshCustomers = true,
  }) async {
    final result = await runShopScoped(_ref, action);
    _ref.invalidate(customerListControllerProvider);
    if (refreshPets) _ref.invalidate(petDetailProvider);
    if (refreshCustomers) _ref.invalidate(customerDetailProvider);
    return result;
  }
}

final customerCommandsProvider = Provider<CustomerCommands>(
  (ref) => CustomerCommands(ref),
);

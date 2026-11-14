import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/plugs/care_marks_plug.dart';
import '../../auth/state/shop_scoped.dart';
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

  /// 반려동물 삭제. 지운 아이의 상세는 다시 부르지 않고, 보호자 상세는 다시
  /// 부른다. `siblingIds`(지운 아이를 뺀 같은 보호자의 다른 아이)의 상세도
  /// 하나씩 다시 부른다 — 그 상세 화면의 "같은 보호자의 아이" 목록이 지운
  /// 아이를 계속 들고 있지 않게 한다.
  Future<void> deletePet(
    int shopId,
    int petId, {
    Iterable<int> siblingIds = const [],
  }) async {
    final result = await _write(
      () => _api.deletePet(shopId, petId),
      refreshPetDetails: false,
    );
    for (final siblingId in siblingIds) {
      _ref.invalidate(petDetailProvider((shopId: shopId, petId: siblingId)));
    }
    return result;
  }

  /// 고객 익명화 삭제. 그 고객의 상세는 모두 사라지므로 목록만 다시 부른다.
  Future<void> deleteCustomer(int shopId, int customerId) => _write(
    () => _api.deleteCustomer(shopId, customerId),
    refreshPetDetails: false,
    refreshCustomerDetails: false,
  );

  /// 매장이 보호자 연결을 끊는다. 성공하든 실패하든 그 고객의 연결을 다시
  /// 읽게 한다 — 보호자가 먼저 끊었을 수 있다(404). 목록·상세는 바뀌지 않는다.
  Future<void> endGuardianLink(int shopId, int customerId) async {
    try {
      await runShopScoped(
        _ref,
        () => _api.endGuardianLink(shopId, customerId),
      );
    } finally {
      _ref.invalidate(
        guardianLinkProvider((shopId: shopId, customerId: customerId)),
      );
    }
  }

  /// 미용 동의서를 받았다고 적는다(③-B). [receivedOn]이 없으면 오늘이다.
  Future<PetDetail> setGroomingConsent(
    int shopId,
    int petId, {
    DateTime? receivedOn,
  }) => _careWrite(
    () => _api.setGroomingConsent(shopId, petId, receivedOn: receivedOn),
  );

  Future<PetDetail> clearGroomingConsent(int shopId, int petId) =>
      _careWrite(() => _api.clearGroomingConsent(shopId, petId));

  /// 주의 고객으로 표시한다. 사유는 다듬은 한 줄(`cleanCautionReason`)이다.
  Future<CustomerDetail> setCaution(int shopId, int customerId, String reason) =>
      _careWrite(() => _api.setCaution(shopId, customerId, reason));

  Future<CustomerDetail> clearCaution(int shopId, int customerId) =>
      _careWrite(() => _api.clearCaution(shopId, customerId));

  /// 동의·주의 쓰기. **성공하든 실패하든** 목록·상세를 다시 읽고 방문 쪽에 알린다 — 다른
  /// 기기가 먼저 바꿨을 수 있고, 방문의 "확인할 것"이 이 값으로 정해진다.
  Future<T> _careWrite<T>(Future<T> Function() action) async {
    try {
      return await runShopScoped(_ref, action);
    } finally {
      _ref.invalidate(customerListControllerProvider);
      _ref.invalidate(petDetailProvider);
      _ref.invalidate(customerDetailProvider);
      _ref.read(careMarksChangedPlugProvider)();
    }
  }

  Future<T> _write<T>(
    Future<T> Function() action, {
    bool refreshPetDetails = true,
    bool refreshCustomerDetails = true,
  }) async {
    final result = await runShopScoped(_ref, action);
    _ref.invalidate(customerListControllerProvider);
    if (refreshPetDetails) _ref.invalidate(petDetailProvider);
    if (refreshCustomerDetails) _ref.invalidate(customerDetailProvider);
    return result;
  }
}

final customerCommandsProvider = Provider<CustomerCommands>(
  (ref) => CustomerCommands(ref),
);

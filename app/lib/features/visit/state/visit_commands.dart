import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../customer/api/consent_models.dart';
import '../../customer/state/consent_commands.dart';
import '../../customer/state/consent_providers.dart';
import '../../customer/state/customer_commands.dart';
import '../../customer/state/customer_list_controller.dart';
import '../../customer/state/customer_providers.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/record_models.dart';
import '../api/visit_api.dart';
import '../api/visit_models.dart';
import 'feed_controller.dart';
import 'visit_providers.dart';

/// 방문·일정·메뉴 쓰기. 모든 호출은 매장 범위 공통 처리(`NOT_A_MEMBER` →
/// 내 정보 재조회)를 거친다.
///
/// 방문 쓰기는 **성공하든 실패하든** 하루 목록·월 요약·상세·시간 칸을 다시
/// 불러오게 한다 — 낙관적 갱신을 하지 않고, 409 가 나면 화면이 서버와 어긋나
/// 있다는 뜻이라 새로 읽어야 한다(설계 9.2). 고객 쪽(목록의 최근 방문순, 고객
/// 상세의 노쇼 횟수·다가오는 예약)도 방문에 따라 바뀌므로 함께 다시 부른다.
class VisitCommands {
  VisitCommands(this._ref);

  final Ref _ref;

  VisitApi get _api => _ref.read(visitApiProvider);

  Future<SavedVisits> register(int shopId, VisitRequest request) =>
      _visitWrite(() => _api.register(shopId, request));

  Future<SavedVisits> update(int shopId, int visitId, VisitUpdate update) =>
      _visitWrite(() => _api.update(shopId, visitId, update));

  Future<SavedVisits> reschedule(
    int shopId, {
    required List<int> visitIds,
    required String startsAt,
  }) => _visitWrite(
    () => _api.reschedule(shopId, visitIds: visitIds, startsAt: startsAt),
  );

  Future<List<Visit>> transition(
    int shopId, {
    required List<int> visitIds,
    required VisitAction action,
    String? cancelReason,
  }) => _visitWrite(
    () => _api.transition(
      shopId,
      visitIds: visitIds,
      action: action,
      cancelReason: cancelReason,
    ),
  );

  /// 기록 저장(전체 교체). 몸무게가 반려동물의 현재 몸무게로 넘어갈 수 있어 고객 쪽도 다시 부른다.
  Future<VisitRecord> saveRecord(int shopId, int visitId, RecordInput input) =>
      _visitWrite(() => _api.putRecord(shopId, visitId, input));

  Future<void> deleteRecord(int shopId, int visitId) =>
      _visitWrite(() => _api.deleteRecord(shopId, visitId));

  /// "지난번처럼" — 반려동물을 고를 때 한 번 읽는다(다시 부르지 않는다).
  Future<VisitDefaults> defaults(int shopId, int petId) =>
      runShopScoped(_ref, () => _api.defaults(shopId, petId));

  /// 다음 예약 초안(저장하지 않는다 — 읽기라 아무것도 다시 부르지 않는다).
  Future<NextVisitDraft> nextDraft(int shopId, int visitId) =>
      runShopScoped(_ref, () => _api.nextDraft(shopId, visitId));

  /// 카톡 초안(저장하지 않는다 — 읽기라 아무것도 다시 부르지 않는다).
  Future<VisitDraft> parseDraft(int shopId, String text) =>
      runShopScoped(_ref, () => _api.parseDraft(shopId, text));

  Future<VisitSettings> updateSettings(int shopId, VisitSettings settings) =>
      _scheduleWrite(() => _api.updateSettings(shopId, settings));

  Future<ClosedDate> addClosedDate(int shopId, DateTime date, {String? note}) =>
      _scheduleWrite(() => _api.addClosedDate(shopId, date, note: note));

  Future<void> deleteClosedDate(int shopId, DateTime date) =>
      _scheduleWrite(() => _api.deleteClosedDate(shopId, date));

  Future<Menu> createMenu(
    int shopId, {
    required String name,
    int? defaultDurationMinutes,
    int? price,
  }) => _menuWrite(
    () => _api.createMenu(
      shopId,
      name: name,
      defaultDurationMinutes: defaultDurationMinutes,
      price: price,
    ),
  );

  Future<Menu> updateMenu(
    int shopId,
    int menuId, {
    required String name,
    required int? defaultDurationMinutes,
    required int sortOrder,
    required int? price,
  }) => _menuWrite(
    () => _api.updateMenu(
      shopId,
      menuId,
      name: name,
      defaultDurationMinutes: defaultDurationMinutes,
      sortOrder: sortOrder,
      price: price,
    ),
  );

  Future<Menu> archiveMenu(int shopId, int menuId) =>
      _menuWrite(() => _api.archiveMenu(shopId, menuId));

  /// 방문 상세의 [받았어요] — 그 아이의 미용 동의를 오늘로 적는다(③-B). 쓰기는 customer 의
  /// 명령이 하고(목록·상세를 다시 읽는다), 여기서는 성공하든 실패하든 확인할 것을 다시 읽는다.
  Future<void> consentReceived(int shopId, int petId) async {
    try {
      await _ref.read(customerCommandsProvider).setGroomingConsent(shopId, petId);
    } finally {
      _ref.invalidate(visitDetailProvider);
      _ref.invalidate(dayVisitsProvider);
      _ref.invalidate(visitChecksProvider);
    }
  }

  /// 방문 상세의 [동의서 보내기] — 그 아이의 동의서 링크를 만든다(있으면 같은 링크, ⑪). [forDate] 는 방문의
  /// 날이다 — 그날에 유효한 동의를 받는다. 성공하든 실패하든 확인할 것을 다시 읽는다(보낸 날이 실린다).
  Future<FormLink> consentFormLink(int shopId, int petId, {required DateTime forDate}) async {
    try {
      return await _ref.read(consentCommandsProvider).send(shopId, [petId], forDate: forDate);
    } finally {
      refreshChecks();
    }
  }

  /// 보호자에게 보낼 글의 토막들(⑪-B). 동의서 링크가 이때 만들어질 수 있다 — 성공하든 실패하든 확인할 것
  /// (보낸 날)과 보낸 서류를 다시 읽는다.
  Future<SendBundle> sendBundle(int shopId, int visitId) async {
    try {
      return await runShopScoped(_ref, () => _api.sendBundle(shopId, visitId));
    } finally {
      refreshChecks();
      _ref.invalidate(sentFormsProvider);
    }
  }

  /// 보낼 것 시트를 보내지 않고 닫았을 때 — 그 시트가 새로 만든 동의서 링크를 끊는다. 실패해도 조용히 끝난다
  /// (링크가 남을 뿐이다 — 보낸 서류에서 끊을 수 있다).
  Future<void> dropUnsentLink(int shopId, int formId) async {
    try {
      await _ref.read(consentCommandsProvider).revoke(shopId, formId);
    } catch (_) {
      // 알리지 않는다 — 사장이 한 일이 아니다.
    } finally {
      refreshChecks();
    }
  }

  /// 확인할 것을 다시 읽는다 — 서명 화면에서 돌아왔을 때.
  void refreshChecks() {
    _ref.invalidate(visitDetailProvider);
    _ref.invalidate(dayVisitsProvider);
    _ref.invalidate(visitChecksProvider);
  }

  Future<T> _visitWrite<T>(Future<T> Function() action) async {
    try {
      return await runShopScoped(_ref, action);
    } finally {
      _ref.invalidate(dayVisitsProvider);
      _ref.invalidate(calendarMonthProvider);
      _ref.invalidate(visitDetailProvider);
      _ref.invalidate(visitSlotsProvider);
      _ref.invalidate(feedControllerProvider);
      _ref.invalidate(customerListControllerProvider);
      _ref.invalidate(customerDetailProvider);
      // 프로필 사진은 가장 최근 완료 기록의 대표 사진이다.
      _ref.invalidate(petDetailProvider);
    }
  }

  /// 영업시간·쉬는 요일·임시 휴무는 시간 칸의 경고와 달력·하루의 휴무 표시를 바꾼다.
  Future<T> _scheduleWrite<T>(Future<T> Function() action) async {
    final result = await runShopScoped(_ref, action);
    _ref.invalidate(visitSettingsProvider);
    _ref.invalidate(closedDatesProvider);
    _ref.invalidate(visitSlotsProvider);
    _ref.invalidate(dayVisitsProvider);
    _ref.invalidate(calendarMonthProvider);
    return result;
  }

  Future<T> _menuWrite<T>(Future<T> Function() action) async {
    final result = await runShopScoped(_ref, action);
    _ref.invalidate(menusProvider);
    return result;
  }
}

final visitCommandsProvider = Provider<VisitCommands>(
  (ref) => VisitCommands(ref),
);

import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/plugs/care_marks_plug.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/consent_api.dart';
import '../api/consent_models.dart';
import 'consent_providers.dart';
import 'customer_providers.dart';

/// 동의서 쓰기 — 보내기·끊기·현장 서명. 모든 호출은 매장 범위 공통 처리를 거친다.
///
/// **성공하든 실패하든** 보낸 서류·반려동물 상세·고객 상세를 다시 읽고 방문 쪽에 알린다 —
/// 방문의 "확인할 것"(동의 줄과 보낸 날)이 이 값으로 정해지고, 실패했더라도 서버에는 반영됐을 수 있다.
class ConsentCommands {
  ConsentCommands(this._ref);

  final Ref _ref;

  ConsentApi get _api => _ref.read(consentApiProvider);

  /// 동의서 링크를 만든다(있으면 같은 링크). [forDate] 는 예약 날이다.
  Future<FormLink> send(int shopId, List<int> petIds, {DateTime? forDate}) =>
      _write(() => _api.issue(shopId, petIds, forDate: forDate));

  Future<void> revoke(int shopId, int formId) => _write(() => _api.revoke(shopId, formId));

  /// 현장 서명. 문서를 읽을 때 준 [forDate] 를 그대로 준다.
  Future<int> signInShop(
    int shopId, {
    required List<int> petIds,
    required String digest,
    required String signerName,
    required Uint8List png,
    DateTime? forDate,
  }) => _write(
    () => _api.signInShop(shopId, petIds: petIds, digest: digest, signerName: signerName, png: png, forDate: forDate),
  );

  Future<T> _write<T>(Future<T> Function() action) async {
    try {
      return await runShopScoped(_ref, action);
    } finally {
      _ref.invalidate(sentFormsProvider);
      _ref.invalidate(petSignaturesProvider);
      _ref.invalidate(petDetailProvider);
      _ref.invalidate(customerDetailProvider);
      _ref.read(careMarksChangedPlugProvider)();
    }
  }
}

final consentCommandsProvider = Provider<ConsentCommands>(ConsentCommands.new);

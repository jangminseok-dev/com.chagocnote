import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/shop_scoped.dart';
import '../api/consent_models.dart';
import '../api/intake_api.dart';
import '../api/intake_models.dart';
import 'consent_providers.dart';
import 'intake_providers.dart';

/// 문진표 쓰기(⑪-C) — 보내기, 받은 답 지우기, 매장이 더한 질문.
///
/// **성공하든 실패하든** 보이는 목록을 다시 읽게 한다 — 실패했더라도 서버에는 반영됐을 수 있고, 다른 기기가
/// 먼저 바꿨을 수 있다. 답으로 등록·반영하는 일은 `CustomerCommands`(등록·아이 더하기·아이 고치기)가 한다.
class IntakeCommands {
  IntakeCommands(this._ref);

  final Ref _ref;

  IntakeApi get _api => _ref.read(intakeApiProvider);

  /// 문진표 링크를 만든다. 둘 다 없으면 새 손님용, [customerId] 면 그 고객의 새 아이, [petId] 면 그 아이의 정보를
  /// 다시 받는다. 보낸 서류에 줄이 생긴다.
  Future<FormLink> send(int shopId, {int? customerId, int? petId}) async {
    try {
      return await runShopScoped(_ref, () => _api.issue(shopId, customerId: customerId, petId: petId));
    } finally {
      _ref.invalidate(sentFormsProvider);
    }
  }

  /// 받은 문진표를 등록하지 않고 지운다.
  Future<void> deleteAnswer(int shopId, int answerId) async {
    try {
      await runShopScoped(_ref, () => _api.deleteAnswer(shopId, answerId));
    } finally {
      _ref.invalidate(receivedIntakeProvider);
      _ref.invalidate(intakeAnswerProvider);
    }
  }

  /// 질문의 목록 전체를 바꾼다. 열려 있던 링크는 다음에 열 때 새 구성이다.
  Future<List<IntakeQuestion>> updateQuestions(int shopId, List<IntakeQuestion> questions) async {
    try {
      return await runShopScoped(_ref, () => _api.updateQuestions(shopId, questions));
    } finally {
      _ref.invalidate(intakeQuestionsProvider);
    }
  }
}

final intakeCommandsProvider = Provider<IntakeCommands>(IntakeCommands.new);

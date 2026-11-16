import '../../../core/proxy/api_client.dart';
import 'consent_models.dart';
import 'intake_models.dart';

/// 첫 방문 문진표 API(⑪-C). 경로는 모두 `/v1/shops/{shopId}` 아래다.
///
/// 받은 문진표는 고객 정보에 저절로 들어가지 않는다 — 등록·아이 더하기·아이 고치기(`CustomerApi`)가
/// `intakeAnswerId` 를 함께 보내면 서버가 같은 처리 안에서 그 답을 지운다.
class IntakeApi {
  IntakeApi(this._client);

  final ApiClient _client;

  /// 문진표 링크를 만든다. 둘 다 없으면 새 손님용(늘 새 링크), [customerId] 면 그 고객의 새 아이,
  /// [petId] 면 그 아이의 정보를 다시 받는다(둘은 살아 있는 링크가 있으면 같은 것이 온다).
  Future<FormLink> issue(int shopId, {int? customerId, int? petId}) async => FormLink.fromJson(
    await _client.post('/v1/shops/$shopId/intake-forms', data: {'customer_id': customerId, 'pet_id': petId})
        as Map<String, dynamic>,
  );

  /// 받은 문진표 — 아직 등록하지 않은 답, 받은 시각 내림차순.
  Future<List<IntakeAnswerItem>> answers(int shopId) async {
    final data = await _client.get('/v1/shops/$shopId/intake-answers') as Map<String, dynamic>;
    return [for (final raw in data['items'] as List) ?IntakeAnswerItem.tryParse(raw)];
  }

  /// 한 장. 이미 등록했거나 지웠거나 보관 기간이 지났으면 404 `INTAKE_ANSWER_NOT_FOUND`.
  Future<IntakeAnswer> answer(int shopId, int answerId) async => IntakeAnswer.fromJson(
    await _client.get('/v1/shops/$shopId/intake-answers/$answerId') as Map<String, dynamic>,
  );

  Future<void> deleteAnswer(int shopId, int answerId) async {
    await _client.delete('/v1/shops/$shopId/intake-answers/$answerId');
  }

  /// 매장이 더한 질문 — 정한 순서대로.
  Future<List<IntakeQuestion>> questions(int shopId) async {
    final data = await _client.get('/v1/shops/$shopId/intake-questions') as Map<String, dynamic>;
    return [for (final raw in data['items'] as List) ?IntakeQuestion.tryParse(raw)];
  }

  /// 질문의 목록 전체를 바꾼다. 빠진 질문은 지운 것이다. 5개·100자·빈 글은 422.
  Future<List<IntakeQuestion>> updateQuestions(int shopId, List<IntakeQuestion> questions) async {
    final data =
        await _client.put(
              '/v1/shops/$shopId/intake-questions',
              data: {'items': [for (final q in questions) q.toJson()]},
            )
            as Map<String, dynamic>;
    return [for (final raw in data['items'] as List) ?IntakeQuestion.tryParse(raw)];
  }
}

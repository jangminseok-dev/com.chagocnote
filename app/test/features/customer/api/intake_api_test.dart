// IntakeApi 와 모델을 실제 네트워크 없이 검증한다 — 경로, 본문, 응답 해석, 모양이 깨진 줄.
import 'dart:convert';
import 'dart:typed_data';

import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/customer/api/consent_models.dart';
import 'package:chagocnote/features/customer/api/customer_api.dart';
import 'package:chagocnote/features/customer/api/customer_models.dart';
import 'package:chagocnote/features/customer/api/intake_api.dart';
import 'package:chagocnote/features/customer/api/intake_models.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/consent_fixtures.dart';
import '../../../support/customer_fixtures.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/intake_fixtures.dart';

({ApiClient client, FakeHttpClientAdapter adapter}) _build(FakeHandler handle) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = MemoryTokenStore()..save(access: 'a', refresh: 'r');
  return (client: ApiClient(tokenStore: store, dio: dio, refreshDio: refreshDio), adapter: adapter);
}

Map<String, dynamic> _bodyOf(Uint8List? body) => jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;

const _pet = PetFields(
  name: '모카', species: 'dog', breed: '푸들', sex: 'male', neutered: false, birthDate: null, birthYear: 2022,
  weightKg: 4.5, noKnownConditions: true, conditions: [], memo: null,
);

void main() {
  test('문진표를 보낸다 — 새 손님·새 아이·다시 받기', () async {
    final bodies = <Map<String, dynamic>>[];
    final s = _build((o, b) {
      bodies.add(_bodyOf(b));
      return FakeResponse(statusCode: 201, data: formLinkJson(url: fakeIntakeUrl));
    });
    final api = IntakeApi(s.client);

    final link = await api.issue(3);
    await api.issue(3, customerId: 7);
    await api.issue(3, petId: 11);

    expect('${s.adapter.requests.first.method} ${s.adapter.requests.first.path}', 'POST /v1/shops/3/intake-forms');
    expect(bodies, [
      {'customer_id': null, 'pet_id': null},
      {'customer_id': 7, 'pet_id': null},
      {'customer_id': null, 'pet_id': 11},
    ]);
    expect(link.url, fakeIntakeUrl);
  });

  test('받은 문진표의 목록 — 모르는 보내는 곳·모양이 깨진 줄은 버리고 나머지는 보인다', () async {
    final s = _build((o, b) => FakeResponse(statusCode: 200, data: {
      'items': [
        intakeItemJson(),
        intakeItemJson(answerId: 52, mode: 'later_mode'),
        {'answer_id': '깨진 것'},
        intakeItemJson(answerId: 53, mode: 'update', petName: '콩이', guardianName: null, petId: 11,
            matchedCustomer: {'customer_id': 7, 'name': '김민지'}),
      ],
    }));

    final items = await IntakeApi(s.client).answers(3);

    expect(s.adapter.requests.single.path, '/v1/shops/3/intake-answers');
    expect([for (final i in items) (i.answerId, i.mode)], [(51, IntakeMode.newGuest), (53, IntakeMode.update)]);
    expect((items[0].petName, items[0].guardianName, items[0].submittedOn, items[0].matchedCustomer),
        ('모카', '박새롬', DateTime(2026, 11, 16), null));
    expect((items[1].matchedCustomer?.customerId, items[1].matchedCustomer?.name, items[1].petId), (7, '김민지', 11));
  });

  test('받은 문진표 한 장 — 답 전부와 빈 필수 칸·메모 초안', () async {
    final s = _build((o, b) => FakeResponse(statusCode: 200, data: intakeAnswerJson(
      breed: null, weightKg: null, noKnownConditions: false,
      conditions: [{'type_code': 'heart_disease', 'label': '심장 질환', 'custom_label': null, 'note': '약 복용 중'}],
      extras: [{'label': '산책은 얼마나 하나요?', 'body': '하루 한 번'}],
      missing: ['breed', 'weight'], memoOver: 12,
    )));

    final answer = await IntakeApi(s.client).answer(3, 51);

    expect(s.adapter.requests.single.path, '/v1/shops/3/intake-answers/51');
    expect((answer.guardianPhone, answer.species, answer.breed, answer.sex, answer.neutered), (
      '010-9999-0000', 'dog', null, 'male', false));
    expect((answer.birthDate, answer.birthYear, answer.birthUnknown, answer.weightKg), (null, 2022, false, null));
    expect([for (final c in answer.conditions) (c.typeCode, c.label, c.note)], [('heart_disease', '심장 질환', '약 복용 중')]);
    expect(answer.extras.single, (label: '산책은 얼마나 하나요?', body: '하루 한 번'));
    expect(answer.missing, ['breed', 'weight']);
    expect((answer.memoOver, answer.memoDraft.contains('드라이기')), (12, true));
  });

  test('지우기와 매장이 더한 질문', () async {
    final calls = <String>[];
    Map<String, dynamic>? sent;
    final s = _build((o, b) {
      calls.add('${o.method} ${o.path}');
      if (o.method == 'DELETE') return const FakeResponse(statusCode: 204);
      if (o.method == 'PUT') sent = _bodyOf(b);
      return FakeResponse(statusCode: 200, data: {'items': [intakeQuestionJson(7, '산책은 얼마나 하나요?', required: true)]});
    });
    final api = IntakeApi(s.client);

    await api.deleteAnswer(3, 51);
    final questions = await api.questions(3);
    await api.updateQuestions(3, [
      questions.single,
      const IntakeQuestion(questionId: null, label: '간식은요?', required: false),
    ]);

    expect(calls, ['DELETE /v1/shops/3/intake-answers/51', 'GET /v1/shops/3/intake-questions',
      'PUT /v1/shops/3/intake-questions']);
    expect((questions.single.questionId, questions.single.label, questions.single.required), (7, '산책은 얼마나 하나요?', true));
    expect(sent, {
      'items': [
        {'question_id': 7, 'label': '산책은 얼마나 하나요?', 'required': true},
        {'question_id': null, 'label': '간식은요?', 'required': false},
      ],
    });
  });

  test('등록·아이 더하기·아이 고치기는 답의 번호를 함께 보낸다 — 없으면 칸이 없다', () async {
    final bodies = <Map<String, dynamic>>[];
    final s = _build((o, b) {
      bodies.add(_bodyOf(b));
      return FakeResponse(statusCode: 200, data: o.path.endsWith('/customers')
          ? customerDetailJson() : petDetailJson());
    });
    final api = CustomerApi(s.client);
    const customer = CustomerFields(name: '박새롬', phone: '01099990000', phoneAlt: null, marketingConsent: false, memo: null);

    await api.register(3, customer: customer, pet: _pet, intakeAnswerId: 51);
    await api.addPet(3, 7, _pet, intakeAnswerId: 52);
    await api.updatePet(3, 11, _pet, intakeAnswerId: 53);
    await api.addPet(3, 7, _pet);

    expect([for (final b in bodies) b['intake_answer_id']], [51, 52, 53, null]);
    expect(bodies.last.containsKey('intake_answer_id'), isFalse);
    expect(bodies.first['pet'], isA<Map<String, dynamic>>());
  });

  test('보낸 서류는 문진표도 싣는다 — 새 손님용은 고객이 없고, 모양이 깨진 줄은 버린다', () {
    final forms = SentForm.listFrom([
      sentFormJson(),
      {...sentFormJson(formId: 32, url: fakeIntakeUrl), 'kind': 'intake', 'mode': 'new', 'customer': null, 'pets': []},
      {...sentFormJson(formId: 33), 'kind': 'intake', 'mode': 'update'},
      {'form_id': 34},
      {...sentFormJson(formId: 35), 'kind': 'later_kind'},
    ]);

    expect([for (final f in forms) (f.formId, f.kind, f.mode)], [
      (31, FormKind.consent, null), (32, FormKind.intake, IntakeMode.newGuest), (33, FormKind.intake, IntakeMode.update)]);
    expect((forms[1].customerId, forms[1].customerName), (null, null));
    expect(forms[1].pets, isEmpty);
    expect(forms[0].customerName, '김민지');
  });
}

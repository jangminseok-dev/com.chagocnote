// ConsentApi 와 모델을 실제 네트워크 없이(FakeHttpClientAdapter) 검증한다 — 경로, 본문, 질의, 응답 해석.
import 'dart:convert';
import 'dart:typed_data';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/customer/api/consent_api.dart';
import 'package:chagocnote/features/customer/api/consent_models.dart';
import 'package:chagocnote/features/customer/api/customer_models.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/consent_fixtures.dart';
import '../../../support/customer_fixtures.dart';
import '../../../support/fake_http_client_adapter.dart';

({ConsentApi api, FakeHttpClientAdapter adapter}) _build(FakeHandler handle) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = MemoryTokenStore()..save(access: 'a', refresh: 'r');
  final client = ApiClient(tokenStore: store, dio: dio, refreshDio: refreshDio);
  return (api: ConsentApi(client), adapter: adapter);
}

Map<String, dynamic> _bodyOf(Uint8List? body) => jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;

void main() {
  test('동의서를 보낸다 — 경로와 본문, 예약 날을 주면 함께 보낸다', () async {
    final bodies = <Map<String, dynamic>>[];
    final s = _build((o, b) {
      bodies.add(_bodyOf(b));
      return FakeResponse(statusCode: 201, data: formLinkJson());
    });

    final link = await s.api.issue(3, [11, 12]);
    await s.api.issue(3, [11], forDate: DateTime(2026, 11, 20, 15));

    expect('${s.adapter.requests.first.method} ${s.adapter.requests.first.path}', 'POST /v1/shops/3/consent-forms');
    expect(bodies, [
      {'pet_ids': [11, 12]},
      {'pet_ids': [11], 'for_date': '2026-11-20'},
    ]);
    expect((link.formId, link.url), (31, fakeConsentUrl));
    expect((link.expiresOn, link.sentOn), (DateTime(2026, 11, 30), DateTime(2026, 11, 16)));
  });

  test('이미 받은 동의면 code 가 그대로 온다', () async {
    final s = _build(
      (o, b) => const FakeResponse(statusCode: 409, data: {'code': 'CONSENT_UP_TO_DATE', 'message': '이미 받은 동의입니다.'}),
    );

    await expectLater(
      s.api.issue(3, [11]),
      throwsA(isA<ApiException>().having((e) => e.code, 'code', 'CONSENT_UP_TO_DATE')),
    );
  });

  test('보낸 서류를 읽고 끊는다', () async {
    final s = _build(
      (o, b) => o.method == 'DELETE'
          ? const FakeResponse(statusCode: 204)
          : FakeResponse(statusCode: 200, data: {
              'items': [
                sentFormJson(pets: const [(11, '콩이'), (12, '보리')]),
              ],
            }),
    );

    final forms = await s.api.forms(3);
    await s.api.revoke(3, 31);

    expect(s.adapter.requests.map((r) => '${r.method} ${r.path}'), ['GET /v1/shops/3/forms', 'DELETE /v1/shops/3/forms/31']);
    final form = forms.single;
    expect((form.formId, form.customerName, form.url), (31, '김민지', fakeConsentUrl));
    expect(form.pets.map((p) => (p.petId, p.name)), [(11, '콩이'), (12, '보리')]);
    expect((form.sentOn, form.expiresOn), (DateTime(2026, 11, 16), DateTime(2026, 11, 30)));
  });

  test('현장 서명의 문서를 읽는다 — 아이는 질의에 하나씩, 토막은 문서의 순서로', () async {
    final s = _build((o, b) => FakeResponse(statusCode: 200, data: consentDocumentJson(previousConsentOn: '2026-03-02')));

    final doc = await s.api.document(3, [12, 11], forDate: DateTime(2026, 11, 20));

    final request = s.adapter.requests.single;
    expect('${request.method} ${request.path}', 'GET /v1/shops/3/consent-document');
    expect(request.uri.queryParametersAll, {
      'pet_ids': ['11', '12'],
      'for_date': ['2026-11-20'],
    });
    expect(doc.digest, 'digest-1');
    expect(doc.previousConsentOn, DateTime(2026, 3, 2));
    expect(doc.parts, [ConsentPart.basic, ConsentPart.senior, ConsentPart.condition]);
    expect(doc.texts[ConsentPart.basic], 'basic 글의 첫 줄.\nbasic 글의 둘째 줄.');
    final pet = doc.pets.single;
    // 레코드 안의 목록은 같은 것인지로 견준다 — 칸을 따로 본다.
    expect((pet.petId, pet.name), (11, '콩이'));
    expect(pet.conditions, ['심장 질환']);
    expect(pet.parts, ConsentPart.values);
  });

  test('모르는 토막은 버린다', () {
    final doc = ConsentDocument.fromJson(consentDocumentJson(
      pets: [
        {'pet_id': 11, 'name': '콩이', 'conditions': <String>[], 'parts': ['basic', 'vaccine']},
      ],
      texts: const ['basic', 'vaccine'],
    ));

    expect(doc.parts, [ConsentPart.basic]);
    expect(doc.pets.single.parts, [ConsentPart.basic]);
  });

  test('현장 서명을 보낸다 — 그림은 base64 로', () async {
    Map<String, dynamic>? sent;
    final s = _build((o, b) {
      sent = _bodyOf(b);
      return const FakeResponse(statusCode: 201, data: {'signature_id': 91});
    });

    final id = await s.api.signInShop(
      3,
      petIds: [11],
      digest: 'digest-1',
      signerName: '김민지',
      png: Uint8List.fromList([1, 2, 3]),
      forDate: DateTime(2026, 11, 20),
    );

    expect(id, 91);
    expect('${s.adapter.requests.single.method} ${s.adapter.requests.single.path}', 'POST /v1/shops/3/consent-signatures');
    expect(sent, {
      'pet_ids': [11],
      'doc_digest': 'digest-1',
      'signer_name': '김민지',
      'signature_png': 'AQID',
      'for_date': '2026-11-20',
    });
  });

  test('아이의 서명 목록과 한 장을 읽는다', () async {
    final s = _build(
      (o, b) => o.path.endsWith('/consent-signatures')
          ? FakeResponse(statusCode: 200, data: {
              'items': [signatureBriefJson(), signatureBriefJson(id: 90, channel: 'link', parts: const ['basic', 'fax'])],
            })
          : FakeResponse(statusCode: 200, data: signatureDetailJson()),
    );

    final list = await s.api.signatures(3, 11);
    final one = await s.api.signature(3, 91);

    expect(s.adapter.requests.map((r) => r.path), ['/v1/shops/3/pets/11/consent-signatures', '/v1/shops/3/consent-signatures/91']);
    expect(list.map((b) => (b.signatureId, b.channel)), [(91, SignatureChannel.inShop), (90, SignatureChannel.link)]);
    expect(list.map((b) => b.parts), [
      [ConsentPart.basic, ConsentPart.senior],
      [ConsentPart.basic],
    ]);
    expect(list.first.signedAt.isUtc, isTrue);
    expect((one.signerName, one.channel), ('김민지', SignatureChannel.link));
    final pet = one.pets.single;
    expect((pet.petId, pet.shownName), (11, '콩이'));
    expect(pet.conditions, ['심장 질환']);
    expect(pet.parts.map((p) => (p.part, p.body)), [(ConsentPart.basic, '미용 안내의 글.'), (ConsentPart.condition, '지병 안내의 글.')]);
  });

  test('모르는 길(channel)의 서명은 목록에서 뺀다', () {
    expect(SignatureBrief.tryParse(signatureBriefJson(channel: 'fax')), isNull);
  });

  test('서명 그림은 받은 바이트 그대로다', () async {
    final png = Uint8List.fromList([0x89, 0x50, 0x4E, 0x47, 1, 2, 3]);
    final s = _build((o, b) => FakeResponse(statusCode: 200, data: png, headers: const {
      'content-type': ['image/png'],
    }));

    final bytes = await s.api.signatureImage(3, 91);

    expect(s.adapter.requests.single.path, '/v1/shops/3/consent-signatures/91/image');
    expect(bytes, png);
  });

  test('반려동물의 동의가 서명으로 받은 것인지 읽는다', () {
    Pet pet(Object? via) => Pet.fromJson({
      ...petJson(),
      'grooming_consent_on': via == null ? null : '2026-11-16',
      'grooming_consent_via': via,
    });

    expect(pet('signature').groomingConsentVia, ConsentVia.signature);
    expect(pet('manual').groomingConsentVia, ConsentVia.manual);
    expect(pet('fax').groomingConsentVia, ConsentVia.manual);
    expect(pet(null).groomingConsentVia, isNull);
    expect(Pet.fromJson(petJson()).groomingConsentVia, isNull);   // 옛 서버
  });
}

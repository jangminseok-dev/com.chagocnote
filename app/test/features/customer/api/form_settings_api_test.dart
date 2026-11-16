// FormSettingsApi 와 모델을 실제 네트워크 없이 검증한다 — 경로, 본문, 응답 해석.
import 'dart:convert';
import 'dart:typed_data';

import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/customer/api/consent_models.dart';
import 'package:chagocnote/features/customer/api/form_settings_api.dart';
import 'package:chagocnote/features/customer/api/form_settings_models.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/form_settings_fixtures.dart';

({FormSettingsApi api, FakeHttpClientAdapter adapter}) _build(FakeHandler handle) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = MemoryTokenStore()..save(access: 'a', refresh: 'r');
  return (api: FormSettingsApi(ApiClient(tokenStore: store, dio: dio, refreshDio: refreshDio)), adapter: adapter);
}

Map<String, dynamic> _bodyOf(Uint8List? body) => jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;

void main() {
  test('서류 설정을 읽는다 — 지금 값과 기본값', () async {
    final s = _build((o, b) => FakeResponse(statusCode: 200, data: formSettingsJson(linkDays: 7, seniorAge: 8)));

    final got = await s.api.settings(3);

    expect('${s.adapter.requests.single.method} ${s.adapter.requests.single.path}', 'GET /v1/shops/3/form-settings');
    expect((got.linkDays, got.seniorAge, got.consentDays), (7, 8, 365));
    expect((got.defaults.linkDays, got.defaults.seniorAge, got.defaults.consentDays), (14, 10, 365));
    expect(got.reservationText, defaultReservationText);
    expect(got.defaults.consentText, defaultConsentText);
  });

  test('바꿀 때는 다섯 칸 전체를 보내고 기본 글 그대로면 null 로 보낸다', () async {
    late Map<String, dynamic> sent;
    final s = _build((o, b) {
      sent = _bodyOf(b);
      return FakeResponse(statusCode: 200, data: formSettingsJson(linkDays: 3));
    });
    final now = FormSettings.fromJson(formSettingsJson());

    final saved = await s.api.updateSettings(3, now.copyWith(linkDays: 3, consentText: '서명 부탁드려요\n{링크}'));

    expect('${s.adapter.requests.single.method} ${s.adapter.requests.single.path}', 'PUT /v1/shops/3/form-settings');
    expect(sent, {
      'link_days': 3,
      'senior_age': 10,
      'consent_days': 365,
      'reservation_text': null,
      'consent_text': '서명 부탁드려요\n{링크}',
      'intake_keep_days': 30,
      'intake_hidden': <String>[],
    });
    expect(saved.linkDays, 3);
  });

  test('문진표의 두 칸 — 읽고, 바꾸면 함께 보낸다. 칸이 없는 옛 응답은 기본값이다', () async {
    late Map<String, dynamic> sent;
    final s = _build((o, b) {
      if (o.method == 'PUT') sent = _bodyOf(b);
      return FakeResponse(statusCode: 200, data: formSettingsJson(intakeKeepDays: 14, intakeHidden: ['weight']));
    });

    final got = await s.api.settings(3);
    await s.api.updateSettings(3, got.copyWith(intakeHidden: ['weight', 'style'], intakeKeepDays: 7));

    expect((got.intakeKeepDays, got.defaults.intakeKeepDays), (14, 30));
    expect(got.intakeHidden, ['weight']);
    expect(sent['intake_keep_days'], 7);
    expect(sent['intake_hidden'], ['weight', 'style']);
    final old = FormSettings.fromJson(formSettingsJson()..remove('intake_keep_days')..remove('intake_hidden'));
    expect(old.intakeKeepDays, 30);
    expect(old.intakeHidden, isEmpty);
  });

  test('동의서의 글 — 토막의 순서 그대로, 모르는 토막은 버린다', () async {
    final s = _build((o, b) => FakeResponse(statusCode: 200, data: {
      'parts': [
        consentTextJson('basic'),
        consentTextJson('later_part'),
        consentTextJson('senior', body: '고친 글', edited: true),
      ],
    }));

    final parts = await s.api.consentTexts(3);

    expect(s.adapter.requests.single.path, '/v1/shops/3/consent-texts');
    expect([for (final p in parts) (p.part, p.edited)], [(ConsentPart.basic, false), (ConsentPart.senior, true)]);
    expect((parts[1].body, parts[1].defaultBody), ('고친 글', 'senior 의 기본 글'));
  });

  test('글을 고치고, null 을 보내면 기본 글로 되돌린다', () async {
    final bodies = <Map<String, dynamic>>[];
    final s = _build((o, b) {
      bodies.add(_bodyOf(b));
      return FakeResponse(statusCode: 200, data: consentTextJson('senior', body: '고친 글', edited: true));
    });

    final saved = await s.api.updateConsentText(3, ConsentPart.senior, '고친 글');
    await s.api.updateConsentText(3, ConsentPart.senior, null);

    expect('${s.adapter.requests.first.method} ${s.adapter.requests.first.path}',
        'PUT /v1/shops/3/consent-texts/senior');
    expect(bodies, [{'body': '고친 글'}, {'body': null}]);
    expect((saved.part, saved.edited), (ConsentPart.senior, true));
  });
}

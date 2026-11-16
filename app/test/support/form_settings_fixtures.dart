// 서류 설정·동의서 글·보낼 것 묶음의 가짜 응답(⑪-B).
const defaultReservationText = '[{매장}] 예약이 접수됐어요.\n{날짜} {시간}\n{아이}\n{메뉴}';
const defaultConsentText = '미용 전에 동의서를 읽고 서명해 주세요.\n{링크}';

Map<String, dynamic> formSettingsJson({
  int linkDays = 14,
  int seniorAge = 10,
  int consentDays = 365,
  String reservationText = defaultReservationText,
  String consentText = defaultConsentText,
}) => {
  'link_days': linkDays,
  'senior_age': seniorAge,
  'consent_days': consentDays,
  'reservation_text': reservationText,
  'consent_text': consentText,
  'defaults': {
    'link_days': 14,
    'senior_age': 10,
    'consent_days': 365,
    'reservation_text': defaultReservationText,
    'consent_text': defaultConsentText,
  },
};

Map<String, dynamic> consentTextJson(String part, {String? body, bool edited = false}) => {
  'part': part,
  'body': body ?? '$part 의 기본 글',
  'edited': edited,
  'default_body': '$part 의 기본 글',
};

Map<String, dynamic> consentTextsJson({String? senior}) => {
  'parts': [
    consentTextJson('basic'),
    consentTextJson('senior', body: senior, edited: senior != null),
    consentTextJson('condition'),
  ],
};

/// 토큰 자리에 가짜 글자를 둔 주소 — 실제 토큰을 테스트에 적지 않는다.
const fakeBundleUrl = 'https://web.test/f/FAKE-BUNDLE-LINK';

Map<String, dynamic> sendBundleJson({bool consent = true, int? createdFormId}) => {
  'created_form_id': createdFormId,
  'parts': [
    {'kind': 'reservation', 'text': '[차곡 살롱] 예약이 접수됐어요.\n11월 17일(화) 오후 2:30\n초코'},
    if (consent) {'kind': 'consent', 'text': '미용 전에 동의서를 읽고 서명해 주세요.\n$fakeBundleUrl'},
  ],
};

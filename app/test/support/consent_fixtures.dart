// 동의서 테스트가 함께 쓰는 가짜 응답. 주소는 가짜다 — 실제 링크의 토큰을 테스트에 적지 않는다.

const fakeConsentUrl = 'https://web.test/f/FAKE-FORM-LINK';

Map<String, dynamic> formLinkJson({int formId = 31, String url = fakeConsentUrl}) => {
  'form_id': formId,
  'url': url,
  'expires_on': '2026-11-30',
  'sent_on': '2026-11-16',
};

Map<String, dynamic> sentFormJson({
  int formId = 31,
  String customerName = '김민지',
  List<(int, String)> pets = const [(11, '콩이')],
  String url = fakeConsentUrl,
}) => {
  'form_id': formId,
  'kind': 'consent',
  'customer': {'customer_id': 7, 'name': customerName},
  'pets': [
    for (final (id, name) in pets) {'pet_id': id, 'name': name},
  ],
  'sent_on': '2026-11-16',
  'expires_on': '2026-11-30',
  'url': url,
};

Map<String, dynamic> consentDocumentJson({
  List<Map<String, dynamic>>? pets,
  List<String> texts = const ['basic', 'senior', 'condition'],
  String? previousConsentOn,
  String digest = 'digest-1',
}) => {
  'pets':
      pets ??
      [
        {
          'pet_id': 11,
          'name': '콩이',
          'conditions': ['심장 질환'],
          'parts': ['basic', 'senior', 'condition'],
        },
      ],
  'texts': {
    for (final part in texts) part: {'body': '$part 글의 첫 줄.\n$part 글의 둘째 줄.'},
  },
  'previous_consent_on': previousConsentOn,
  'doc_digest': digest,
};

Map<String, dynamic> signatureBriefJson({
  int id = 91,
  String channel = 'in_shop',
  List<String> parts = const ['basic', 'senior'],
}) => {
  'signature_id': id,
  'signed_at': '2026-11-16T03:00:00Z',
  'channel': channel,
  'signer_name': '김민지',
  'parts': parts,
};

Map<String, dynamic> signatureDetailJson({int id = 91, String channel = 'link'}) => {
  'signature_id': id,
  'signed_at': '2026-11-16T03:00:00Z',
  'channel': channel,
  'signer_name': '김민지',
  'by_member_id': 5,
  'pets': [
    {
      'pet_id': 11,
      'shown_name': '콩이',
      'conditions': ['심장 질환'],
      'parts': [
        {'part': 'basic', 'body': '미용 안내의 글.'},
        {'part': 'condition', 'body': '지병 안내의 글.'},
      ],
    },
  ],
};

import 'package:chagocnote/features/visit/api/record_models.dart';
import 'package:chagocnote/features/visit/state/photo_edits.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/visit_fixtures.dart';

RecordMedia _m(int id, String phase, int sortOrder, {String kind = 'photo'}) =>
    RecordMedia.fromJson(
      recordMediaJson(
        mediaId: id,
        phase: phase,
        sortOrder: sortOrder,
        kind: kind,
      ),
    );

/// 전 51·52, 후 61·62 — 서버가 주는 순서(전 → 후, 칸마다 순서).
final _media = [
  _m(51, 'before', 0),
  _m(52, 'before', 1),
  _m(61, 'after', 0),
  _m(62, 'after', 1),
];

List<(int, String, int)> _shape(List<MediaPlacement>? p) => [
  for (final x in p!) (x.mediaId, x.phase.code, x.sortOrder),
];

void main() {
  test('보이는 순서는 대표 규칙과 같다 — 후 사진부터, 그다음 전 사진, 영상은 맨 뒤', () {
    final media = [..._media, _m(71, 'after', 2, kind: 'video')];

    expect(galleryOrder(media).map((m) => m.mediaId), [61, 62, 51, 52, 71]);
  });

  test('빼기는 그 사진만 빼고 칸마다 0부터 다시 센다', () {
    expect(_shape(applyPhotoEdit(_media, 51, PhotoEdit.remove)), [
      (52, 'before', 0),
      (61, 'after', 0),
      (62, 'after', 1),
    ]);
  });

  test('전/후 바꾸기는 다른 칸의 맨 뒤로 옮긴다', () {
    expect(_shape(applyPhotoEdit(_media, 51, PhotoEdit.togglePhase)), [
      (52, 'before', 0),
      (61, 'after', 0),
      (62, 'after', 1),
      (51, 'after', 2),
    ]);
  });

  test('대표로는 그 칸의 맨 앞으로 옮긴다', () {
    expect(_shape(applyPhotoEdit(_media, 62, PhotoEdit.makeCover)), [
      (51, 'before', 0),
      (52, 'before', 1),
      (62, 'after', 0),
      (61, 'after', 1),
    ]);
  });

  test('그 사이 빠진 사진이면 아무것도 보내지 않는다(null)', () {
    expect(applyPhotoEdit(_media, 99, PhotoEdit.remove), isNull);
  });

  test('대표로는 대표가 될 수 있는 사진에만 — 이미 대표거나, 후 사진이 있는데 전 사진이면 안 된다', () {
    expect(canMakeCover(_media, 62), isTrue);
    expect(canMakeCover(_media, 61), isFalse, reason: '이미 대표');
    expect(canMakeCover(_media, 52), isFalse, reason: '후 사진이 대표를 먼저 가진다');
    final beforeOnly = [_m(51, 'before', 0), _m(52, 'before', 1)];
    expect(canMakeCover(beforeOnly, 52), isTrue);
    expect(
      canMakeCover([..._media, _m(71, 'after', 2, kind: 'video')], 71),
      isFalse,
      reason: '영상은 사진이 있으면 대표가 되지 않는다',
    );
  });

  test('기록 입력은 사진 자리만 바꾸고 나머지 칸·버전은 읽은 그대로 보낸다', () {
    final record = VisitRecord.fromJson(
      recordJson(
        weightKg: 4.2,
        careNote: '귀 청소',
        internalNote: '예민함',
        paymentMethod: 'card',
        totalAmount: 50000,
        items: [
          {'menu_id': 1, 'name': '목욕', 'amount': 30000},
        ],
        media: [recordMediaJson()],
        version: 7,
      ),
    );

    final input = recordInputOf(
      record,
      applyPhotoEdit(record.media, 51, PhotoEdit.remove)!,
    );

    expect(input.toJson(), {
      'version': 7,
      'weight_kg': 4.2,
      'care_note': '귀 청소',
      'internal_note': '예민함',
      'payment_method': 'card',
      'total_amount': 50000,
      'items': [
        {'menu_id': 1, 'amount': 30000},
      ],
      'media': <Object>[],
    });
  });
}

/// 기록 화면의 입력 규칙(설계 10.1 ④) — 미리 채우기, 총액, 사진 자리, 버전 충돌 뒤 합치기.
/// 서버 규칙을 앱에서 먼저 확인하려는 것이다 — 최종 판단은 서버다.
library;

import '../api/record_models.dart';
import '../api/visit_models.dart';

/// 기록의 돈 칸 상한(원) — 서버 입력 경계와 같다(설계 9절). 메뉴 정가도 같은 상한이다.
const maxAmount = 100000000;

/// 메모 한 칸의 최대 글자 수(설계 9절).
const maxNoteLength = 1000;

/// 폼의 메뉴 한 줄. [amount]가 null 이면 비워 둔 것 — 0원으로 보낸다.
class FormLine {
  const FormLine({required this.menuId, required this.name, this.amount});

  final int menuId;
  final String name;
  final int? amount;
}

/// 폼의 사진 하나 — 이미 기록에 붙은 사진. 폼에서 전/후를 바꾸거나 뺄 수 있고, 저장할 때 반영된다.
class FormMedia {
  const FormMedia(this.media, this.phase);

  final RecordMedia media;
  final MediaPhase phase;

  int get mediaId => media.mediaId;
}

/// 폼을 처음 열 때의 값.
class RecordFormStart {
  const RecordFormStart({
    required this.weightKg,
    required this.lines,
    required this.totalAmount,
    required this.payment,
    required this.careNote,
    required this.internalNote,
    required this.media,
    required this.version,
  });

  final double? weightKg;
  final List<FormLine> lines;

  /// null 이면 항목 합을 따라간다.
  final int? totalAmount;
  final PaymentMethod? payment;
  final String careNote;
  final String internalNote;
  final List<FormMedia> media;
  final int? version;
}

/// 사진만 있거나 아무것도 없는 기록 — 대기열이 사진을 붙이며 만든 기록도 여기 든다.
bool isBlankRecord(VisitRecord? r) =>
    r == null ||
    (r.weightKg == null &&
        r.items.isEmpty &&
        r.totalAmount == null &&
        r.paymentMethod == null &&
        (r.careNote ?? '').isEmpty &&
        (r.internalNote ?? '').isEmpty);

/// 처음 값. 기록이 비었으면(사진만 있어도) 몸무게는 반려동물의 현재 값, 메뉴는 예약한 메뉴와 그 정가로
/// 미리 채운다. 조금이라도 적은 기록이면 적은 그대로 보인다.
RecordFormStart recordFormStart(VisitDetail detail, List<Menu> menus) {
  final record = detail.record;
  final media = [
    for (final m in record?.media ?? const <RecordMedia>[])
      FormMedia(m, m.phase),
  ];
  if (!isBlankRecord(record)) {
    return RecordFormStart(
      weightKg: record!.weightKg,
      lines: [
        for (final i in record.items)
          FormLine(menuId: i.menuId, name: i.name, amount: i.amount),
      ],
      totalAmount: record.totalAmount,
      payment: record.paymentMethod,
      careNote: record.careNote ?? '',
      internalNote: record.internalNote ?? '',
      media: media,
      version: record.version,
    );
  }
  final prices = {for (final m in menus) m.menuId: m.price};
  return RecordFormStart(
    weightKg: detail.visit.pet?.weightKg,
    lines: [
      for (final m in detail.visit.menus)
        FormLine(menuId: m.menuId, name: m.name, amount: prices[m.menuId]),
    ],
    totalAmount: null,
    payment: null,
    careNote: '',
    internalNote: '',
    media: media,
    version: record?.version,
  );
}

/// 항목 합. 비운 금액은 0원이다.
int sumOfLines(Iterable<FormLine> lines) =>
    lines.fold(0, (sum, l) => sum + (l.amount ?? 0));

/// 총액 칸이 따라가는 글자 — 금액을 하나도 적지 않았으면 비운다(0원을 받은 게 아니다).
String sumText(Iterable<FormLine> lines) =>
    lines.every((l) => l.amount == null) ? '' : '${sumOfLines(lines)}';

/// 사진의 자리 — 폼에 놓인 순서대로 전·후 칸마다 0부터 센다.
List<MediaPlacement> placementsOf(List<FormMedia> media) {
  final next = {for (final p in MediaPhase.values) p: 0};
  return [
    for (final m in media)
      MediaPlacement(
        mediaId: m.mediaId,
        phase: m.phase,
        sortOrder: next.update(m.phase, (n) => n + 1) - 1,
      ),
  ];
}

/// 다른 곳(대기열·다른 기기)이 붙인 사진을 폼에 더한다 — 폼에 이미 있거나 사용자가 뺀 사진은 두고,
/// 새 사진만 뒤에 붙인다. 사용자가 고친 칸은 건드리지 않는다(설계 8절).
List<FormMedia> withNewMedia(
  List<FormMedia> form,
  Set<int> removed,
  VisitRecord? fresh,
) {
  final known = {for (final m in form) m.mediaId, ...removed};
  return [
    ...form,
    for (final m in fresh?.media ?? const <RecordMedia>[])
      if (!known.contains(m.mediaId)) FormMedia(m, m.phase),
  ];
}

/// 대표 사진 — 후 사진의 첫 장, 없으면 전 사진의 첫 장, 사진이 없으면 영상 포스터(서버의 대표 규칙과 같다).
RecordMedia? coverOf(List<RecordMedia> media) {
  final photos = media.where((m) => m.kind == MediaKind.photo);
  return photos.where((m) => m.phase == MediaPhase.after).firstOrNull ??
      photos.where((m) => m.phase == MediaPhase.before).firstOrNull ??
      media.firstOrNull;
}

/// 메모 칸 — 앞뒤 공백을 떼고 비었으면 null(지운다).
String? noteOrNull(String text) {
  final trimmed = text.trim();
  return trimmed.isEmpty ? null : trimmed;
}

/// 크게 보기에서 사진 하나를 바꾸는 규칙(설계 10.1 ⑤) — 전/후 바꾸기·대표로·빼기는 기록 전체 교체 한 번이다.
library;

import '../api/record_models.dart';
import 'record_rules.dart';

enum PhotoEdit { togglePhase, makeCover, remove }

/// 넘기기·크게 보기에서 보이는 순서 — 서버의 대표 규칙과 같다(후 사진 → 전 사진 → 영상, 칸마다 순서대로).
/// 그래서 첫 장이 늘 대표 사진이다.
List<RecordMedia> galleryOrder(List<RecordMedia> media) =>
    [...media]..sort((a, b) {
      int rank(RecordMedia m) =>
          (m.kind == MediaKind.photo ? 0 : 2) +
          (m.phase == MediaPhase.after ? 0 : 1);
      final byRank = rank(a).compareTo(rank(b));
      return byRank != 0 ? byRank : a.sortOrder.compareTo(b.sortOrder);
    });

/// "대표로"를 보일지 — 그 칸 맨 앞으로 옮겨 실제로 대표가 되는 사진에만. 후 사진이 있으면 전 사진은
/// 맨 앞으로 옮겨도 대표가 아니고, 사진이 있으면 영상도 대표가 아니다.
bool canMakeCover(List<RecordMedia> media, int mediaId) {
  final target = media.where((m) => m.mediaId == mediaId).firstOrNull;
  if (target == null || target.kind != MediaKind.photo) return false;
  if (coverOf(media)?.mediaId == mediaId) return false;
  return target.phase == MediaPhase.after ||
      !media.any(
        (m) => m.kind == MediaKind.photo && m.phase == MediaPhase.after,
      );
}

/// 바꾼 뒤의 사진 자리. 그 사진이 그사이 빠졌으면 null(보낼 것이 없다).
List<MediaPlacement>? applyPhotoEdit(
  List<RecordMedia> media,
  int mediaId,
  PhotoEdit edit,
) {
  final target = media.where((m) => m.mediaId == mediaId).firstOrNull;
  if (target == null) return null;
  // 서버가 주는 순서(전 → 후, 칸마다 순서) 그대로 두고 그 사진만 옮긴다.
  final ordered = [
    for (final m in [...media]..sort(_byPhaseThenOrder))
      if (m.mediaId != mediaId) FormMedia(m, m.phase),
  ];
  switch (edit) {
    case PhotoEdit.remove:
      break;
    case PhotoEdit.togglePhase:
      ordered.add(
        FormMedia(
          target,
          target.phase == MediaPhase.before
              ? MediaPhase.after
              : MediaPhase.before,
        ),
      );
    case PhotoEdit.makeCover:
      final first = ordered.indexWhere((m) => m.phase == target.phase);
      ordered.insert(
        first < 0 ? ordered.length : first,
        FormMedia(target, target.phase),
      );
  }
  return placementsOf(ordered);
}

int _byPhaseThenOrder(RecordMedia a, RecordMedia b) {
  final byPhase = a.phase.index.compareTo(b.phase.index);
  return byPhase != 0 ? byPhase : a.sortOrder.compareTo(b.sortOrder);
}

/// 사진 자리만 바꾼 전체 교체 — 나머지 칸과 버전은 읽은 기록 그대로 보낸다.
RecordInput recordInputOf(VisitRecord record, List<MediaPlacement> media) =>
    RecordInput(
      version: record.version,
      weightKg: record.weightKg,
      careNote: record.careNote,
      internalNote: record.internalNote,
      paymentMethod: record.paymentMethod,
      totalAmount: record.totalAmount,
      items: [
        for (final i in record.items) (menuId: i.menuId, amount: i.amount),
      ],
      media: media,
    );

/// 사진 자리를 바꾸지 않는 전체 교체의 사진 자리 — 서버가 준 차례(전 → 후, 칸마다 순서) 그대로(⑬ 하루 마무리의
/// 결제 장이 총액·수단만 바꿀 때).
List<MediaPlacement> keptPlacements(List<RecordMedia> media) => placementsOf([
  for (final m in [...media]..sort(_byPhaseThenOrder)) FormMedia(m, m.phase),
]);

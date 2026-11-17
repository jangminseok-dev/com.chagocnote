/// 하루 마무리(⑬ 설계 3.6)의 응답 모델 — 그날의 남은 일을 장으로.
library;

import 'record_models.dart';
import 'visit_models.dart';

/// 장의 종류 — 이 차례로 넘긴다(정리 안 된 예약 → 결제 안 적음 → 알림장 안 보냄).
enum WrapUpKind {
  unresolved('unresolved'),
  unpaid('unpaid'),
  reportUnsent('report_unsent');

  const WrapUpKind(this.code);

  final String code;

  static WrapUpKind? tryParse(Object? code) {
    for (final k in values) {
      if (k.code == code) return k;
    }
    return null;
  }
}

/// 결제 장에 채워 둘 값 — 둘 다 고칠 수 있고, 근거가 없으면 null(그 자리에서 묻는다).
class WrapUpPrefill {
  const WrapUpPrefill({required this.totalAmount, required this.paymentMethod});

  factory WrapUpPrefill.fromJson(Map<String, dynamic> json) => WrapUpPrefill(
    totalAmount: json['total_amount'] as int?,
    paymentMethod: PaymentMethod.values
        .where((m) => m.code == json['payment_method'])
        .firstOrNull,
  );

  final int? totalAmount;
  final PaymentMethod? paymentMethod;
}

/// 한 장 — 방문 하나의 남은 일 하나.
class WrapUpCard {
  const WrapUpCard({
    required this.kind,
    required this.visit,
    required this.photoUrl,
    required this.prefill,
  });

  /// 모르는 종류(서버가 더한 남은 일)·모양이 깨진 장은 null — 나머지 장은 보인다.
  static WrapUpCard? tryParse(Object? json) {
    try {
      final j = json! as Map<String, dynamic>;
      final kind = WrapUpKind.tryParse(j['kind']);
      if (kind == null) return null;
      return WrapUpCard(
        kind: kind,
        visit: Visit.fromJson(j['visit'] as Map<String, dynamic>),
        photoUrl: j['photo_url'] as String?,
        prefill: j['prefill'] == null
            ? null
            : WrapUpPrefill.fromJson(j['prefill'] as Map<String, dynamic>),
      );
    } catch (_) {
      return null;
    }
  }

  final WrapUpKind kind;
  final Visit visit;

  /// 아이의 프로필 사진 썸네일 서명 URL.
  final String? photoUrl;

  /// 결제 장에만.
  final WrapUpPrefill? prefill;
}

class DayWrapUp {
  const DayWrapUp({required this.date, required this.cards});

  factory DayWrapUp.fromJson(Map<String, dynamic> json) => DayWrapUp(
    date: parseDay(json['date'] as String),
    cards: [for (final c in json['cards'] as List) ?WrapUpCard.tryParse(c)],
  );

  final DateTime date;
  final List<WrapUpCard> cards;
}

import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/consent_api.dart';
import '../api/consent_models.dart';

final consentApiProvider = Provider<ConsentApi>((ref) => ConsentApi(ref.watch(apiClientProvider)));

/// 보낸 서류 — 살아 있는 링크. 화면을 떠나면 버린다.
final sentFormsProvider = FutureProvider.autoDispose.family<List<SentForm>, int>(
  (ref, shopId) => runShopScoped(ref, () => ref.read(consentApiProvider).forms(shopId)),
);

/// 문서를 읽는 키 — 아이들(오름차순으로 이은 글자)과 기준일(예약 날, `YYYY-MM-DD` 또는 null).
/// 목록과 날짜는 값으로 비교되지 않아 글자로 둔다.
typedef ConsentDocumentKey = ({int shopId, String petIds, String? forDate});

/// 매장에서 바로 서명받을 문서. 서버가 열 때 조립한다 — 내용이 바뀌었다고 하면 다시 읽는다.
final consentDocumentProvider = FutureProvider.autoDispose.family<ConsentDocument, ConsentDocumentKey>(
  (ref, key) => runShopScoped(
    ref,
    () => ref.read(consentApiProvider).document(
      key.shopId,
      [for (final id in key.petIds.split(',')) int.parse(id)],
      forDate: key.forDate == null ? null : DateTime.parse(key.forDate!),
    ),
  ),
);

typedef PetSignaturesKey = ({int shopId, int petId});
typedef SignatureKey = ({int shopId, int signatureId});

final petSignaturesProvider = FutureProvider.autoDispose.family<List<SignatureBrief>, PetSignaturesKey>(
  (ref, key) => runShopScoped(ref, () => ref.read(consentApiProvider).signatures(key.shopId, key.petId)),
);

final signatureDetailProvider = FutureProvider.autoDispose.family<SignatureDetail, SignatureKey>(
  (ref, key) => runShopScoped(ref, () => ref.read(consentApiProvider).signature(key.shopId, key.signatureId)),
);

/// 서명 그림의 바이트. 기기에 저장하지 않는다 — 화면을 떠나면 버린다.
final signatureImageProvider = FutureProvider.autoDispose.family<Uint8List, SignatureKey>(
  (ref, key) => runShopScoped(ref, () => ref.read(consentApiProvider).signatureImage(key.shopId, key.signatureId)),
);

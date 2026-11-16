import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/intake_api.dart';
import '../api/intake_models.dart';

final intakeApiProvider = Provider<IntakeApi>((ref) => IntakeApi(ref.watch(apiClientProvider)));

/// 받은 문진표 — 아직 등록하지 않은 답. 등록·지우기가 끝나면 `IntakeCommands`·`CustomerCommands` 가 다시 읽게 한다.
final receivedIntakeProvider = FutureProvider.autoDispose.family<List<IntakeAnswerItem>, int>(
  (ref, shopId) => runShopScoped(ref, () => ref.read(intakeApiProvider).answers(shopId)),
);

typedef IntakeAnswerKey = ({int shopId, int answerId});

/// 받은 문진표 한 장.
final intakeAnswerProvider = FutureProvider.autoDispose.family<IntakeAnswer, IntakeAnswerKey>(
  (ref, key) => runShopScoped(ref, () => ref.read(intakeApiProvider).answer(key.shopId, key.answerId)),
);

/// 매장이 문진표에 더한 질문.
final intakeQuestionsProvider = FutureProvider.autoDispose.family<List<IntakeQuestion>, int>(
  (ref, shopId) => runShopScoped(ref, () => ref.read(intakeApiProvider).questions(shopId)),
);

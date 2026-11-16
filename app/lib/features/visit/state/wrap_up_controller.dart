import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/shop_scoped.dart';
import '../api/wrap_up_models.dart';
import 'visit_providers.dart';
import 'wrap_up_rules.dart';

/// 하루 마무리의 넘김 상태 — 서버의 장(차례대로)과 건너뛴 장, 지나온 장 수.
class WrapUpState {
  const WrapUpState({
    required this.queue,
    required this.skipped,
    required this.passed,
    required this.total,
  });

  final List<WrapUpCard> queue;
  final Set<String> skipped;

  /// 끝냈거나 건너뛴 장 수.
  final int passed;

  /// 처음 연 때의 장 수(다시 읽어 늘면 함께 는다).
  final int total;

  /// 지금 장 — 건너뛰지 않은 첫 장. 없으면 끝이다.
  WrapUpCard? get current {
    for (final c in queue) {
      if (!skipped.contains(cardKey(c))) return c;
    }
    return null;
  }

  /// 위의 `N개 중 M번째` 의 M.
  int get position => passed + 1;

  /// 남겨 둔 장 수(끝 화면의 `N개는 남겨 뒀어요`) — 지금도 서버에 남은 것만 센다.
  int get skippedCount => queue.where((c) => skipped.contains(cardKey(c))).length;
}

typedef WrapUpKey = ({int shopId, DateTime date, WrapUpKind? start});

/// 하루 마무리(⑬ 설계 3.6) — 장을 하나씩 넘긴다. 한 장을 끝내면 [done] 이 서버에서 다시 읽어 다음 장으로 간다
/// (다른 기기가 먼저 끝낸 장도 빠진다). [skip] 은 아무것도 적지 않고 다음 장 — 건너뛴 장은 다시 읽어도 되살아나지
/// 않고 남은 일에 그대로 남는다. [reviewSkipped] 는 남겨 둔 장으로 처음부터.
class WrapUpController extends AsyncNotifier<WrapUpState> {
  WrapUpController(this.key);

  final WrapUpKey key;

  Future<List<WrapUpCard>> _fetch() async => orderCards(
    (await runShopScoped(ref, () => ref.read(visitApiProvider).dayWrapUp(key.shopId, key.date))).cards,
    key.start,
  );

  @override
  Future<WrapUpState> build() async {
    final queue = await _fetch();
    return WrapUpState(queue: queue, skipped: const {}, passed: 0, total: queue.length);
  }

  void skip() {
    final s = state.value;
    final current = s?.current;
    if (s == null || current == null) return;
    state = AsyncData(
      WrapUpState(queue: s.queue, skipped: {...s.skipped, cardKey(current)}, passed: s.passed + 1, total: s.total),
    );
  }

  /// 지금 장을 끝냈다(성공했든, 그 사이 다른 기기가 끝내 실패했든) — 다시 읽고 다음 장으로.
  /// 다시 읽지 못하면 보던 상태를 둔다.
  Future<void> done() async {
    final s = state.value;
    if (s == null) return;
    final List<WrapUpCard> queue;
    try {
      queue = await _fetch();
    } catch (_) {
      return;
    }
    if (!ref.mounted) return;
    final passed = s.passed + 1;
    final left = queue.where((c) => !s.skipped.contains(cardKey(c))).length;
    final total = passed + left > s.total ? passed + left : s.total;
    state = AsyncData(WrapUpState(queue: queue, skipped: s.skipped, passed: passed, total: total));
  }

  void reviewSkipped() {
    final s = state.value;
    if (s == null) return;
    state = AsyncData(WrapUpState(queue: s.queue, skipped: const {}, passed: 0, total: s.queue.length));
  }
}

final wrapUpControllerProvider = AsyncNotifierProvider.autoDispose
    .family<WrapUpController, WrapUpState, WrapUpKey>(WrapUpController.new);

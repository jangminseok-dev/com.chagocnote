import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../proxy/providers.dart';

/// "보기 방식"처럼 enum 하나를 기기에 기억하는 컨트롤러. 기능마다 복사하던 것을
/// 하나로 — 새 토글은 키·값 목록·기본값만 주면 된다.
///
/// 기본값은 [fallback]이고, 저장된 이름이 값 목록에 없으면(옛 버전·오타) 기본값이다.
class ViewModeController<T extends Enum> extends AsyncNotifier<T> {
  ViewModeController({
    required this.key,
    required this.values,
    required this.fallback,
  });

  final String key;
  final List<T> values;
  final T fallback;

  @override
  Future<T> build() async {
    final saved = await ref.read(prefsStoreProvider).read(key);
    return values.firstWhere((v) => v.name == saved, orElse: () => fallback);
  }

  Future<void> select(T mode) async {
    state = AsyncData(mode);
    await ref.read(prefsStoreProvider).write(key, mode.name);
  }
}

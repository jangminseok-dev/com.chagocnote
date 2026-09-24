import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/core/storage/view_mode_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

enum _Mode { one, two }

final _provider = AsyncNotifierProvider<ViewModeController<_Mode>, _Mode>(
  () => ViewModeController(
    key: 'mode',
    values: _Mode.values,
    fallback: _Mode.one,
  ),
);

ProviderContainer _container(MemoryPrefsStore prefs) {
  final container = ProviderContainer(
    overrides: [prefsStoreProvider.overrideWithValue(prefs)],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  test('저장된 것이 없으면 기본값이다', () async {
    final container = _container(MemoryPrefsStore());
    expect(await container.read(_provider.future), _Mode.one);
  });

  test('고르면 바로 바뀌고 기기에 이름으로 남는다', () async {
    final prefs = MemoryPrefsStore();
    final container = _container(prefs);
    await container.read(_provider.future);
    await container.read(_provider.notifier).select(_Mode.two);
    expect(container.read(_provider).value, _Mode.two);
    expect(await prefs.read('mode'), 'two');
  });

  test('저장된 이름으로 시작하고, 모르는 이름이면 기본값이다', () async {
    final prefs = MemoryPrefsStore();
    await prefs.write('mode', 'two');
    expect(await _container(prefs).read(_provider.future), _Mode.two);

    final stale = MemoryPrefsStore();
    await stale.write('mode', 'three');
    expect(await _container(stale).read(_provider.future), _Mode.one);
  });
}

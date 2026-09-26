import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../design/widgets/app_error_banner.dart';
import '../../design/widgets/app_error_retry.dart';
import '../proxy/network_watcher.dart';
import 'error_kind.dart';
import 'error_messages.dart';

/// 서버에서 읽는 화면 본문의 틀 — 불러오는 중·처음부터 실패·받은 데이터 위 실패·성공을 한 곳에서
/// 그린다(오류 화면 다듬기 설계 3절).
///
/// - 값이 없고 실패면 [AppErrorRetry] — 원인 문구와 원인 행동(다시 시도, 또는 뒤로 갈 수 있으면 돌아가기).
/// - 값이 있는데 새로 불러오다 실패면 [builder]를 그대로 두고 위에 [AppErrorBanner].
/// - 이 틀이 화면에 있는 동안 인터넷이 돌아오면, 오류가 인터넷 없음일 때 [onRetry]를 한 번 부른다.
/// - [onRefresh]가 있으면 당겨서 새로고침. 실패는 [value]의 오류로 보이므로 여기서 삼킨다.
///
/// 저장 실패처럼 누른 일의 오류는 이 틀이 아니라 화면의 문구·스낵바로 보인다(쓰던 내용을 지우지 않는다).
class AsyncBody<T> extends ConsumerStatefulWidget {
  const AsyncBody({
    super.key,
    required this.value,
    required this.onRetry,
    required this.builder,
    this.onRefresh,
  }) : inline = false,
       placeholder = null;

  /// 흐름 안에 놓이는 자리(달력, 탭 안) — 높이를 채우지 않고, 오류는 [AppErrorRetry.inline].
  /// [placeholder]를 주면 처음 불러오는 동안 로딩 대신 그것을 보인다(달력은 빈 칸을 먼저 그린다).
  const AsyncBody.inline({
    super.key,
    required this.value,
    required this.onRetry,
    required this.builder,
    this.placeholder,
  }) : inline = true,
       onRefresh = null;

  final AsyncValue<T> value;
  final VoidCallback onRetry;
  final Widget Function(T data) builder;
  final Future<void> Function()? onRefresh;
  final bool inline;
  final Widget? placeholder;

  @override
  ConsumerState<AsyncBody<T>> createState() => _AsyncBodyState<T>();
}

class _AsyncBodyState<T> extends ConsumerState<AsyncBody<T>> {
  StreamSubscription<void>? _restored;

  @override
  void initState() {
    super.initState();
    _watchNetwork();
  }

  @override
  void didUpdateWidget(AsyncBody<T> oldWidget) {
    super.didUpdateWidget(oldWidget);
    _watchNetwork();
  }

  @override
  void dispose() {
    _restored?.cancel();
    super.dispose();
  }

  /// 오류가 인터넷 없음인 동안만 복귀 신호를 듣는다 — 멀쩡한 화면·다시 시도 중엔 듣지 않는다.
  void _watchNetwork() {
    final value = widget.value;
    final offline =
        value.hasError &&
        !value.isLoading &&
        kindOf(value.error!) == ErrorKind.offline;
    if (offline && _restored == null) {
      _restored = ref.read(networkWatcherProvider).restored.listen((_) {
        _restored?.cancel();
        _restored = null;
        widget.onRetry();
      });
    } else if (!offline && _restored != null) {
      _restored!.cancel();
      _restored = null;
    }
  }

  Future<void> _refresh() async {
    try {
      await widget.onRefresh!();
    } catch (_) {
      // 실패는 value 의 오류(띠)로 보인다.
    }
  }

  @override
  Widget build(BuildContext context) {
    final value = widget.value;
    if (!value.hasValue) {
      // 다시 시도 중(오류를 품은 로딩)이면 오류 대신 로딩을 보인다.
      if (value.hasError && !value.isLoading) {
        return _failure(context, value.error!);
      }
      if (widget.placeholder case final placeholder?) return placeholder;
      return widget.inline
          ? const Padding(
              padding: EdgeInsets.all(24),
              child: Center(child: CircularProgressIndicator()),
            )
          : const Center(child: CircularProgressIndicator());
    }
    Widget content = widget.builder(value.requireValue);
    if (widget.onRefresh != null) {
      content = RefreshIndicator(onRefresh: _refresh, child: content);
    }
    final banner = AnimatedSize(
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeOut,
      alignment: Alignment.topCenter,
      child: value.hasError ? _banner(value.error!) : const SizedBox.shrink(),
    );
    return widget.inline
        ? Column(mainAxisSize: MainAxisSize.min, children: [banner, content])
        : Column(children: [banner, Expanded(child: content)]);
  }

  Widget _failure(BuildContext context, Object error) {
    final kind = kindOf(error);
    final navigator = Navigator.of(context);
    final onRetry = kind.retryable ? widget.onRetry : null;
    final onBack = !kind.retryable && navigator.canPop()
        ? () => navigator.maybePop()
        : null;
    final message = loadMessageFor(error);
    return widget.inline
        ? AppErrorRetry.inline(
            message: message,
            onRetry: onRetry,
            onBack: onBack,
          )
        : AppErrorRetry(message: message, onRetry: onRetry, onBack: onBack);
  }

  Widget _banner(Object error) {
    final kind = kindOf(error);
    final offline = kind == ErrorKind.offline;
    return AppErrorBanner(
      message: offline ? offlineBannerMessage : loadMessageFor(error),
      offline: offline,
      // 인터넷 없음은 스스로 잇고, 권한·없음은 다시 해도 같다. 다시 시도 중엔 결과가 올 때까지 감춘다.
      onRetry: !offline && kind.retryable && !widget.value.isLoading
          ? widget.onRetry
          : null,
    );
  }
}

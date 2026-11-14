import 'dart:async';

import 'package:flutter/services.dart';

/// 검색창 입력을 받아, 한글 조합이 끝난 뒤 [delay] 동안 입력이 없으면
/// [onSearch]를 부른다(설계 8.2).
///
/// - 조합 중(`composing` 구간이 있음)에는 기다린다 — 'ㅋ'·'코'·'콩' 을 하나씩
///   보내지 않는다.
/// - 앞뒤 공백을 없앤 검색어가 마지막으로 보낸 것과 같으면 보내지 않는다
///   (커서만 옮기거나 공백만 친 경우).
class SearchDebouncer {
  SearchDebouncer({
    required this.onSearch,
    this.delay = const Duration(milliseconds: 300),
  });

  final void Function(String query) onSearch;
  final Duration delay;

  Timer? _timer;
  String _sent = '';

  void onChanged(TextEditingValue value) {
    _timer?.cancel();
    final composing = value.composing;
    if (composing.isValid && !composing.isCollapsed) return;
    final query = value.text.trim();
    _timer = Timer(delay, () {
      if (query == _sent) return;
      _sent = query;
      onSearch(query);
    });
  }

  /// 걸려 있던 것을 버리고 "마지막으로 보낸 검색어"를 잊는다 — 화면이 결과를 스스로 비웠을 때 부른다.
  /// 그 뒤에 같은 검색어를 다시 쳐도 보낸다.
  void reset() {
    _timer?.cancel();
    _sent = '';
  }

  void dispose() => _timer?.cancel();
}

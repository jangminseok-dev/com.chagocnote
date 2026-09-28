import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import 'pressable.dart';

/// 메모 칸 제목 줄의 받아쓰기 토글(④-3b 설계 3.3).
///
/// 쉬는 동안은 마이크 아이콘만, 듣는 동안은 아이콘 오른쪽 위에 점이 0.8초 주기로 깜빡인다.
/// 점은 팔레트의 포인트 색(잉크)이다 — 이 앱은 팔레트 밖의 색(붉은색)을 들이지 않는다.
/// 탭 영역은 44×44.
class AppMicButton extends StatefulWidget {
  const AppMicButton({
    super.key,
    required this.listening,
    required this.onTap,
    this.semanticLabel,
  });

  final bool listening;
  final VoidCallback onTap;
  final String? semanticLabel;

  @override
  State<AppMicButton> createState() => _AppMicButtonState();
}

class _AppMicButtonState extends State<AppMicButton>
    with SingleTickerProviderStateMixin {
  // 0.4초에 한 번 꺼지고 0.4초에 켜진다 — 한 주기 0.8초. 첫 프레임(0)은 켜진 점이다.
  late final AnimationController _blink;

  @override
  void initState() {
    super.initState();
    _blink = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    if (widget.listening) _blink.repeat(reverse: true);
  }

  @override
  void didUpdateWidget(AppMicButton oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.listening == oldWidget.listening) return;
    if (widget.listening) {
      _blink.repeat(reverse: true);
    } else {
      _blink.reset();
    }
  }

  @override
  void dispose() {
    _blink.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: widget.onTap,
      semanticLabel: widget.semanticLabel,
      child: SizedBox(
        width: 44,
        height: 44,
        child: Stack(
          alignment: Alignment.center,
          children: [
            const Icon(Icons.mic_rounded, size: 22, color: AppColors.ink),
            if (widget.listening)
              Positioned(
                top: 9,
                right: 9,
                child: FadeTransition(
                  opacity: ReverseAnimation(_blink),
                  child: Container(
                    width: 7,
                    height: 7,
                    decoration: const BoxDecoration(
                      color: AppColors.ink,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

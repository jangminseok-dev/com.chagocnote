import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_shadows.dart';
import 'pressable.dart';

/// 켜고 끄는 스위치 — 40×24 알약 안에서 흰 동그라미가 좌우로 움직인다.
///
/// 켜짐은 잉크 바탕, 꺼짐은 구분선 색 바탕이다. 누르면 지금 값의 반대로 [onChanged]를 부른다 —
/// 값은 부모가 든다. [onChanged]가 null 이면 눌리지 않고 흐리다(읽기 전용).
/// [semanticLabel]은 스크린리더가 읽는 이름이고, 켜짐·꺼짐과 함께 읽힌다.
class AppSwitch extends StatelessWidget {
  const AppSwitch({
    super.key,
    required this.value,
    required this.onChanged,
    this.semanticLabel,
  });

  final bool value;
  final ValueChanged<bool>? onChanged;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final onChanged = this.onChanged;
    return Pressable(
      onTap: onChanged == null ? null : () => onChanged(!value),
      semanticLabel: semanticLabel,
      // 켜짐·꺼짐은 Pressable 의 의미 노드(이름표·버튼)에 합쳐져 읽힌다.
      child: Semantics(
        toggled: value,
        enabled: onChanged != null,
        // 누르는 영역은 44×44, 그리는 알약은 그 가운데 40×24 다.
        child: SizedBox(
          width: 44,
          height: 44,
          child: Center(
            child: Opacity(
              opacity: onChanged == null ? 0.4 : 1,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 150),
                width: 40,
                height: 24,
                padding: const EdgeInsets.all(2),
                alignment: value ? Alignment.centerRight : Alignment.centerLeft,
                decoration: BoxDecoration(
                  color: value ? AppColors.ink : AppColors.line,
                  borderRadius: BorderRadius.circular(AppRadius.pill),
                ),
                child: Container(
                  width: 20,
                  height: 20,
                  decoration: const BoxDecoration(
                    color: AppColors.white,
                    shape: BoxShape.circle,
                    boxShadow: AppShadows.badge,
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

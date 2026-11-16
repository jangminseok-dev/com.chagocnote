import 'dart:math' as math;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../state/signature_png.dart';

/// 서명의 선들. 점은 칸의 폭·높이에 대한 비율(0~1)이라 칸의 크기가 바뀌어도(화면을 돌려도) 그대로 그려진다.
/// 서명 칸의 가장 큰 폭 — 아이패드에서도 손으로 쓰기 알맞은 크기까지만 커진다.
const signaturePadMaxWidth = 560.0;

class SignatureController extends ChangeNotifier {
  final List<List<Offset>> _strokes = [];

  List<List<Offset>> get strokes => _strokes;

  bool get isEmpty => _strokes.isEmpty;

  void _begin(Offset point) {
    _strokes.add([point]);
    notifyListeners();
  }

  void _extend(Offset point) {
    _strokes.last.add(point);
    notifyListeners();
  }

  void clear() {
    if (_strokes.isEmpty) return;
    _strokes.clear();
    notifyListeners();
  }
}

/// 손가락으로 서명하는 칸(⑪ 설계 3.3 — 매장에서 바로 서명). 네이티브로 그린다.
///
/// - 한 번에 포인터 하나만 받는다 — 서명하는 동안 닿은 다른 손가락·손바닥은 선을 긋지 않는다.
/// - 칸 위의 손짓은 칸이 먼저 갖는다 — 서명하는 손가락을 따라 화면이 구르지 않는다.
/// - 비율은 5:2(600×240), 빈 칸에는 안내 글이 있다.
class SignaturePad extends StatefulWidget {
  const SignaturePad({super.key, required this.controller});

  static const canvasKey = Key('signature-pad');

  final SignatureController controller;

  @override
  State<SignaturePad> createState() => _SignaturePadState();
}

class _SignaturePadState extends State<SignaturePad> {
  /// 지금 그리는 포인터. 그리는 중이 아니면 null.
  int? _pointer;

  Offset _normalized(Offset local, Size size) => Offset(
    (local.dx / size.width).clamp(0.0, 1.0),
    (local.dy / size.height).clamp(0.0, 1.0),
  );

  Widget _canvas(SignatureController controller) {
    return AspectRatio(
          aspectRatio: signatureWidth / signatureHeight,
          child: LayoutBuilder(
            builder: (context, constraints) {
              final size = constraints.biggest;
              return Semantics(
                label: AppStrings.signaturePadLabel,
                child: RawGestureDetector(
                  // 누르자마자 이 칸이 손짓을 갖는다 — 바깥의 스크롤이 가져가지 못한다.
                  gestures: {
                    EagerGestureRecognizer: GestureRecognizerFactoryWithHandlers<EagerGestureRecognizer>(
                      EagerGestureRecognizer.new,
                      (_) {},
                    ),
                  },
                  child: Listener(
                    key: SignaturePad.canvasKey,
                    behavior: HitTestBehavior.opaque,
                    onPointerDown: (event) {
                      // 이미 그리는 중이면 다른 포인터는 받지 않는다. 마우스는 왼쪽 단추만.
                      if (_pointer != null || (event.buttons != 0 && event.buttons != kPrimaryButton)) return;
                      _pointer = event.pointer;
                      controller._begin(_normalized(event.localPosition, size));
                    },
                    onPointerMove: (event) {
                      if (event.pointer != _pointer) return;
                      controller._extend(_normalized(event.localPosition, size));
                    },
                    onPointerUp: (event) {
                      if (event.pointer == _pointer) _pointer = null;
                    },
                    onPointerCancel: (event) {
                      if (event.pointer == _pointer) _pointer = null;
                    },
                    child: ListenableBuilder(
                      listenable: controller,
                      builder: (context, _) => DecoratedBox(
                        decoration: BoxDecoration(
                          color: AppColors.white,
                          border: Border.all(color: AppColors.line),
                        ),
                        child: Stack(
                          fit: StackFit.expand,
                          children: [
                            if (controller.isEmpty)
                              const Center(
                                child: ExcludeSemantics(
                                  child: Text(AppStrings.signaturePadHint, style: AppTypography.caption),
                                ),
                              ),
                            CustomPaint(painter: _SignaturePainter(controller.strokes, controller.strokes.fold(0, (n, s) => n + s.length))),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        );
  }

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        // 칸이 화면을 다 덮으면 칸 밖을 끌어 굴릴 자리가 없다(가로로 돌린 폰) — 보이는 높이의 반, 폭 560 까지만.
        Center(
          child: ConstrainedBox(
            constraints: BoxConstraints(
              maxWidth: math.min(
                signaturePadMaxWidth,
                MediaQuery.sizeOf(context).height / 2 * signatureWidth / signatureHeight,
              ),
            ),
            child: _canvas(controller),
          ),
        ),
        Pressable(
          semanticLabel: AppStrings.signatureAgain,
          onTap: () {
            _pointer = null;
            controller.clear();
          },
          child: const Padding(
            // 누르는 자리는 44 이상으로 둔다.
            padding: EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, 0, AppSpacing.md),
            child: ExcludeSemantics(
              child: Text(
                AppStrings.signatureAgain,
                style: TextStyle(
                  inherit: true,
                  decoration: TextDecoration.underline,
                  color: AppColors.secondary,
                  fontSize: 13,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _SignaturePainter extends CustomPainter {
  _SignaturePainter(this.strokes, this.points);

  final List<List<Offset>> strokes;

  /// 점의 수 — 같은 목록에 점이 더해져도 다시 그리게 한다.
  final int points;

  @override
  void paint(Canvas canvas, Size size) => paintSignature(canvas, size, strokes);

  @override
  bool shouldRepaint(_SignaturePainter old) => old.points != points || old.strokes != strokes;
}

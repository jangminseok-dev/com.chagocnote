import 'package:flutter/widgets.dart';
import 'package:liquid_glass_widgets/liquid_glass_widgets.dart';

// `liquid_glass_widgets`를 앱 진입점에서 초기화하고 감싸는 두 함수.
//
// `main.dart`가 패키지를 직접 import하지 않도록, 셋업 관련 호출은
// 전부 이 파일 뒤에 감춘다(다른 브리지 파일과 같은 원칙).

/// 셰이더를 미리 디스크에서 RAM으로 올려 첫 프레임 깜빡임을 없앤다.
///
/// **테스트에서는 절대 호출하면 안 된다** — 테스트 환경에는 셰이더 에셋이
/// 없어서 예외를 던진다(`Asset 'shaders/liquid_glass_render.frag' not
/// found`).
Future<void> initializeGlass() => LiquidGlassWidgets.initialize();

/// 앱 루트를 유리 인프라 스코프로 감싼다.
///
/// `adaptiveQuality: true`를 켠다 — 기기를 실시간으로 벤치마크해서 유리
/// 품질 상한을 조정한다(1단계: 셰이더 미지원 기기는 즉시 `minimal`로 고정,
/// 2단계: 첫 ~3초간 실제 래스터 시간을 측정해 초기 품질을 정함, 3단계:
/// 이후 지속적으로 프레임 예산을 넘기면 품질을 낮추고 여유가 생기면
/// 다시 올림). 저사양 안드로이드에서 셰이더 품질을 자동으로 낮춰 프레임
/// 드랍을 줄이는 게 목적이다 — 패키지 문서는 이 기능을 실험적이라고
/// 표시하고 있어, 임계값이 전체 안드로이드 기기군에서 검증되진 않았다.
Widget wrapWithGlass(Widget app) {
  return LiquidGlassWidgets.wrap(child: app, adaptiveQuality: true);
}

import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/design/tokens/app_colors.dart';
import 'package:chagocnote/design/tokens/app_shadows.dart';
import 'package:chagocnote/design/widgets/app_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  // 설계 6.2: 글래스는 떠 있는 조작 계층에만 쓰고, 스크롤 콘텐츠의 목록 행·
  // 카드는 불투명 면으로 그린다(최종 검토 D).
  testWidgets('AppCard 는 실제 글래스 팩토리 아래에서도 글래스 없이 흰 면·구분선 테두리·옅은 그림자로 그린다', (
    tester,
  ) async {
    await tester.pumpWidget(
      const Directionality(
        textDirection: TextDirection.ltr,
        child: Center(child: AppCard(child: Text('행'))),
      ),
    );

    expect(find.byType(GlassSurface), findsNothing);
    expect(find.byType(BackdropFilter), findsNothing);
    final decoration = tester
        .widgetList<Container>(
          find.descendant(
            of: find.byType(AppCard),
            matching: find.byType(Container),
          ),
        )
        .map((c) => c.decoration)
        .whereType<BoxDecoration>()
        .single;
    expect(decoration.color, AppColors.white);
    expect((decoration.border! as Border).top.color, AppColors.line);
    expect(decoration.boxShadow, AppShadows.soft);
  });

  testWidgets('AppCard 골든', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      const SizedBox(
        width: 240,
        height: 120,
        child: AppCard(
          child: Text(
            '차곡노트',
            style: TextStyle(fontFamily: 'Pretendard', fontSize: 24),
          ),
        ),
      ),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_card.png'));
  });
}

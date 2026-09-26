import 'package:chagocnote/design/tokens/app_colors.dart';
import 'package:chagocnote/design/widgets/dictation_text_editing_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('진행 중 구간만 회색으로 나뉘어 그려지고, 구간이 없으면 한 덩이다', (tester) async {
    final controller = DictationTextEditingController(text: '앞안녕뒤');
    addTearDown(controller.dispose);
    late BuildContext context;
    await tester.pumpWidget(
      Builder(
        builder: (c) {
          context = c;
          return const SizedBox();
        },
      ),
    );
    const style = TextStyle(color: AppColors.ink);

    var notified = 0;
    controller.addListener(() => notified++);
    controller.pending = const TextRange(start: 1, end: 3);
    expect(notified, 1);

    final span = controller.buildTextSpan(
      context: context,
      style: style,
      withComposing: false,
    );
    final children = span.children!.cast<TextSpan>();
    expect(children.map((s) => s.text), ['앞', '안녕', '뒤']);
    expect(children[0].style?.color, isNot(AppColors.secondary));
    expect(children[1].style?.color, AppColors.secondary);
    expect(children[2].style?.color, isNot(AppColors.secondary));

    controller.pending = null;
    final plain = controller.buildTextSpan(
      context: context,
      style: style,
      withComposing: false,
    );
    expect(plain.toPlainText(), '앞안녕뒤');
    expect(plain.children, isNull);
  });
}

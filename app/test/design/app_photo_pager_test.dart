import 'package:chagocnote/design/widgets/app_glass_card.dart';
import 'package:chagocnote/design/widgets/app_photo_pager.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';
import '../support/upload_fakes.dart';

final _image = FakeMediaImages().image;

List<AppPagerPhoto> _photos(int n, {bool video = false}) => [
  for (var i = 0; i < n; i++)
    AppPagerPhoto(
      image: _image,
      label: i == 0 ? '전' : '후',
      semanticLabel: '사진 ${i + 1}',
      video: video && i == n - 1,
    ),
];

Future<void> _pump(
  WidgetTester tester,
  List<AppPagerPhoto> photos, {
  ValueChanged<int>? onTap,
  Widget? overlay,
}) => tester.pumpWidget(
  MaterialApp(
    home: Scaffold(
      body: Center(
        child: AppPhotoPager(photos: photos, onTap: onTap, overlay: overlay),
      ),
    ),
  ),
);

void main() {
  testWidgets('사진이 없으면 회색 자리 하나만 — 페이저 글자도 없다', (tester) async {
    await _pump(tester, const []);

    expect(find.byType(PageView), findsNothing);
    expect(find.textContaining(' / '), findsNothing);
  });

  testWidgets('가운데 사진을 누르면 그 자리를 알리고, 옆 사진을 누르면 그리로 넘어간다', (tester) async {
    final taps = <int>[];
    await _pump(tester, _photos(3), onTap: taps.add);
    expect(find.text('01 / 03'), findsOneWidget);

    await tester.tap(find.bySemanticsLabel('사진 1'));
    await tester.pumpAndSettle();
    expect(taps, [0]);

    await tester.tap(find.bySemanticsLabel('사진 2'));
    await tester.pumpAndSettle();
    expect(taps, [0], reason: '옆 사진은 넘기기만 한다');
    expect(find.text('02 / 03'), findsOneWidget);

    await tester.tap(find.bySemanticsLabel('사진 2'));
    await tester.pumpAndSettle();
    expect(taps, [0, 1]);
  });

  testWidgets('밀어 넘기면 페이저 글자가 따라간다', (tester) async {
    await _pump(tester, _photos(4));

    await tester.drag(find.byType(PageView), const Offset(-300, 0));
    await tester.pumpAndSettle();

    expect(find.text('01 / 04'), findsNothing);
    expect(find.textContaining(' / 04'), findsOneWidget);
  });

  testWidgets('이름 카드 위에서 누르거나 밀어도 넘기기에 닿는다', (tester) async {
    final taps = <int>[];
    await _pump(
      tester,
      _photos(3),
      onTap: taps.add,
      overlay: const AppGlassCard(child: Text('두부 · 골든두들')),
    );

    await tester.tap(find.text('두부 · 골든두들'));
    await tester.pumpAndSettle();
    expect(taps, [0]);

    await tester.drag(find.text('두부 · 골든두들'), const Offset(-300, 0));
    await tester.pumpAndSettle();
    expect(find.text('01 / 03'), findsNothing);
  });

  testWidgets('전/후 알약을 얹고, 영상이면 재생 표시를 얹는다', (tester) async {
    await _pump(tester, _photos(2, video: true));

    expect(find.text('전'), findsOneWidget);
    expect(find.text('후'), findsOneWidget);
    expect(find.byIcon(Icons.play_circle_fill), findsOneWidget);
  });

  testWidgets('사진이 줄어 지금 자리가 없어지면 마지막 사진으로 간다', (tester) async {
    await _pump(tester, _photos(3));
    await tester.tap(find.bySemanticsLabel('사진 2'));
    await tester.pumpAndSettle();
    await tester.tap(find.bySemanticsLabel('사진 3'));
    await tester.pumpAndSettle();
    expect(find.text('03 / 03'), findsOneWidget);

    await _pump(tester, _photos(2));
    await tester.pumpAndSettle();

    expect(find.text('02 / 02'), findsOneWidget);
  });

  testWidgets('AppPhotoPager 골든 — 가운데 크게, 양옆 기울어, 이름 카드와 페이저', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      SizedBox(
        width: 390,
        child: AppPhotoPager(
          photos: _photos(3),
          overlay: const SizedBox(
            width: 190,
            child: AppGlassCard(
              padding: EdgeInsets.symmetric(horizontal: 15, vertical: 11),
              child: Text('두부 · 골든두들 · 12.4kg'),
            ),
          ),
        ),
      ),
    );
    await tester.runAsync(
      () => precacheImage(_image, tester.element(target)),
    );
    await tester.pumpAndSettle();

    await expectLater(target, matchesGoldenFile('goldens/app_photo_pager.png'));
  });
}

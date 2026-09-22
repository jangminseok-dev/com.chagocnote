import 'package:chagocnote/design/widgets/app_photo_tile.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('count를 주면 숫자가 표시된다', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Center(child: AppPhotoTile(image: null, count: 4)),
      ),
    );

    expect(find.text('4'), findsOneWidget);
  });

  testWidgets('count가 없으면 숫자를 표시하지 않는다', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: Center(child: AppPhotoTile(image: null))),
    );

    expect(find.text('4'), findsNothing);
  });
}

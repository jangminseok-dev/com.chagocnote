import 'package:chagocnote/design/widgets/app_photo_fan.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';
import '../support/upload_fakes.dart';

final _image = FakeMediaImages().image;

void main() {
  testWidgets('넷을 넘게 받아도 넷만 그린다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Center(
          child: SizedBox(
            width: 320,
            child: AppPhotoFan(images: List.filled(6, _image)),
          ),
        ),
      ),
    );

    expect(find.byType(Transform), findsNWidgets(AppPhotoFan.max * 2));
  });

  testWidgets('AppPhotoFan 골든 — 네 장을 부채꼴로', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      SizedBox(width: 320, child: AppPhotoFan(images: List.filled(4, _image))),
    );
    await tester.runAsync(
      () => precacheImage(_image, tester.element(target)),
    );
    await tester.pumpAndSettle();

    await expectLater(target, matchesGoldenFile('goldens/app_photo_fan.png'));
  });
}

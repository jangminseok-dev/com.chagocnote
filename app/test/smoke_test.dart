import 'package:chagocnote/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('앱이 뜨고 이름이 보인다', (tester) async {
    await tester.pumpWidget(const BootstrapApp());
    expect(find.text('차곡노트'), findsOneWidget);
  });
}

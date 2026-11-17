import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/features/customer/screens/form_text_edit_screens.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../../support/customer_test_app.dart';
import '../../../../support/fake_http_client_adapter.dart';
import '../../../../support/visit_fixtures.dart';
import '../../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 23))];

class _Server {
  _Server({String? message}) : current = revisitSettingsJson(message: message) {
    backend = VisitTestBackend({
      'GET /v1/shops/3/revisit-settings': (o, b) =>
          FakeResponse(statusCode: 200, data: current),
      'PUT /v1/shops/3/revisit-settings': (o, body) {
        final sent = bodyOf(body);
        puts.add(sent);
        current = {...current, ...sent};
        return FakeResponse(statusCode: 200, data: current);
      },
    });
  }

  late final VisitTestBackend backend;
  Map<String, dynamic> current;
  final puts = <Map<String, dynamic>>[];
}

Future<Closed<Object?>> _open(WidgetTester tester, _Server server) async {
  final setup = CustomerTestSetup(server.backend.call, overrides: _today);
  addTearDown(setup.container.dispose);
  useTallView(tester, height: 1400);
  return pushOnHome<Object?>(tester, setup, '/settings/revisit-message');
}

String _input(WidgetTester tester) =>
    tester.widget<TextField>(find.byKey(FormTextEdit.inputKey)).controller!.text;

void main() {
  testWidgets('처음 글로 열리고, 칩은 이름표로 보이며 누르면 커서 자리에 그 자리를 넣는다', (tester) async {
    await _open(tester, _Server());

    expect(find.byKey(ScreenKeys.revisitMessage), findsOneWidget);
    expect(_input(tester), contains('{아이}'));
    for (final label in [
      AppStrings.revisitChipPet,
      AppStrings.revisitChipWeeks,
      AppStrings.revisitChipShop,
    ]) {
      expect(find.text(label), findsOneWidget);
    }
    // 보호자가 받는 모습에는 예시 아이 이름과 기본 간격 주가 들어 있다.
    final preview = find.descendant(
      of: find.byKey(FormTextEdit.previewKey),
      matching: find.byType(Text),
    );
    final shown = tester.widget<Text>(preview).data!;
    expect(shown.contains(AppStrings.revisitSamplePet), isTrue);
    expect(shown.contains('4주'), isTrue);

    await tester.enterText(find.byKey(FormTextEdit.inputKey), '');
    await tester.pump();
    await tester.tap(find.text(AppStrings.revisitChipPet));
    await tester.pump();
    expect(_input(tester), '{아이}');
  });

  testWidgets('빈 글은 저장하지 않고 까닭을 말한다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await tester.enterText(find.byKey(FormTextEdit.inputKey), '   ');
    await tester.pump();
    await tester.ensureVisible(find.byKey(FormTextEdit.saveKey));
    await tester.tap(find.byKey(FormTextEdit.saveKey));
    await settle(tester);

    expect(server.puts, isEmpty);
    expect(find.text(AppStrings.revisitMessageEmpty), findsOneWidget);
  });

  testWidgets('저장하면 글 하나만 보내고 닫는다', (tester) async {
    final server = _Server();
    final closed = await _open(tester, server);

    await tester.enterText(find.byKey(FormTextEdit.inputKey), '{아이} 미용할 때가 됐어요');
    await tester.pump();
    await tester.ensureVisible(find.byKey(FormTextEdit.saveKey));
    await tester.tap(find.byKey(FormTextEdit.saveKey));
    await settle(tester);

    expect(server.puts, [
      {'revisit_message': '{아이} 미용할 때가 됐어요'},
    ]);
    expect(closed.closed, isTrue);
  });

  testWidgets('고친 글이 있으면 [처음 글로 돌아가기]로 null 을 보낸다', (tester) async {
    final server = _Server(message: '{아이} 미용할 때가 됐어요');
    await _open(tester, server);

    await tester.ensureVisible(find.byKey(FormTextEdit.resetKey));
    await tester.tap(find.byKey(FormTextEdit.resetKey));
    await settle(tester);

    expect(server.puts, [
      {'revisit_message': null},
    ]);
  });
}

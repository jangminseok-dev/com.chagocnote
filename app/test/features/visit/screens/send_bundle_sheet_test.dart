// 보낼 것 시트(⑪-B) — 예약에 보호자에게 보낼 글을 토막으로 보이고, 고치고 빼고, 공유 한 번으로 보낸다.
import 'package:chagocnote/core/proxy/share_sheet.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_sheet.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/screens/send_bundle_sheet.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_share_sheet.dart';
import '../../../support/form_settings_fixtures.dart';

const _reservation = BundlePart(kind: 'reservation', text: '예약이 접수됐어요.\n11월 17일(화) 오후 2:30');
const _consent = BundlePart(kind: 'consent', text: '동의서를 읽고 서명해 주세요.\n$fakeBundleUrl');

Future<({FakeShareSheet share, List<bool?> closed})> _open(WidgetTester tester, List<BundlePart> parts) async {
  tester.view.physicalSize = const Size(390, 1600);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  final share = FakeShareSheet();
  final closed = <bool?>[];
  await tester.pumpWidget(ProviderScope(
    overrides: [shareSheetProvider.overrideWithValue(share)],
    child: MaterialApp(
      home: Scaffold(
        body: Builder(
          builder: (context) => TextButton(
            onPressed: () async => closed.add(
              await AppSheet.show<bool>(context, builder: (_) => SendBundleSheet(parts: parts)),
            ),
            child: const Text('열기'),
          ),
        ),
      ),
    ),
  ));
  await tester.tap(find.text('열기'));
  await tester.pumpAndSettle();
  return (share: share, closed: closed);
}

Future<void> _send(WidgetTester tester) async {
  await tester.tap(find.byKey(SendBundleSheet.sendKey));
  await tester.pumpAndSettle();
}

Future<void> _close(WidgetTester tester) async {
  await tester.tap(find.text(AppStrings.close));
  await tester.pumpAndSettle();
}

AppButton _sendButton(WidgetTester tester) => tester.widget<AppButton>(find.byKey(SendBundleSheet.sendKey));

void main() {
  testWidgets('토막마다 이름과 글이 보이고 [보내기] 한 번으로 빈 줄을 사이에 두고 이어 보낸다', (tester) async {
    final s = await _open(tester, const [_reservation, _consent]);

    expect(find.text(AppStrings.bundleSheetTitle), findsOneWidget);
    expect(find.text(AppStrings.bundlePartReservation), findsOneWidget);
    expect(find.text(AppStrings.bundlePartConsent), findsOneWidget);
    await _send(tester);

    expect(s.share.shared, ['${_reservation.text}\n\n${_consent.text}']);
    // 공유 창에서 취소했는지 앱은 모른다 — 시트가 남아 다시 보낼 수 있고, 닫는 것은 사장이 한다.
    expect(s.closed, isEmpty);
    expect(_sendButton(tester).label, AppStrings.bundleSendAgain);
    await _close(tester);
    expect(s.closed, [true]);
  });

  testWidgets('보낸 뒤에도 고친 글이 남아 다시 보낼 수 있다', (tester) async {
    final s = await _open(tester, const [_reservation]);
    await tester.enterText(find.byKey(const ValueKey('bundle-part-reservation')), '고친 글');

    await _send(tester);
    await _send(tester);

    expect(s.share.shared, ['고친 글', '고친 글']);
    expect(find.text(AppStrings.bundleLater), findsNothing);
  });

  testWidgets('작은 폰에서 키보드가 올라와도 [보내기]와 닫는 버튼이 가려지지 않는다', (tester) async {
    final s = await _open(tester, const [_reservation, _consent]);
    tester.view.physicalSize = const Size(375, 667);
    tester.view.viewInsets = const FakeViewPadding(bottom: 260);
    addTearDown(tester.view.resetViewInsets);
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(tester.getRect(find.byKey(SendBundleSheet.sendKey)).bottom, lessThanOrEqualTo(667 - 260));
    expect(tester.getRect(find.text(AppStrings.bundleLater)).bottom, lessThanOrEqualTo(667 - 260));
    expect(s.share.shared, isEmpty);
  });

  testWidgets('뺀 토막은 나가지 않고 다시 넣을 수 있다', (tester) async {
    final s = await _open(tester, const [_reservation, _consent]);

    await tester.tap(find.byKey(const ValueKey('bundle-toggle-consent')));
    await tester.pump();
    expect(find.descendant(of: find.byKey(const ValueKey('bundle-toggle-consent')),
        matching: find.text(AppStrings.bundleRestore)), findsOneWidget);
    await _send(tester);
    expect(s.share.shared.single, _reservation.text);
  });

  testWidgets('고친 글이 나가고 [처음 글로]로 되돌릴 수 있다', (tester) async {
    final s = await _open(tester, const [_reservation]);

    expect(find.byKey(const ValueKey('bundle-reset-reservation')), findsNothing);
    await tester.enterText(find.byKey(const ValueKey('bundle-part-reservation')), '내일 봬요');
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('bundle-reset-reservation')));
    await tester.pump();
    await tester.enterText(find.byKey(const ValueKey('bundle-part-reservation')), '  내일 2시에 봬요  ');
    await _send(tester);

    expect(s.share.shared.single, '내일 2시에 봬요');
  });

  testWidgets('전부 빼거나 비우면 [보내기]가 눌리지 않고 까닭을 말한다', (tester) async {
    final s = await _open(tester, const [_reservation]);

    await tester.enterText(find.byKey(const ValueKey('bundle-part-reservation')), '   ');
    await tester.pump();

    expect(_sendButton(tester).onPressed, isNull);
    expect(find.text(AppStrings.bundleEmpty), findsOneWidget);
    expect(s.share.shared, isEmpty);
  });

  testWidgets('모르는 종류의 토막도 글 그대로 싣는다 — 이름표만 없다', (tester) async {
    final s = await _open(tester, const [BundlePart(kind: 'deposit', text: '예약금은 3만 원이에요')]);

    expect(find.byKey(const ValueKey('bundle-part-deposit')), findsOneWidget);
    await _send(tester);
    expect(s.share.shared.single, '예약금은 3만 원이에요');
  });

  testWidgets('공유가 실패하면 시트가 남고 고친 글도 남아 다시 누를 수 있다', (tester) async {
    final s = await _open(tester, const [_reservation]);
    await tester.enterText(find.byKey(const ValueKey('bundle-part-reservation')), '고친 글');
    s.share.error = Exception('채널 오류');

    await _send(tester);

    expect(find.text(AppStrings.bundleShareFailed), findsOneWidget);
    expect(s.closed, isEmpty);
    s.share.error = null;
    await _send(tester);
    expect(s.share.shared, ['고친 글']);
    await _close(tester);
    expect(s.closed, [true]);
  });

  testWidgets('[나중에]는 보내지 않고 닫는다', (tester) async {
    final s = await _open(tester, const [_reservation]);

    await tester.tap(find.text(AppStrings.bundleLater));
    await tester.pumpAndSettle();

    expect(s.share.shared, isEmpty);
    expect(s.closed, [false]);
  });
}

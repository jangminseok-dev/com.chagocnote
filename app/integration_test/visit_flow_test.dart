// ③-A2 Task 12 Step 3 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해 완료 기준
// 12개를 확인한다. 확인마다 스크린샷을 찍고, 단언이 실패해도 다음 확인으로
// 넘어가며, 마지막에 결과를 모아 찍는다.
//
// 실행(app/ 에서):
//   flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/visit_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080
// 선택: --dart-define=ONLY=1,2 (그 확인만), --dart-define=RUN=1 (다시 돌릴 때 날짜·시각을 옮긴다)

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/tokens/app_colors.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_chip.dart';
import 'package:chagocnote/design/widgets/app_dashed_tile.dart';
import 'package:chagocnote/design/widgets/app_icon_toggle.dart';
import 'package:chagocnote/design/widgets/pressable.dart';
import 'package:chagocnote/features/customer/screens/family_card_view.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/screens/visit_labels.dart';
import 'package:chagocnote/features/visit/state/calendar_selection.dart';
import 'package:chagocnote/features/visit/state/day_view_mode.dart';
import 'package:chagocnote/features/visit/state/visit_commands.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:chagocnote/main.dart' as app;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:integration_test/integration_test.dart';

const run = int.fromEnvironment('RUN');
const only = String.fromEnvironment('ONLY');
const shopId = 18;
const ownerName = 'vflow-owner-1790178513';
const staffName = 'vflow-staff-1790178513';

late IntegrationTestWidgetsFlutterBinding binding;
late WidgetTester t;
final results = <String>[];
String current = '-';

// 확인끼리 넘겨 쓰는 것.
String? newCustomerName;
String? newCustomerTail;

DateTime get today {
  final n = DateTime.now();
  return DateTime(n.year, n.month, n.day);
}

DateTime plusDays(int days) => DateTime(today.year, today.month, today.day + days);
String hh(int hour) => '${hour.toString().padLeft(2, '0')}:00';

ProviderContainer get container =>
    ProviderScope.containerOf(t.element(find.byType(App)));
GoRouter get router => container.read(routerProvider);

final softFails = <String>[];

/// 단언이 틀려도 그 확인을 계속한다 — 확인이 끝날 때 실패로 적는다.
void soft(bool ok, String what) {
  if (!ok) {
    softFails.add(what);
    note('어긋남: $what');
  }
}

void note(String text) {
  results.add('NOTE $current :: $text');
  debugPrint('NOTE $current :: $text');
}

void drain() {
  Object? ex;
  while ((ex = t.takeException()) != null) {
    final line = ex.toString().split('\n').take(6).join(' / ');
    results.add('EXC $current :: $line');
    debugPrint('EXC $current :: $line');
  }
}

Future<void> pumpFor(Duration d) async {
  final end = DateTime.now().add(d);
  while (DateTime.now().isBefore(end)) {
    await t.pump(const Duration(milliseconds: 50));
    drain();
  }
}


Future<void> shot(String name) async {
  await pumpFor(const Duration(milliseconds: 400));
  try {
    await binding.takeScreenshot(name);
  } catch (e) {
    debugPrint('스크린샷 실패 $name: $e');
  }
}

Finder btn(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);
Finder btnWhere(bool Function(String) f) =>
    find.byWidgetPredicate((w) => w is AppButton && f(w.label));
Finder p(String label) =>
    find.byWidgetPredicate((w) => w is Pressable && w.semanticLabel == label);
Finder pWhere(bool Function(String) f) => find.byWidgetPredicate(
  (w) => w is Pressable && w.semanticLabel != null && f(w.semanticLabel!),
);
Finder chip(String label) =>
    find.byWidgetPredicate((w) => w is AppChip && w.label == label);

Future<void> waitFor(
  Finder f, {
  Duration timeout = const Duration(seconds: 20),
}) async {
  final end = DateTime.now().add(timeout);
  while (true) {
    await t.pump(const Duration(milliseconds: 50));
    drain();
    if (f.evaluate().isNotEmpty) return;
    if (DateTime.now().isAfter(end)) {
      throw TestFailure('보이지 않는다: ${f.describeMatch(Plurality.zero)}');
    }
  }
}

Future<void> waitGone(
  Finder f, {
  Duration timeout = const Duration(seconds: 20),
}) async {
  final end = DateTime.now().add(timeout);
  while (true) {
    await t.pump(const Duration(milliseconds: 50));
    drain();
    if (f.evaluate().isEmpty) return;
    if (DateTime.now().isAfter(end)) {
      throw TestFailure('사라지지 않는다: ${f.describeMatch(Plurality.one)}');
    }
  }
}

Future<void> waitEnabled(Finder f) async {
  final end = DateTime.now().add(const Duration(seconds: 20));
  while (true) {
    await t.pump(const Duration(milliseconds: 50));
    drain();
    if (f.evaluate().isNotEmpty &&
        t.widget<AppButton>(f.first).onPressed != null &&
        !t.widget<AppButton>(f.first).busy) {
      return;
    }
    if (DateTime.now().isAfter(end)) {
      throw TestFailure('버튼이 켜지지 않는다: ${f.describeMatch(Plurality.one)}');
    }
  }
}

/// 보이는 세로 스크롤 중 맨 위 화면의 것.
Finder? mainScroll() {
  final all = find.byType(Scrollable).evaluate().where((e) {
    final w = e.widget as Scrollable;
    return w.axisDirection == AxisDirection.down;
  }).toList();
  if (all.isEmpty) return null;
  final last = all.last;
  return find.byElementPredicate((e) => e == last);
}

/// 찾을 때까지 기다리고, 없으면 조금씩 내려 본다. 찾으면 보이게 옮긴다.
Future<void> reveal(
  Finder f, {
  Duration timeout = const Duration(seconds: 20),
}) async {
  final start = DateTime.now();
  var drags = 0;
  while (true) {
    await t.pump(const Duration(milliseconds: 50));
    drain();
    if (f.evaluate().isNotEmpty) {
      await t.ensureVisible(f.first);
      await t.pump(const Duration(milliseconds: 150));
      return;
    }
    final waited = DateTime.now().difference(start);
    if (waited > timeout) {
      throw TestFailure('보이지 않는다: ${f.describeMatch(Plurality.zero)}');
    }
    if (waited > const Duration(seconds: 3) && drags < 10) {
      final s = mainScroll();
      if (s != null) {
        await t.drag(s, const Offset(0, -300), warnIfMissed: false);
        drags++;
        await t.pump(const Duration(milliseconds: 300));
      }
    }
  }
}

Future<void> tap(
  Finder f, {
  Duration after = const Duration(milliseconds: 500),
  bool last = false,
}) async {
  await reveal(f);
  await t.tap(last ? f.last : f.first);
  await pumpFor(after);
}

Future<void> longPress(Finder f) async {
  await reveal(f);
  await t.longPress(f.first);
  await pumpFor(const Duration(milliseconds: 600));
}

/// 보이는 단계(IndexedStack 의 앞면)만.
Finder onStage(Finder f) => f.hitTestable();

Future<void> closeSheets() async {
  for (var i = 0; i < 4; i++) {
    final navs = find.byType(Navigator).evaluate().toList();
    if (navs.isEmpty) return;
    final nav = (navs.first as StatefulElement).state as NavigatorState;
    var popped = false;
    nav.popUntil((route) {
      if (route is PopupRoute) {
        popped = true;
        return false;
      }
      return true;
    });
    if (!popped) return;
    await pumpFor(const Duration(milliseconds: 400));
  }
}

Future<void> goHome() async {
  try {
    await closeSheets();
    router.go('/home');
    await pumpFor(const Duration(milliseconds: 900));
    if (p(AppStrings.tabCalendar).evaluate().isNotEmpty &&
        find.byKey(ScreenKeys.home).evaluate().isNotEmpty) {
      await t.tap(p(AppStrings.tabCalendar).first);
      await pumpFor(const Duration(milliseconds: 600));
    }
  } catch (e) {
    debugPrint('홈으로 못 감: $e');
  }
}

Future<void> step(String id, String title, Future<void> Function() body) async {
  if (only.isNotEmpty && !only.split(',').contains(id)) return;
  current = id;
  debugPrint('STEP $id 시작 — $title');
  try {
    softFails.clear();
    await body();
    if (softFails.isNotEmpty) throw TestFailure('어긋남 ${softFails.length}건: ${softFails.join(' | ')}');
    results.add('PASS $id $title');
    debugPrint('STEP $id 통과');
  } catch (e, st) {
    final msg = e.toString().split('\n').take(8).join(' / ');
    results.add('FAIL $id $title :: $msg');
    debugPrint('STEP $id 실패: $e\n$st');
    await shot('$id-FAIL');
  }
  drain();
  await goHome();
}

// ── 앱 흐름 도우미 ──────────────────────────────────────────────

Future<void> logout() async {
  await closeSheets();
  router.push('/settings/account');
  await tap(btn(AppStrings.logout));
  await waitFor(find.byKey(ScreenKeys.login), timeout: const Duration(seconds: 30));
  await pumpFor(const Duration(milliseconds: 500));
}

Future<void> login(String name) async {
  await waitFor(find.byKey(ScreenKeys.login), timeout: const Duration(seconds: 30));
  await t.enterText(find.byType(TextField).first, name);
  await pumpFor(const Duration(milliseconds: 300));
  await tap(btn(AppStrings.devSignIn));
  await waitFor(find.byKey(ScreenKeys.home), timeout: const Duration(seconds: 30));
  await pumpFor(const Duration(seconds: 1));
}

Future<void> goCalendarTab() async {
  if (find.byKey(ScreenKeys.home).evaluate().isEmpty ||
      find.byKey(ScreenKeys.registerVisit).evaluate().isNotEmpty ||
      find.byKey(ScreenKeys.day).evaluate().isNotEmpty) {
    await goHome();
  }
  if (p(AppStrings.tabCalendar).evaluate().isNotEmpty) {
    await tap(p(AppStrings.tabCalendar));
  }
}

/// 캘린더 탭에서 [date]로 달을 옮기고 그 칸을 누른다.
Future<void> selectDate(DateTime date) async {
  await goCalendarTab();
  for (var i = 0; i < 24; i++) {
    final sel = container.read(selectedDateProvider);
    final diff = (date.year - sel.year) * 12 + date.month - sel.month;
    if (diff == 0) break;
    await tap(p(diff > 0 ? AppStrings.nextMonth : AppStrings.prevMonth));
  }
  await tap(p(dayLabel(date)), after: const Duration(milliseconds: 900));
}

Future<void> openPreviewDay(DateTime date) async {
  await tap(p(AppStrings.dayHeading(date.day, date.weekday)));
  await waitFor(find.byKey(ScreenKeys.day));
  await pumpFor(const Duration(milliseconds: 1200));
}

/// ① 에서 고객을 찾아 고른다.
Future<void> pickCustomer(String query, bool Function(String) match) async {
  await waitFor(find.text(AppStrings.reserveWhoTitle));
  final field = find.byType(TextField).first;
  await waitFor(field);
  await t.enterText(field, query);
  await pumpFor(const Duration(milliseconds: 1200));
  await tap(pWhere(match));
  await waitFor(find.text(AppStrings.reserveWhenTitle));
}

bool isKim(String l) => l.startsWith('김민지 ');

int? parseDuration(String s) {
  final m = RegExp(r'^(?:(\d+)시간)?\s*(?:(\d+)분)?$').firstMatch(s.trim());
  if (m == null || (m.group(1) == null && m.group(2) == null)) return null;
  return int.parse(m.group(1) ?? '0') * 60 + int.parse(m.group(2) ?? '0');
}

/// 예약 폼의 소요 값.
int durationNow() {
  final row = find.ancestor(of: p(AppStrings.longer), matching: find.byType(Row)).first;
  for (final e in find.descendant(of: row, matching: find.byType(Text)).evaluate()) {
    final d = (e.widget as Text).data;
    if (d != null) {
      final v = parseDuration(d);
      if (v != null) return v;
    }
  }
  throw TestFailure('소요 값을 못 읽었다');
}

Finder saveReservationBtn() => btnWhere((l) => l.startsWith('예약 저장'));

/// 홈에서 [date]를 고르고 + → ① → ② → 저장까지.
Future<void> reserve({
  required DateTime date,
  required String query,
  required bool Function(String) family,
  required List<String> pets,
  required String at,
  int? duration,
}) async {
  await selectDate(date);
  await tap(p(AppStrings.addReservation));
  await pickCustomer(query, family);
  for (final pet in pets) {
    await waitFor(p(pet));
    if (t.widget<Pressable>(p(pet).first).selected != true) await tap(p(pet));
  }
  await tap(p(at));
  if (duration != null) {
    await pumpFor(const Duration(milliseconds: 800));
    var d = durationNow();
    while (d > duration) {
      if (d - duration >= 30) {
        await longPress(p(AppStrings.shorter));
      } else {
        await tap(p(AppStrings.shorter), after: const Duration(milliseconds: 200));
      }
      d = durationNow();
    }
    while (d < duration) {
      await tap(p(AppStrings.longer), after: const Duration(milliseconds: 200));
      d = durationNow();
    }
  }
  await waitEnabled(saveReservationBtn());
  await tap(saveReservationBtn());
  await waitGone(find.byKey(ScreenKeys.registerVisit));
  await pumpFor(const Duration(milliseconds: 800));
}

/// 하루 화면의 [hour] 시 묶음 카드.
Finder cardAt(String at, String title) =>
    find.ancestor(of: find.text(at), matching: p(title));

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('③-A2 완료 기준 12개', timeout: const Timeout(Duration(minutes: 45)), (
    tester,
  ) async {
    t = tester;
    app.main();
    final end = DateTime.now().add(const Duration(seconds: 40));
    while (DateTime.now().isBefore(end)) {
      await t.pump(const Duration(milliseconds: 100));
      drain();
      if (find.byKey(ScreenKeys.login).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.home).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.invite).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.shopSelect).evaluate().isNotEmpty) {
        break;
      }
    }
    if (find.byKey(ScreenKeys.login).evaluate().isEmpty) await logout();
    await login(ownerName);
    await shot('00-home-owner');

    final d1 = plusDays(5 + run * 7); // 두 마리 예약을 잡는 앞날(처음은 9/29 화)
    var nextOf3 = plusDays(28); // 3 이 서버 초안의 날짜로 바꾼다
    final h3 = const [16, 17, 15, 14, 12][run];

    // ── 1 ──
    await step('1', '두 마리 예약 → 달력 점선 + 2, 미리보기', () async {
      await selectDate(d1);
      await tap(p(AppStrings.addReservation));
      await waitFor(find.text(AppStrings.reserveWhoTitle));
      final field = find.byType(TextField).first;
      await t.enterText(field, '8513');
      await pumpFor(const Duration(milliseconds: 1500));
      await waitFor(pWhere(isKim));
      final tailCount = find.byType(Pressable).evaluate().where((e) {
        final l = (e.widget as Pressable).semanticLabel ?? '';
        return l.contains(' ') && !l.startsWith('뒤로');
      }).length;
      note('뒷자리 8513 검색 결과에 김민지가 보인다(보이는 이름표 수 $tailCount)');
      await shot('01a-search-tail');
      await t.enterText(field, 'ㄱㅁㅈ');
      await pumpFor(const Duration(milliseconds: 1500));
      await waitFor(pWhere(isKim));
      await shot('01b-search-chosung');
      await tap(pWhere(isKim));
      await waitFor(find.text(AppStrings.reserveWhenTitle));
      await tap(p('콩이'));
      await tap(p('두부'));
      await tap(p('14:00'));
      final save = btn(AppStrings.saveReservation('${dayLabel(d1)} 14:00'));
      await waitEnabled(save);
      await shot('01c-form-two-pets');
      await tap(save);
      await waitGone(find.byKey(ScreenKeys.registerVisit));
      await pumpFor(const Duration(milliseconds: 1500));
      final dashed = find.descendant(
        of: p(dayLabel(d1)),
        matching: find.byType(AppDashedTile),
      );
      await waitFor(dashed);
      final count = t.widget<AppDashedTile>(dashed).count;
      note('${dayLabel(d1)} 칸 점선 수 = $count');
      final names = find.text('콩이 · 두부').evaluate().isNotEmpty
          ? '콩이 · 두부'
          : find.text('두부 · 콩이').evaluate().isNotEmpty
          ? '두부 · 콩이'
          : null;
      note('미리보기 이름 = $names, 고른 날 = ${container.read(selectedDateProvider)}');
      await shot('01d-calendar-dashed-preview');
      expect(count, greaterThanOrEqualTo(2));
      expect(names, isNotNull);
    });

    // ── 2 ──
    await step('2', '하루 목록 ↔ 시간표, 기억', () async {
      await selectDate(d1);
      await openPreviewDay(d1);
      await waitFor(find.byType(AppIconToggle));
      if (t.widget<AppIconToggle>(find.byType(AppIconToggle)).currentIndex != 0) {
        note('처음 열었을 때 이미 시간표였다(앞선 실행이 남긴 값) — 목록으로 되돌리고 시작');
        await tap(p(AppStrings.viewAsList));
      }
      await shot('02a-day-list');
      await tap(p(AppStrings.viewAsTimeline), after: const Duration(seconds: 1));
      await shot('02b-day-timeline');
      final saved = await container.read(prefsStoreProvider).readDayViewMode();
      note('시간표로 바꾼 뒤 PrefsStore.readDayViewMode() = $saved');
      expect(saved, 'timeline');
      await tap(p(AppStrings.back));
      await waitFor(find.byKey(ScreenKeys.home));
      // 앱을 다시 켠 것처럼 보기 방식을 기기 저장소에서 다시 읽게 한다.
      container.invalidate(dayViewModeProvider);
      await pumpFor(const Duration(milliseconds: 500));
      await openPreviewDay(d1);
      final idx = t.widget<AppIconToggle>(find.byType(AppIconToggle)).currentIndex;
      note('닫았다 다시 연 하루 화면(보기 방식 다시 읽음)의 토글 = ${idx == 1 ? '시간표' : '목록'}');
      await shot('02c-day-reopened-timeline');
      expect(idx, 1);
      await tap(p(AppStrings.viewAsList), after: const Duration(seconds: 1));
      final back = await container.read(prefsStoreProvider).readDayViewMode();
      note('목록으로 되돌린 뒤 저장값 = $back');
      await shot('02d-day-list-again');
      expect(back, 'list');
    });

    // ── 3 ──
    await step('3', '시작 → 완료 시트 → 완료하고 다음 예약', () async {
      await reserve(
        date: today,
        query: '8513',
        family: isKim,
        pets: ['콩이', '두부'],
        at: hh(h3),
      );
      await openPreviewDay(today);
      final card = cardAt(hh(h3), '콩이 · 두부');
      await waitFor(card);
      await tap(find.descendant(of: card, matching: btn(AppStrings.actionStart)));
      await waitFor(
        find.descendant(of: card, matching: btn(AppStrings.actionCompleteShort)),
      );
      await shot('03a-group-in-progress');
      await tap(
        find.descendant(of: card, matching: btn(AppStrings.actionCompleteShort)),
      );
      await waitFor(find.text(AppStrings.completeTitle));
      await pumpFor(const Duration(milliseconds: 800));
      final arrow = find.textContaining('→ ').evaluate().map((e) => (e.widget as Text).data!).toList();
      final weeks = find.textContaining('주 뒤').evaluate().map((e) => (e.widget as Text).data).toList();
      note('완료 시트 미리보기 = $arrow, 안내 = $weeks');
      await shot(run >= 3 ? '03b-rerun$run' : '03b-complete-sheet');
      soft(arrow.isNotEmpty, '완료 시트에 다음 예약 미리보기("→ …")가 없다');
      soft(weeks.isNotEmpty, '완료 시트에 "N주 뒤 …" 안내가 없다');
      await tap(btn(AppStrings.completeAndNext));
      await waitFor(find.byKey(ScreenKeys.registerVisit));
      final save = saveReservationBtn();
      await waitEnabled(save);
      final label = t.widget<AppButton>(save).label;
      final m = RegExp(r'(\d+)월 (\d+)일 . (\d\d:\d\d)').firstMatch(label)!;
      final month = int.parse(m.group(1)!);
      nextOf3 = DateTime(today.year + (month < today.month ? 1 : 0), month, int.parse(m.group(2)!));
      note('다음 예약 ② 저장 버튼 = "$label" (시각 ${m.group(3)} — 완료한 시각 ${hh(h3)})');
      soft(m.group(3) == hh(h3), '다음 예약 시각이 같은 시각이 아니다');
      final formWhen = label.replaceFirst('예약 저장 · ', '');
      soft(arrow.isNotEmpty && arrow.first == '→ $formWhen', '② 날짜·시각("$formWhen")이 시트 미리보기($arrow)와 다르다');
      final kong = t.widget<Pressable>(p('콩이').first).selected;
      final dubu = t.widget<Pressable>(p('두부').first).selected;
      final menusSel = find.byType(Pressable).evaluate().where((e) {
        final w = e.widget as Pressable;
        return w.selected == true && !['콩이', '두부'].contains(w.semanticLabel) && !(w.semanticLabel ?? '').contains('월 ');
      }).map((e) => (e.widget as Pressable).semanticLabel).toList();
      note('다음 예약 ② — 콩이 선택=$kong, 두부 선택=$dubu, 골라진 칸·메뉴=$menusSel, 소요=${durationNow()}분');
      await shot(run >= 3 ? '03c-rerun$run' : '03c-next-draft-form');
      soft(kong == true, '다음 예약 ②에 콩이가 골라져 있지 않다');
      soft(dubu == true, '다음 예약 ②에 두부가 골라져 있지 않다');
      await tap(save);
      await waitGone(find.byKey(ScreenKeys.registerVisit));
      await pumpFor(const Duration(seconds: 1));
      await shot(run >= 3 ? '03d-rerun$run' : '03d-day-after-complete');
      router.push('/visits/day/${isoDay(nextOf3)}');
      await waitFor(cardAt(hh(h3), '콩이 · 두부'));
      await shot(run >= 3 ? '03e-rerun$run' : '03e-next-reservation-day');
      if (run >= 3) return;

      // 추가 소견: 한 마리만 미용 중으로 되돌려 섞인 가족 카드를 본다(화면은
      // 늘 같은 상태의 묶음 전체를 바꾸므로 앱의 명령을 직접 부른다).
      router.pop();
      await pumpFor(const Duration(milliseconds: 800));
      final dayData = await container.read(visitApiProvider).day(shopId, today);
      final ids = [
        for (final i in dayData.items)
          if (i.visit.startsAt.wall.hour == h3 &&
              i.visit.customer.name == '김민지' &&
              i.visit.status == VisitStatus.completed)
            i.visit.visitId,
      ];
      note('오늘 ${hh(h3)} 김민지 완료 방문 = $ids');
      if (ids.length >= 2) {
        await container
            .read(visitCommandsProvider)
            .transition(shopId, visitIds: [ids.first], action: VisitAction.revert);
        container.invalidate(dayVisitsProvider);
        await pumpFor(const Duration(seconds: 2));
        final mixed = cardAt(hh(h3), '콩이 · 두부');
        final chips = find.descendant(of: mixed, matching: find.byType(AppChip)).evaluate().map((e) => (e.widget as AppChip).label).toList();
        final buttons = find.descendant(of: mixed, matching: find.byType(AppButton)).evaluate().map((e) => (e.widget as AppButton).label).toList();
        note('섞인 가족 카드(한 마리 되돌림) — 칩=$chips, 버튼=$buttons');
        await shot('03f-mixed-family-card');
      }
    });

    // ── 4 ──
    await step('4', '취소 → 사유 → 되돌리기', () async {
      router.push('/visits/day/${isoDay(nextOf3)}');
      final card = cardAt(hh(h3), '콩이 · 두부');
      await tap(card);
      await waitFor(find.byKey(ScreenKeys.visitDetail));
      await tap(btn(AppStrings.actionCancelVisit));
      await waitFor(find.text(AppStrings.cancelReasonTitle));
      await shot('04a-cancel-reason-sheet');
      await tap(btn(AppStrings.reasonCustomerRequest));
      await waitFor(find.text(AppStrings.cancelReasonLabel));
      await waitFor(chip(AppStrings.statusCanceled));
      note('취소 뒤 사유 카드 = ${find.text(AppStrings.reasonCustomerRequest).evaluate().isNotEmpty ? '보호자 요청' : '?'}');
      await shot('04b-canceled-with-reason');
      await tap(p(AppStrings.more));
      await tap(p(AppStrings.actionRevert));
      await waitFor(chip(AppStrings.statusReserved));
      await shot('04c-reverted-reserved');
      expect(find.text(AppStrings.cancelReasonLabel), findsNothing);
    });

    // ── 5 ──
    await step('5', '노쇼 — 지난 방문은 되고, 시각 전은 막힌다', () async {
      final y = plusDays(-1);
      final h5 = 15 + run;
      await reserve(date: y, query: '8513', family: isKim, pets: ['콩이'], at: hh(h5));
      await selectDate(y);
      await openPreviewDay(y);
      await tap(cardAt(hh(h5), '콩이'));
      await waitFor(find.byKey(ScreenKeys.visitDetail));
      await tap(btn(AppStrings.actionNoShow));
      await waitFor(find.text(AppStrings.noShowConfirm));
      await shot('05a-noshow-confirm');
      await tap(btn(AppStrings.actionNoShow), last: true);
      await waitFor(chip(AppStrings.statusNoShow));
      await shot('05b-noshow-done');
      // 시각 전 방문
      await goHome();
      router.push('/visits/day/${isoDay(nextOf3)}');
      await tap(cardAt(hh(h3), '콩이 · 두부'));
      await waitFor(find.byKey(ScreenKeys.visitDetail));
      await tap(btn(AppStrings.actionNoShow));
      await waitFor(find.text(AppStrings.noShowConfirm));
      await tap(btn(AppStrings.actionNoShow), last: true);
      await waitFor(find.textContaining('아직 할 수 없습니다'));
      note('시각 전 노쇼 문구 = ${find.textContaining('아직 할 수 없습니다').evaluate().map((e) => (e.widget as Text).data).first}');
      await shot('05c-noshow-not-yet');
      expect(chip(AppStrings.statusReserved), findsWidgets);
    });

    // ── 7 (6 이 7 의 새 고객을 쓴다) ──
    await step('7', '다른 날에서 [지금 시작], ①에서 [새 고객 등록] → ②', () async {
      final other = plusDays(6 + run * 7);
      await selectDate(other);
      await tap(p(AppStrings.addReservation));
      await waitFor(find.text(AppStrings.reserveWhoTitle));
      await tap(btn(AppStrings.registerNewCustomer));
      await waitFor(find.byKey(ScreenKeys.registerCustomer));
      final digits = (DateTime.now().millisecondsSinceEpoch % 100000000).toString().padLeft(8, '0');
      final phone = '010$digits';
      final tail = digits.substring(4);
      final name = '통합$tail';
      await t.enterText(onStage(find.byType(TextField)).first, phone);
      await pumpFor(const Duration(milliseconds: 1500));
      await waitEnabled(onStage(btn(AppStrings.next)));
      await tap(onStage(btn(AppStrings.next)));
      await waitFor(find.text(AppStrings.registerStepTitle(AppStrings.registerStepOwner, 2)));
      await pumpFor(const Duration(milliseconds: 500));
      await t.enterText(
        onStage(find.widgetWithText(TextField, AppStrings.ownerNameLabel)),
        name,
      );
      await tap(onStage(p(AppStrings.marketingDeclined)));
      await tap(onStage(btn(AppStrings.next)));
      await waitFor(find.text(AppStrings.registerStepTitle(AppStrings.registerStepPet, 3)));
      await pumpFor(const Duration(milliseconds: 500));
      await t.enterText(
        onStage(find.widgetWithText(TextField, AppStrings.petNameLabel)),
        '보리',
      );
      await tap(onStage(p(AppStrings.speciesDog)));
      await tap(onStage(p('푸들')));
      await tap(onStage(p(AppStrings.sexFemale)));
      await tap(onStage(p(AppStrings.neuteredYes)));
      await tap(onStage(p(AppStrings.ageUnknown)));
      await t.enterText(
        onStage(find.widgetWithText(TextField, AppStrings.weightLabel)),
        '3.0',
      );
      await pumpFor(const Duration(milliseconds: 300));
      await tap(onStage(p(AppStrings.noKnownConditions)));
      await shot('07a-register-pet-step');
      await tap(onStage(btn(AppStrings.save)));
      await waitGone(find.byKey(ScreenKeys.registerCustomer));
      await waitFor(find.text(AppStrings.reserveWhenTitle));
      await waitFor(find.text('$name · ··$tail'));
      newCustomerName = name;
      newCustomerTail = tail;
      note('새 고객 $name(뒷자리 $tail) 등록 뒤 그 고객의 ②로 왔다');
      await shot('07b-new-customer-form');
      await reveal(btn(AppStrings.startNow));
      await shot('07c-walkin-button-other-day');
      await tap(btn(AppStrings.startNow));
      await waitGone(find.byKey(ScreenKeys.registerVisit));
      await pumpFor(const Duration(milliseconds: 1500));
      final sel = container.read(selectedDateProvider);
      note('지금 시작 뒤 홈이 고른 날 = $sel (오늘 $today)');
      await shot('07d-home-selects-today');
      soft(sel == today, '지금 시작 뒤 홈이 오늘을 고르지 않았다($sel)');
      await openPreviewDay(today);
      final card = p('보리');
      await waitFor(card);
      final times = find.descendant(of: card.first, matching: find.byType(Text)).evaluate().map((e) => (e.widget as Text).data).toList();
      note('오늘 하루 목록의 보리 카드 = $times (지금 ${DateTime.now()})');
      await shot('07e-day-walkin-in-progress');
      expect(find.descendant(of: card.first, matching: btn(AppStrings.actionCompleteShort)), findsOneWidget);
    });

    // ── 6 ──
    await step('6', '겹침 줄긋기·경고, 쉬는 날, 10분 단위, 소요 ±', () async {
      final tail = newCustomerTail ?? '통합';
      bool isNew(String l) => newCustomerName == null
          ? l.startsWith('통합')
          : l.startsWith('$newCustomerName ');
      await selectDate(d1);
      await tap(p(AppStrings.addReservation));
      await pickCustomer(tail, isNew);
      await waitFor(p('14:00'));
      await pumpFor(const Duration(milliseconds: 800));
      Text slotText(String label) => t.widget<Text>(
        find.descendant(of: p(label).first, matching: find.byType(Text)).first,
      );
      final s14 = slotText('14:00');
      final s11 = slotText('11:00');
      note('겹침 칸 14:00 decoration=${s14.style?.decoration}, color=${s14.style?.color}; 보통 칸 11:00 color=${s11.style?.color}');
      await shot('06a-grid-overlap-strike');
      soft(s14.style?.decoration == TextDecoration.lineThrough, '겹침 칸 14:00 에 줄이 없다');
      await tap(p('14:00'));
      await waitFor(find.text('· ${AppStrings.warningOverlap}'));
      await shot('06b-overlap-warning');
      // 쉬는 요일(월)
      final mon = DateTime(d1.year, d1.month, d1.day - (d1.weekday - 1));
      await tap(p(dayLabel(mon)), after: const Duration(seconds: 1));
      await waitFor(find.text('· ${AppStrings.warningClosedDay}'));
      final f10 = slotText('10:00');
      note('쉬는 날 칸 10:00 color=${f10.style?.color} (secondary=${AppColors.secondary}), decoration=${f10.style?.decoration}');
      await shot('06c-closed-day-faint');
      // 10분 단위
      await longPress(p('15:00'));
      await waitFor(find.text(AppStrings.pickMinuteTitle));
      await shot('06d-minute-sheet');
      await tap(p('15:40'));
      await waitFor(btn(AppStrings.saveReservation('${dayLabel(mon)} 15:40')));
      await shot('06e-minute-picked');
      // 소요 ±
      final d0 = durationNow();
      await tap(p(AppStrings.longer), after: const Duration(milliseconds: 300));
      final d1v = durationNow();
      await longPress(p(AppStrings.longer));
      final d2 = durationNow();
      note('소요 $d0 → [+] $d1v → [+]길게 $d2');
      await shot('06f-duration-steps');
      soft(d1v - d0 == 10, '[+] 한 번이 10분이 아니다');
      soft(d2 - d1v == 30, '[+] 길게가 30분이 아니다');
      // 겹치는 칸으로 되돌아가 저장 — 막지 않는다
      await tap(p(dayLabel(d1)), after: const Duration(seconds: 1));
      await tap(p('14:00'));
      await waitFor(find.text('· ${AppStrings.warningOverlap}'));
      final save = btn(AppStrings.saveReservation('${dayLabel(d1)} 14:00'));
      await waitEnabled(save);
      await tap(save);
      await waitGone(find.byKey(ScreenKeys.registerVisit));
      await selectDate(d1);
      await openPreviewDay(d1);
      await waitFor(find.textContaining(AppStrings.markOverlap));
      await shot('06g-overlap-saved-day');
    });

    // ── 8 ──
    await step('8', '묶음 방문 시간 수정 → 같이 옮기기', () async {
      await selectDate(d1);
      await openPreviewDay(d1);
      await tap(cardAt('14:00', '콩이 · 두부'));
      await waitFor(find.byKey(ScreenKeys.visitDetail));
      await tap(p(AppStrings.more));
      await tap(p(AppStrings.edit));
      await waitFor(find.byKey(ScreenKeys.visitEdit));
      await tap(p('16:00'));
      await waitEnabled(btn(AppStrings.save));
      await shot('08a-edit-form');
      await tap(btn(AppStrings.save));
      await waitFor(find.textContaining('도 같이 옮길까요?'));
      note('질문 = ${find.textContaining('도 같이 옮길까요?').evaluate().map((e) => (e.widget as Text).data).first}');
      await shot('08b-move-together-sheet');
      await tap(btn(AppStrings.moveTogether));
      await waitGone(find.byKey(ScreenKeys.visitEdit));
      await pumpFor(const Duration(seconds: 1));
      await shot('08c-detail-after-move');
      await tap(p(AppStrings.back));
      await waitFor(cardAt('16:00', '콩이 · 두부'));
      await shot('08d-day-moved-together');
      expect(cardAt('14:00', '콩이 · 두부'), findsNothing);
    });

    // ── 9 ──
    await step('9', '최근 방문순, 보호자 탭의 노쇼·다가오는 예약', () async {
      await tap(p(AppStrings.tabCustomers));
      await tap(p(AppStrings.sortLastVisit), after: const Duration(seconds: 2));
      await waitFor(find.byType(FamilyCardView));
      final names = t.widgetList<FamilyCardView>(find.byType(FamilyCardView)).map((w) => w.card.name).take(4).toList();
      note('최근 방문순 앞쪽 = $names');
      await shot('09a-sort-last-visit');
      expect(names.first, '김민지');
      await tap(p('콩이'));
      await waitFor(find.byKey(ScreenKeys.petDetail));
      await tap(p(AppStrings.petTabOwner), after: const Duration(seconds: 1));
      await reveal(find.textContaining('노쇼 '));
      final ns = find.textContaining(RegExp(r'^노쇼 \d+회$')).evaluate().map((e) => (e.widget as Text).data).toList();
      note('보호자 탭 노쇼 값 = $ns, 라벨 "${AppStrings.actionNoShow}" 보임=${find.text(AppStrings.actionNoShow).evaluate().isNotEmpty}');
      await shot('09b-owner-tab-noshow');
      await reveal(find.text(AppStrings.upcomingVisitsLabel));
      await shot('09c-owner-tab-upcoming');
      final upcoming = pWhere((l) => RegExp(r'^\d+월 \d+일 [월화수목금토일]$').hasMatch(l));
      await tap(upcoming);
      await waitFor(find.byKey(ScreenKeys.visitDetail));
      await shot('09d-upcoming-to-detail');
      expect(ns, isNotEmpty);
    });

    // ── 10 ──
    String? origOpens;
    String? origCloses;
    List<String>? origClosedChips;
    Future<void> setTime(String label, String value) async {
      await tap(p(label));
      await waitFor(find.text(AppStrings.pickTimeTitle));
      await tap(p(value.substring(0, 2)));
      await tap(p(value.substring(3, 5)), last: true);
      await tap(btn(AppStrings.confirm));
    }

    String rowValue(String label) {
      final texts = find.descendant(of: p(label), matching: find.byType(Text)).evaluate().map((e) => (e.widget as Text).data!).toList();
      return texts[1];
    }

    Future<void> openSchedule() async {
      await goHome();
      await tap(p(AppStrings.settingsLabel));
      await waitFor(find.byKey(ScreenKeys.settings));
      await tap(p(AppStrings.settingsSchedule));
      await waitFor(find.byKey(ScreenKeys.settingsSchedule));
      await waitFor(p(AppStrings.opensAtLabel));
      await pumpFor(const Duration(milliseconds: 800));
    }

    await step('10', '설정 — 일정·임시 휴무·하루 휴무·메뉴', () async {
      await openSchedule();
      origOpens = rowValue(AppStrings.opensAtLabel);
      origCloses = rowValue(AppStrings.closesAtLabel);
      origClosedChips = [
        for (final d in AppStrings.weekdaysShort)
          if (t.widget<Pressable>(p(d).first).selected == true) d,
      ];
      note('원래 일정 = $origOpens–$origCloses, 쉬는 요일 $origClosedChips');
      await shot('10a-schedule-before');
      await setTime(AppStrings.opensAtLabel, '09:00');
      await setTime(AppStrings.closesAtLabel, '20:00');
      if (t.widget<Pressable>(p('화').first).selected != true) await tap(p('화'));
      await tap(btn(AppStrings.save));
      await waitFor(find.text(AppStrings.saved));
      await shot('10b-schedule-saved');
      // 임시 휴무
      final temp = plusDays(21);
      final field = find.byType(TextField).first;
      await reveal(field);
      final kb = t.widget<TextField>(field).keyboardType;
      note('임시 휴무 날짜 칸 keyboardType = $kb (datetime 기대)');
      await t.tap(field);
      await t.enterText(field, '${temp.year}.${temp.month.toString().padLeft(2, '0')}.${temp.day.toString().padLeft(2, '0')}');
      await pumpFor(const Duration(milliseconds: 500));
      await shot('10c-closed-date-input');
      await tap(btn(AppStrings.addClosedDate));
      await waitFor(find.textContaining(dayLabel(temp)));
      await shot('10d-closed-date-added');
      await tap(p('${AppStrings.delete} ${dayLabel(temp)}'));
      await waitGone(find.textContaining(dayLabel(temp)));
      await shot('10e-closed-date-removed');
      soft(kb == TextInputType.datetime, '임시 휴무 날짜 칸이 datetime 키보드가 아니다($kb)');

      // 달력 휴무(화요일) 와 ② 시간 칸(09~19시)
      final tue = plusDays(19); // 10/13 화
      await selectDate(tue);
      await pumpFor(const Duration(seconds: 1));
      final tueClosed = find.descendant(of: p(dayLabel(tue)), matching: find.text(AppStrings.closedShort)).evaluate().isNotEmpty;
      final prevTue = DateTime(tue.year, tue.month, tue.day - 7);
      final tueClosed2 = find.descendant(of: p(dayLabel(prevTue)), matching: find.text(AppStrings.closedShort)).evaluate().isNotEmpty;
      note('화요일 칸 휴무 — ${dayLabel(tue)}=$tueClosed, ${dayLabel(prevTue)}=$tueClosed2');
      await shot('10f-calendar-tuesday-closed');
      await tap(p(AppStrings.addReservation));
      await pickCustomer('8513', isKim);
      await waitFor(p('09:00'));
      final slots = find.byType(Pressable).evaluate().map((e) => (e.widget as Pressable).semanticLabel ?? '').where((l) => RegExp(r'^\d\d:\d\d$').hasMatch(l)).toList();
      note('영업 09–20 · 화 휴무 뒤 ② 시간 칸 = $slots');
      await shot('10g-form-slots-changed');
      soft(slots.isNotEmpty && slots.first == '09:00', '② 첫 시간 칸이 09:00 이 아니다');
      soft(slots.isNotEmpty && slots.last == '19:00', '② 끝 시간 칸이 19:00 이 아니다');
      soft(tueClosed, '달력 화요일 칸에 휴무가 없다');

      // 하루 화면 ··· → 이 날 휴무
      final off = plusDays(14 + run * 7); // 10/8 목
      await selectDate(off);
      await openPreviewDay(off);
      await tap(p(AppStrings.more));
      await waitFor(p(AppStrings.markClosedDate));
      await shot('10h-day-more-sheet');
      await tap(p(AppStrings.markClosedDate), after: const Duration(seconds: 1));
      await waitFor(find.textContaining(AppStrings.closedDayNote));
      await tap(p(AppStrings.back));
      await waitFor(find.byKey(ScreenKeys.home));
      await pumpFor(const Duration(seconds: 1));
      final marked = find.descendant(of: p(dayLabel(off)), matching: find.text(AppStrings.closedShort));
      await waitFor(marked);
      await shot('10i-calendar-day-closed');
      await openPreviewDay(off);
      await tap(p(AppStrings.more));
      await waitFor(p(AppStrings.unmarkClosedDate));
      await tap(p(AppStrings.unmarkClosedDate), after: const Duration(seconds: 1));
      await waitGone(find.textContaining(AppStrings.closedDayNote));
      await tap(p(AppStrings.back));
      await waitFor(find.byKey(ScreenKeys.home));
      await waitGone(marked);
      await shot('10j-calendar-day-unclosed');

      // 메뉴
      await goHome();
      await tap(p(AppStrings.settingsLabel));
      await tap(p(AppStrings.settingsMenus));
      await waitFor(find.byKey(ScreenKeys.settingsMenus));
      final stamp = DateTime.now().millisecondsSinceEpoch % 10000;
      final a = '통합A$stamp';
      final b = '통합B$stamp';
      for (final name in [a, b]) {
        await tap(btn(AppStrings.addMenu));
        await waitFor(find.text(AppStrings.menuNameHint));
        await t.enterText(find.byType(TextField).last, name);
        await pumpFor(const Duration(milliseconds: 300));
        await tap(btn(AppStrings.save).last);
        await waitFor(find.text(name));
      }
      await shot('10k-menus-added');
      await tap(p('${AppStrings.moveUp} $b'), after: const Duration(seconds: 1));
      await tap(p('${AppStrings.moveUp} $b'), after: const Duration(seconds: 1));
      await tap(p('${AppStrings.archiveMenu} $a'));
      await waitFor(find.text(AppStrings.archiveMenuConfirm));
      await tap(btn(AppStrings.archiveMenu));
      await waitGone(find.text(a));
      final order = find.byType(Text).evaluate().map((e) => (e.widget as Text).data ?? '').where((s) => ['목욕', '위생', '부분 미용', '전체 미용', '스포팅', '발톱', a, b].contains(s)).toList();
      note('메뉴 화면 순서 = $order');
      await shot('10l-menus-reordered-archived');
      await goHome();
      await tap(p(AppStrings.addReservation));
      await pickCustomer('8513', isKim);
      await reveal(p(b));
      final chipOrder = find.byType(Pressable).evaluate().map((e) => (e.widget as Pressable).semanticLabel ?? '').where((s) => ['목욕', '위생', '부분 미용', '전체 미용', '스포팅', '발톱', a, b].contains(s)).toList();
      note('② 메뉴 칩 순서 = $chipOrder');
      await shot('10m-form-menu-chips');
      soft(!chipOrder.contains(a), '보관한 메뉴 칩이 ②에 남았다');
      soft(chipOrder.contains(b) && chipOrder.indexOf(b) < chipOrder.indexOf('발톱'), '올린 메뉴가 ②에서 발톱보다 앞에 있지 않다');

    });

    // 10 이 어디서 멈춰도 일정은 원래대로 되돌린다.
    await step('10R', '일정 되돌리기', () async {
      if (origOpens == null) return;
      await openSchedule();
      await setTime(AppStrings.opensAtLabel, origOpens!);
      await setTime(AppStrings.closesAtLabel, origCloses!);
      for (final d in AppStrings.weekdaysShort) {
        final sel = t.widget<Pressable>(p(d).first).selected == true;
        if (sel != origClosedChips!.contains(d)) await tap(p(d));
      }
      await tap(btn(AppStrings.save));
      await waitFor(find.text(AppStrings.saved));
      note('되돌린 일정 = ${rowValue(AppStrings.opensAtLabel)}–${rowValue(AppStrings.closesAtLabel)}');
      await shot('10n-schedule-restored');
    });

    // ── 12 ──
    await step('12', '정리 안 된 예약', () async {
      final past = plusDays(-2);
      final h12 = 11 + run;
      await selectDate(past);
      await tap(p(AppStrings.addReservation));
      await pickCustomer('8513', isKim);
      await tap(p('두부'));
      await tap(p(hh(h12)));
      await waitEnabled(saveReservationBtn());
      await shot('12a-past-form');
      await tap(saveReservationBtn());
      await pumpFor(const Duration(seconds: 2));
      if (find.byKey(ScreenKeys.registerVisit).evaluate().isNotEmpty) {
        final texts = find.byType(Text).evaluate().map((e) => (e.widget as Text).data).whereType<String>().where((s) => s.contains('니다') || s.contains('요')).toList();
        note('지난 날짜 저장이 닫히지 않음 — 화면 문구 $texts');
        await shot('12b-past-rejected');
        throw TestFailure('지난 날짜 예약이 저장되지 않았다');
      }
      await goHome();
      final banner = pWhere((l) => l.startsWith('정리 안 된 예약'));
      await waitFor(banner);
      note('배너 = ${t.widget<Pressable>(banner.first).semanticLabel}');
      await shot('12c-unresolved-banner');
      await tap(banner);
      await waitFor(find.byKey(ScreenKeys.day));
      await waitFor(find.textContaining(AppStrings.markUnresolved));
      await pumpFor(const Duration(seconds: 1));
      await shot('12d-day-unresolved-mark');
    });

    // ── 추가 소견: 5묶음 이상인 날, 30분 블록 ──
    await step('X', '추가 — 5묶음 미리보기, 30분 블록', () async {
      final busy = plusDays(7 + run * 7); // 10/1 목
      for (final (i, h) in [10, 12, 14, 16, 18].indexed) {
        await reserve(
          date: busy,
          query: '8513',
          family: isKim,
          pets: ['콩이'],
          at: hh(h),
          duration: i == 0 ? 30 : null,
        );
      }
      await selectDate(busy);
      await pumpFor(const Duration(seconds: 1));
      await shot('X1-preview-five-groups');
      await openPreviewDay(busy);
      await tap(p(AppStrings.viewAsTimeline), after: const Duration(seconds: 1));
      await shot('X2-timeline-30min-block');
      await tap(p(AppStrings.viewAsList), after: const Duration(seconds: 1));
      await shot('X3-day-list-five');
    });

    // ── 추가 소견: 한 마리 완료·한 마리 미용 중(호스트에서 한 마리를 시작해 둔 뒤) ──
    await step('M', '추가 — 섞인 가족 카드', () async {
      await selectDate(today);
      await openPreviewDay(today);
      final card = cardAt(hh(h3), '콩이 · 두부');
      await waitFor(card);
      final chips = find.descendant(of: card, matching: find.byType(AppChip)).evaluate().map((e) => (e.widget as AppChip).label).toList();
      final buttons = find.descendant(of: card, matching: find.byType(AppButton)).evaluate().map((e) => (e.widget as AppButton).label).toList();
      note('섞인 가족 카드 ${hh(h3)} — 칩=$chips, 버튼=$buttons');
      await reveal(card);
      await shot('M1-mixed-inprogress-completed');
      await tap(p(AppStrings.viewAsTimeline), after: const Duration(seconds: 1));
      await shot('M2-mixed-timeline');
      await tap(p(AppStrings.viewAsList), after: const Duration(seconds: 1));
    });

    // ── 11 ──
    await step('11', '직원 — 일정·메뉴···· 없음, 예약·전이는 됨', () async {
      await logout();
      await login(staffName);
      await shot('11a-staff-home');
      await tap(p(AppStrings.settingsLabel));
      await waitFor(find.byKey(ScreenKeys.settings));
      await pumpFor(const Duration(seconds: 1));
      final hasSchedule = p(AppStrings.settingsSchedule).evaluate().isNotEmpty;
      final hasMenus = p(AppStrings.settingsMenus).evaluate().isNotEmpty;
      note('직원 설정 — 일정 행=$hasSchedule, 메뉴 행=$hasMenus');
      await shot('11b-staff-settings');
      expect(hasSchedule, isFalse);
      expect(hasMenus, isFalse);
      final h11 = 11 + run;
      await reserve(date: today, query: '8513', family: isKim, pets: ['콩이'], at: hh(h11));
      await openPreviewDay(today);
      final hasMore = p(AppStrings.more).evaluate().isNotEmpty;
      note('직원 하루 화면 ··· = $hasMore');
      final card = cardAt(hh(h11), '콩이');
      await waitFor(card);
      await shot('11c-staff-day');
      expect(hasMore, isFalse);
      await tap(find.descendant(of: card, matching: btn(AppStrings.actionStart)));
      await waitFor(find.descendant(of: card, matching: btn(AppStrings.actionCompleteShort)));
      await shot('11d-staff-started');
    });

    // 사장 계정으로 돌려 둔다.
    try {
      await goHome();
      await logout();
      await login(ownerName);
    } catch (e) {
      debugPrint('사장으로 돌리지 못함: $e');
    }

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint('RESULT $r');
    }
    // takeScreenshot 이 reportData['screenshots'] 에 모아 두므로 덮어쓰지 않는다.
    (binding.reportData ??= <String, dynamic>{})['results'] = results;
  });
}

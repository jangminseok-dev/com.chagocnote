// ③-A3 Task 9 Step 3 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해 카톡
// 붙여넣기 초안 흐름(확인 1~8)을 확인한다. ③-A2 의 visit_flow_test.dart 를
// 본떴다: 확인마다 스크린샷을 찍고, 단언이 실패해도 다음 확인으로 넘어가며,
// 마지막에 결과를 모아 찍는다. 클립보드는 앱 안에서 `Clipboard.setData`로 채운다.
//
// 준비: infra/ 에서 `bash ../backend/scripts/check_visit_flow.sh`가 만든 매장(김민지
// — 콩이·두부, 오늘 13:00 두 마리 완료, 어제 두부 노쇼, 월요일 휴무, 10–19시)을 쓴다.
// 확인 0 이 그 매장에 박서준(보리)과 확인 8 에 필요한 예약을 API 로 더하고, 확인 7 은
// 화면을 열기 바로 전에 다음 예약 시각에 콩이만 잡아 둔다.
//
// 실행(app/ 에서):
//   SHOTS_DIR=<스크린샷 폴더> flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/draft_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 \
//     --dart-define=SHOP_ID=<매장> --dart-define=OWNER=vflow-owner-<stamp>
// 선택: --dart-define=ONLY=1,2 (그 확인만 — 0 은 늘 돈다)

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/tokens/app_colors.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_chip.dart';
import 'package:chagocnote/design/widgets/pressable.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/screens/visit_labels.dart';
import 'package:chagocnote/features/visit/state/calendar_selection.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:chagocnote/main.dart' as app;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:integration_test/integration_test.dart';

const only = String.fromEnvironment('ONLY');
const shopId = int.fromEnvironment('SHOP_ID');
const ownerName = String.fromEnvironment('OWNER');

late IntegrationTestWidgetsFlutterBinding binding;
late WidgetTester t;
final results = <String>[];
String current = '-';

// 확인 0 이 채운다.
late int kimId;
late int kongId;
late int dubuId;
late int bathId;
late String nextDraftAt; // 확인 7 — 오늘 13:00 묶음의 다음 예약 시각
late String mixedAt; // 확인 8 — 섞인 가족 카드의 시각

DateTime get today {
  final n = DateTime.now();
  return DateTime(n.year, n.month, n.day);
}

DateTime plusDays(int days) =>
    DateTime(today.year, today.month, today.day + days);

/// 다음 주 월요일(월요일 시작 주).
DateTime get nextMonday => plusDays(8 - today.weekday);

/// 미리보기 "외 N건"·30분 블록·시간 칸 색을 볼 날 — 다음 주 토요일.
DateTime get busyDay => plusDays(13 - today.weekday);

String at(DateTime d, int hour) =>
    '${isoDay(d)}T${hour.toString().padLeft(2, '0')}:00:00+09:00';

ProviderContainer get container =>
    ProviderScope.containerOf(t.element(find.byType(App)));
GoRouter get router => container.read(routerProvider);
String get s => '/v1/shops/$shopId';

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
  if (id != '0' && only.isNotEmpty && !only.split(',').contains(id)) return;
  current = id;
  debugPrint('STEP $id 시작 — $title');
  try {
    softFails.clear();
    await body();
    if (softFails.isNotEmpty) {
      throw TestFailure('어긋남 ${softFails.length}건: ${softFails.join(' | ')}');
    }
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
  await waitFor(
    find.byKey(ScreenKeys.login),
    timeout: const Duration(seconds: 30),
  );
  await pumpFor(const Duration(milliseconds: 500));
}

Future<void> login(String name) async {
  await waitFor(
    find.byKey(ScreenKeys.login),
    timeout: const Duration(seconds: 30),
  );
  await t.enterText(find.byType(TextField).first, name);
  await pumpFor(const Duration(milliseconds: 300));
  await tap(btn(AppStrings.devSignIn));
  await waitFor(
    find.byKey(ScreenKeys.home),
    timeout: const Duration(seconds: 30),
  );
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

/// 캘린더 + → ①.
Future<void> openWho() async {
  await goCalendarTab();
  await tap(p(AppStrings.addReservation));
  await waitFor(find.text(AppStrings.reserveWhoTitle));
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

/// 클립보드에 [text]를 두고 ①의 [카톡 붙여넣기]로 초안 화면을 연다.
Future<void> pasteDraft(String text) async {
  await Clipboard.setData(ClipboardData(text: text));
  await openWho();
  await tap(btn(AppStrings.pasteFromKakao));
  await waitFor(find.byKey(ScreenKeys.visitDraft));
  await waitFor(
    btnWhere(
      (l) => l == AppStrings.draftContinue || l == AppStrings.draftFindCustomer,
    ),
  );
  await pumpFor(const Duration(milliseconds: 800));
}

/// 초안 화면의 날짜·시작·메뉴 한 줄 — 값과 "짐작" 칩.
({String value, bool guessed}) line(String label) {
  final row = find
      .ancestor(
        of: find.descendant(
          of: find.byKey(ScreenKeys.visitDraft),
          matching: find.text(label),
        ),
        matching: find.byType(Row),
      )
      .first;
  final texts = find
      .descendant(of: row, matching: find.byType(Text))
      .evaluate()
      .map((e) => (e.widget as Text).data)
      .whereType<String>()
      .toList();
  final guessed = find
      .descendant(of: row, matching: find.byType(AppChip))
      .evaluate()
      .isNotEmpty;
  return (value: texts.length > 1 ? texts[1] : '?', guessed: guessed);
}

/// 초안 화면의 보호자 후보 줄(Pressable 이름표).
List<String> candidates() => find
    .descendant(
      of: find.byKey(ScreenKeys.visitDraft),
      matching: find.byType(Pressable),
    )
    .evaluate()
    .map((e) => e.widget as Pressable)
    .where(
      (w) =>
          w.semanticLabel != null &&
          w.semanticLabel != AppStrings.draftReceivedText &&
          w.semanticLabel != AppStrings.draftContinue &&
          w.semanticLabel != AppStrings.draftFindCustomer &&
          w.semanticLabel != AppStrings.back,
    )
    .map((w) => '${w.semanticLabel}${w.selected == true ? ' [고름]' : ''}')
    .toList();

/// 후보 줄에 보이는 "이름 · 뒷자리" 글자.
List<String> candidateTexts() => find
    .descendant(
      of: find.byKey(ScreenKeys.visitDraft),
      matching: find.byType(Text),
    )
    .evaluate()
    .map((e) => (e.widget as Text).data ?? '')
    .where((d) => d.contains(' · ··'))
    .toList();

bool ownerGuessedChip() {
  final row = find
      .ancestor(
        of: find.descendant(
          of: find.byKey(ScreenKeys.visitDraft),
          matching: find.text(AppStrings.draftOwnerSection),
        ),
        matching: find.byType(Row),
      )
      .first;
  return find
      .descendant(of: row, matching: find.byType(AppChip))
      .evaluate()
      .isNotEmpty;
}

void noteDraft() {
  final d = line(AppStrings.visitDateLabel);
  final tm = line(AppStrings.visitTimeLabel);
  final m = line(AppStrings.menuLabel);
  note(
    '초안 — 후보=${candidates()} ${candidateTexts()}(보호자 짐작 칩=${ownerGuessedChip()}), '
    '날짜=${d.value}${d.guessed ? '(짐작)' : ''}, 시작=${tm.value}${tm.guessed ? '(짐작)' : ''}, '
    '메뉴=${m.value}${m.guessed ? '(짐작)' : ''}',
  );
}

/// 예약을 저장하면 보낼 것 시트(⑪-B)가 뜰 수 있다 — 떠 있으면 [나중에]로 닫는다.
Future<void> closeBundle() async {
  final end = DateTime.now().add(const Duration(seconds: 8));
  while (DateTime.now().isBefore(end)) {
    await pumpFor(const Duration(milliseconds: 200));
    if (find.text(AppStrings.bundleLater).evaluate().isNotEmpty) {
      await tap(find.text(AppStrings.bundleLater));
      return;
    }
    if (find.byKey(ScreenKeys.registerVisit).evaluate().isEmpty) return;
  }
}

Finder saveReservationBtn() => btnWhere(
  (l) =>
      l.startsWith('예약 저장') ||
      l == AppStrings.pickTimeFirst ||
      l.endsWith('골라 주세요'),
);

String saveLabel() => t.widget<AppButton>(saveReservationBtn().first).label;

bool selected(String label) =>
    p(label).evaluate().isNotEmpty &&
    t.widget<Pressable>(p(label).first).selected == true;

int? parseDuration(String s) {
  final m = RegExp(r'^(?:(\d+)시간)?\s*(?:(\d+)분)?$').firstMatch(s.trim());
  if (m == null || (m.group(1) == null && m.group(2) == null)) return null;
  return int.parse(m.group(1) ?? '0') * 60 + int.parse(m.group(2) ?? '0');
}

/// 예약 폼의 소요 값.
int durationNow() {
  final row = find
      .ancestor(of: p(AppStrings.longer), matching: find.byType(Row))
      .first;
  for (final e
      in find.descendant(of: row, matching: find.byType(Text)).evaluate()) {
    final d = (e.widget as Text).data;
    if (d != null) {
      final v = parseDuration(d);
      if (v != null) return v;
    }
  }
  throw TestFailure('소요 값을 못 읽었다');
}

/// 하루 화면의 [at] 시 묶음 카드.
Finder cardAt(String at, String title) =>
    find.ancestor(of: find.text(at), matching: p(title));

// ── 준비(API) ────────────────────────────────────────────────────

dynamic get api => container.read(apiClientProvider);

Future<List<Map<String, dynamic>>> dayItems(DateTime d) async {
  final data = await api.get('$s/visits', queryParameters: {'date': isoDay(d)});
  return [
    for (final i in (data['items'] as List))
      (i as Map<String, dynamic>)['visit'] as Map<String, dynamic>,
  ];
}

Future<List<int>> book(List<int> pets, String startsAt, {int? duration}) async {
  try {
    final saved = await api.post(
      '$s/visits',
      data: {
        'customer_id': kimId,
        'pet_ids': pets,
        'starts_at': startsAt,
        'menu_ids': [bathId],
        'duration_minutes': ?duration,
      },
    );
    return [for (final v in saved['visits'] as List) v['visit_id'] as int];
  } catch (e) {
    note('예약 $startsAt $pets 는 이미 있다(앞선 실행) — $e'.split('\n').first);
    return const [];
  }
}

Future<void> transition(List<int> ids, String action) => api.post(
  '$s/visits/transitions',
  data: {'visit_ids': ids, 'action': action},
);

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('③-A3 카톡 초안 흐름 확인 8개', timeout: const Timeout(Duration(minutes: 30)), (
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

    // ── 0 준비 ──
    await step('0', '준비 — 박서준(보리), 확인 7·8 의 예약', () async {
      final kim = await api.get('$s/customers', queryParameters: {'q': '김민지'});
      final family = (kim['items'] as List).first as Map<String, dynamic>;
      kimId = family['customer_id'] as int;
      final pets = {
        for (final pet in family['pets'] as List) pet['name']: pet['pet_id'],
      };
      kongId = pets['콩이'] as int;
      dubuId = pets['두부'] as int;
      final menus = await api.get('$s/menus');
      bathId = [
        for (final m in menus['items'] as List)
          if (m['name'] == '목욕') m['menu_id'] as int,
      ].first;
      note('김민지=$kimId 콩이=$kongId 두부=$dubuId 목욕=$bathId');

      final park = await api.get('$s/customers', queryParameters: {'q': '박서준'});
      if ((park['items'] as List).isEmpty) {
        final digits = (DateTime.now().millisecondsSinceEpoch % 100000000)
            .toString()
            .padLeft(8, '0');
        await api.post(
          '$s/customers',
          data: {
            'customer': {
              'name': '박서준',
              'phone': '010$digits',
              'marketing_consent': false,
            },
            'pet': {
              'name': '보리',
              'species': 'dog',
              'breed': '푸들',
              'sex': 'male',
              'neutered': true,
              'birth_year': 2022,
              'weight_kg': 4.1,
              'no_known_conditions': true,
            },
          },
        );
        note('박서준(보리) 등록');
      }

      // 다시 돌릴 때 — 확인 1 이 내일 잡은 예약을 비운다.
      for (final v in await dayItems(plusDays(1))) {
        if (v['status'] == VisitStatus.reserved &&
            v['customer']['customer_id'] == kimId) {
          await api.post(
            '$s/visits/transitions',
            data: {
              'visit_ids': [v['visit_id']],
              'action': 'cancel',
              'cancel_reason': 'shop_reason',
            },
          );
          note('앞선 실행의 내일 예약 ${v['visit_id']} 취소');
        }
      }

      // 확인 8 — 오늘 비어 있는 시각에 두 마리 → 둘 다 시작 → 콩이만 완료.
      final taken = {
        for (final v in await dayItems(today))
          (v['starts_at'] as String).substring(11, 16),
      };
      final hour = [
        17,
        16,
        15,
        14,
        12,
        11,
      ].firstWhere((h) => !taken.contains('$h:00'));
      mixedAt = '$hour:00';
      final ids = await book([kongId, dubuId], at(today, hour));
      await transition(ids, 'start');
      final kong = (await dayItems(today)).firstWhere(
        (v) => ids.contains(v['visit_id']) && v['pet']?['pet_id'] == kongId,
      );
      await transition([kong['visit_id'] as int], 'complete');
      note('오늘 $mixedAt 콩이·두부 — 콩이 완료, 두부 미용 중으로 만듦');

      // 확인 8 — 바쁜 날(다음 주 토요일)에 다섯 묶음, 10:00 은 30분.
      await book([kongId], at(busyDay, 10), duration: 30);
      for (final h in [12, 14, 16, 18]) {
        await book([kongId], at(busyDay, h));
      }
      note('바쁜 날 ${isoDay(busyDay)} 에 콩이 10(30분)·12·14·16·18시');
    });

    // ── 1 ──
    await step('1', '붙여넣기 → 초안 → ② → 저장 → 초안·① 닫히고 내일', () async {
      final tomorrow = plusDays(1);
      await pasteDraft('안녕하세요 내일 오후 2시에 콩이 목욕 부탁드려요');
      final shown = find
          .descendant(
            of: find.byKey(ScreenKeys.visitDraft),
            matching: find.text('안녕하세요 내일 오후 2시에 콩이 목욕 부탁드려요'),
          )
          .evaluate()
          .isNotEmpty;
      noteDraft();
      await shot('01a-draft');
      soft(shown, '받은 글이 보이지 않는다');
      soft(candidates().length == 1, '후보가 하나가 아니다');
      soft(
        candidates().isNotEmpty &&
            candidates().first.startsWith('김민지 콩이 · 두부') &&
            candidates().first.endsWith('[고름]'),
        '후보 김민지(콩이 · 두부)가 고른 상태가 아니다',
      );
      final d = line(AppStrings.visitDateLabel);
      final tm = line(AppStrings.visitTimeLabel);
      final m = line(AppStrings.menuLabel);
      soft(d.value == dayLabel(tomorrow) && !d.guessed, '날짜가 내일(확정)이 아니다');
      soft(tm.value == '14:00' && !tm.guessed, '시작이 14:00(짐작 없음)이 아니다');
      soft(m.value == '목욕', '메뉴가 목욕이 아니다');
      await tap(btn(AppStrings.draftContinue));
      await waitFor(find.text(AppStrings.reserveWhenTitle));
      await waitEnabled(saveReservationBtn());
      await pumpFor(const Duration(milliseconds: 800));
      final label = saveLabel();
      note(
        '② — 저장 버튼="$label", 콩이=${selected('콩이')}, 두부=${selected('두부')}, '
        '목욕=${selected('목욕')}, 14:00=${selected('14:00')}, 소요=${durationNow()}분',
      );
      await shot('01b-form');
      soft(
        label == AppStrings.saveReservation('${dayLabel(tomorrow)} 14:00'),
        '② 저장 버튼이 내일 14:00 이 아니다',
      );
      soft(selected('콩이') && !selected('두부'), '②에 콩이만 골라져 있지 않다');
      soft(selected('목욕'), '②에 목욕이 골라져 있지 않다');
      soft(durationNow() == 60, '② 소요가 60분이 아니다');
      await tap(saveReservationBtn());
      await closeBundle();
      await waitGone(find.byKey(ScreenKeys.registerVisit));
      await waitGone(find.byKey(ScreenKeys.visitDraft));
      await pumpFor(const Duration(seconds: 1));
      final sel = container.read(selectedDateProvider);
      note('저장 뒤 — 초안·① 닫힘, 홈이 고른 날 = $sel');
      await shot('01c-home-tomorrow');
      soft(sel == tomorrow, '홈이 내일을 고르지 않았다');
      final saved = (await dayItems(tomorrow)).where(
        (v) =>
            v['status'] == VisitStatus.reserved &&
            (v['starts_at'] as String).substring(11, 16) == '14:00',
      );
      note('서버의 내일 14:00 예약 = ${saved.map((v) => v['pet']?['name']).toList()}');
      soft(saved.length == 1, '서버에 내일 14:00 예약이 하나가 아니다');
    });

    // ── 2 ──
    await step('2', '"내일 2시 콩이" → 시작 14:00 짐작 → ②에서 바꿀 수 있다', () async {
      await pasteDraft('내일 2시 콩이');
      noteDraft();
      await shot('02a-draft-guessed-time');
      final tm = line(AppStrings.visitTimeLabel);
      soft(tm.value == '14:00' && tm.guessed, '시작이 14:00(짐작)이 아니다');
      await tap(btn(AppStrings.draftContinue));
      await waitFor(find.text(AppStrings.reserveWhenTitle));
      await waitEnabled(saveReservationBtn());
      final before = saveLabel();
      await tap(p('15:00'), after: const Duration(seconds: 1));
      await waitEnabled(saveReservationBtn());
      final after = saveLabel();
      note('② 저장 버튼 "$before" → 15:00 을 누른 뒤 "$after"');
      await shot('02b-form-time-changed');
      soft(before.endsWith('14:00'), '②가 14:00 으로 열리지 않았다');
      soft(after.endsWith('15:00'), '②에서 시각을 바꾸지 못했다');
    });

    // ── 3 ──
    await step('3', '카톡 머리말 → 다음 주 월요일(짐작)·15:00(짐작)·김민지', () async {
      await pasteDraft('[김민지] [오후 2:31] 콩이 다음 주 월요일 3시 될까요');
      noteDraft();
      await shot('03a-draft-kakao-header');
      final d = line(AppStrings.visitDateLabel);
      final tm = line(AppStrings.visitTimeLabel);
      soft(
        d.value == dayLabel(nextMonday) && d.guessed,
        '날짜가 다음 주 월요일(짐작)이 아니다',
      );
      soft(tm.value == '15:00' && tm.guessed, '시작이 15:00(짐작)이 아니다');
      soft(candidates().any((c) => c.startsWith('김민지 ')), '후보에 김민지가 없다');
    });

    // ── 4 ──
    await step('4', '"보리 모레 부분미용" → 박서준(보리), 부분 미용(짐작)', () async {
      await pasteDraft('보리 모레 부분미용');
      noteDraft();
      await shot('04a-draft-park');
      final d = line(AppStrings.visitDateLabel);
      final m = line(AppStrings.menuLabel);
      soft(
        candidates().length == 1 && candidates().first.startsWith('박서준 보리'),
        '후보가 박서준(보리) 하나가 아니다',
      );
      soft(d.value == dayLabel(plusDays(2)), '날짜가 모레가 아니다');
      soft(m.value == '부분 미용' && m.guessed, '메뉴가 부분 미용(짐작)이 아니다');
    });

    // ── 5 ──
    await step('5', '"콩" → 후보 없음 → [고객 찾기] → ① → ②(오늘, 빈 시각)', () async {
      await pasteDraft('콩');
      noteDraft();
      final none = find
          .text(AppStrings.draftNoCandidates)
          .evaluate()
          .isNotEmpty;
      await shot('05a-draft-no-candidates');
      soft(none, '"찾은 보호자가 없어요"가 없다');
      await tap(btn(AppStrings.draftFindCustomer));
      await pickCustomer('김민지', isKim);
      await pumpFor(const Duration(seconds: 1));
      final label = saveLabel();
      final anySlot = find
          .byType(Pressable)
          .evaluate()
          .map((e) => e.widget as Pressable)
          .where(
            (w) =>
                w.selected == true &&
                RegExp(r'^\d\d:\d\d$').hasMatch(w.semanticLabel ?? ''),
          )
          .map((w) => w.semanticLabel)
          .toList();
      note(
        '② — 저장 버튼="$label", 오늘 칸 고름=${selected(dayLabel(today))}, 고른 시간 칸=$anySlot',
      );
      await shot('05b-form-today-no-time');
      soft(!label.startsWith('예약 저장'), '시각이 비어 있지 않다');
      soft(selected(dayLabel(today)), '날짜가 오늘이 아니다');
      soft(anySlot.isEmpty, '골라진 시간 칸이 있다');
    });

    // ── 6 ──
    await step('6', '클립보드가 비었을 때 → "복사한 글이 없어요"', () async {
      await Clipboard.setData(const ClipboardData(text: ''));
      await openWho();
      await tap(
        btn(AppStrings.pasteFromKakao),
        after: const Duration(seconds: 1),
      );
      final shown = find.text(AppStrings.clipboardEmpty).evaluate().isNotEmpty;
      final opened = find.byKey(ScreenKeys.visitDraft).evaluate().isNotEmpty;
      note('문구 보임=$shown, 초안 화면 열림=$opened');
      await shot('06a-clipboard-empty');
      soft(shown, '"복사한 글이 없어요"가 없다');
      soft(!opened, '빈 클립보드로 초안 화면이 열렸다');
    });

    // ── 7 ──
    await step('7', '다음 예약 ②에서 한 아이가 이미 예약됨 → 스낵바 뒤 닫힘', () async {
      router.push('/visits/day/${isoDay(today)}');
      await waitFor(find.byKey(ScreenKeys.day));
      // 오늘 13:00 완료 묶음의 다음 예약 시각에 콩이만 먼저 잡아 둔다. 다음 예약
      // 시각은 방문 이력에 따라 바뀌므로 화면을 열기 바로 전에 묻는다.
      final done = (await dayItems(today)).firstWhere(
        (v) =>
            (v['starts_at'] as String).substring(11, 16) == '13:00' &&
            v['status'] == VisitStatus.completed,
      );
      final draft = await api.get('$s/visits/${done['visit_id']}/next-draft');
      nextDraftAt = draft['starts_at'] as String;
      final day = DateTime.parse(nextDraftAt.substring(0, 10));
      for (final v in await dayItems(day)) {
        if (v['starts_at'] == nextDraftAt &&
            v['status'] == VisitStatus.reserved) {
          await api.post(
            '$s/visits/transitions',
            data: {
              'visit_ids': [v['visit_id']],
              'action': 'cancel',
              'cancel_reason': 'shop_reason',
            },
          );
          note(
            '앞선 실행의 $nextDraftAt 예약 ${v['visit_id']}(${v['pet']?['name']}) 취소',
          );
        }
      }
      await book([kongId], nextDraftAt);
      note('다음 예약 시각 $nextDraftAt 에 콩이만 예약');
      await tap(cardAt('13:00', '콩이 · 두부'));
      await waitFor(find.byKey(ScreenKeys.visitDetail));
      await tap(p(AppStrings.more));
      await tap(p(AppStrings.actionNextReservation));
      await waitFor(find.text(AppStrings.reserveWhenTitle));
      await waitEnabled(saveReservationBtn());
      final label = saveLabel();
      note(
        '다음 예약 ② 저장 버튼="$label", 콩이=${selected('콩이')}, 두부=${selected('두부')}',
      );
      await shot('07a-next-form');
      await tap(saveReservationBtn(), after: const Duration(milliseconds: 100));
      await waitFor(find.text(AppStrings.duplicateVisitNotice));
      await shot('07b-snackbar');
      await waitGone(find.byKey(ScreenKeys.registerVisit));
      final onDetail = find.byKey(ScreenKeys.visitDetail).evaluate().isNotEmpty;
      final stillSnack = find
          .text(AppStrings.duplicateVisitNotice)
          .evaluate()
          .isNotEmpty;
      note('닫힌 뒤 — 방문 상세 위=$onDetail, 스낵바 남음=$stillSnack');
      await shot('07c-after-close');
      final target = DateTime.parse(nextDraftAt.substring(0, 10));
      final there = (await dayItems(target))
          .where(
            (v) =>
                v['starts_at'] == nextDraftAt &&
                v['status'] != VisitStatus.canceled,
          )
          .map((v) => v['pet']?['name'])
          .toList();
      note('서버의 $nextDraftAt 예약 = $there (두부 몫은 저장되지 않아야 한다)');
      soft(there.length == 1 && there.first == '콩이', '다음 예약 시각에 콩이만 있지 않다');
    });

    // ── 8 ──
    await step('8', 'A2 잔여 — 섞인 카드, 외 N건, 시간 칸 색, 30분 블록, 노쇼 횟수', () async {
      // 섞인 가족 카드
      router.push('/visits/day/${isoDay(today)}');
      await waitFor(find.byKey(ScreenKeys.day));
      final card = cardAt(mixedAt, '콩이 · 두부');
      await reveal(card);
      final texts = find
          .descendant(of: card, matching: find.byType(Text))
          .evaluate()
          .map((e) => (e.widget as Text).data)
          .whereType<String>()
          .toList();
      final buttons = find
          .descendant(of: card, matching: find.byType(AppButton))
          .evaluate()
          .map((e) => (e.widget as AppButton).label)
          .toList();
      note('섞인 카드 $mixedAt — 글=$texts, 버튼=$buttons');
      await shot('08a-mixed-card');
      soft(texts.contains('콩이 완료 · 두부 미용 중'), '카드에 "콩이 완료 · 두부 미용 중"이 없다');
      soft(buttons.contains(AppStrings.actionCompleteShort), '카드에 [완료하기]가 없다');
      await tap(
        find.descendant(
          of: card,
          matching: btn(AppStrings.actionCompleteShort),
        ),
      );
      // ④-2: 완료는 기록 화면(완료 모드)을 거친다 — 기록 없이 완료하고 다음 예약 시트는 닫는다.
      await waitFor(find.byKey(ScreenKeys.visitRecord));
      await shot('08b-complete-record');
      await tap(btn(AppStrings.completeWithoutRecord));
      await waitFor(find.text(AppStrings.completeTitle));
      await tap(btn(AppStrings.close));
      await waitGone(find.text(AppStrings.completeTitle));
      await pumpFor(const Duration(seconds: 1));
      final after = (await dayItems(today))
          .where((v) => (v['starts_at'] as String).substring(11, 16) == mixedAt)
          .map((v) => '${v['pet']?['name']} ${v['status']}')
          .toList();
      note('완료하기 뒤 $mixedAt = $after');
      await shot('08c-mixed-completed');
      soft(
        after.length == 2 &&
            after.every((s) => s.endsWith(VisitStatus.completed.code)),
        '$mixedAt 두 마리가 모두 완료가 아니다',
      );

      // 미리보기 "외 N건"
      await goHome();
      await selectDate(busyDay);
      await pumpFor(const Duration(seconds: 1));
      final more = find
          .textContaining(RegExp(r'^외 \d+건$'))
          .evaluate()
          .map((e) => (e.widget as Text).data)
          .toList();
      note('${dayLabel(busyDay)} 미리보기 초과 표시 = $more');
      await shot('08d-preview-more');
      soft(more.contains(AppStrings.moreGroups(1)), '미리보기에 "외 1건"이 없다');

      // 30분 블록 "이름 · 메뉴"
      await openPreviewDay(busyDay);
      await tap(
        p(AppStrings.viewAsTimeline),
        after: const Duration(seconds: 1),
      );
      final rich = find.byWidgetPredicate(
        (w) => w is RichText && w.text.toPlainText() == '콩이 · 목욕',
      );
      final hasBlock = rich.evaluate().isNotEmpty;
      note('시간표 30분 블록 "콩이 · 목욕" 보임=$hasBlock');
      await shot('08e-timeline-30min');
      soft(hasBlock, '30분 블록에 "콩이 · 목욕"이 없다');
      await tap(p(AppStrings.viewAsList), after: const Duration(seconds: 1));

      // 예약 ② 시간 칸 — 겹침(줄긋기·흰 바탕)과 휴무(옅은 바탕)
      await goHome();
      await selectDate(busyDay);
      await tap(p(AppStrings.addReservation));
      await pickCustomer('김민지', isKim);
      await waitFor(p('12:00'));
      await pumpFor(const Duration(seconds: 1));
      Text slotText(String label) => t.widget<Text>(
        find.descendant(of: p(label).first, matching: find.byType(Text)).first,
      );
      Color? slotBg(String label) {
        final c = t.widget<Container>(
          find
              .descendant(of: p(label).first, matching: find.byType(Container))
              .first,
        );
        return (c.decoration as BoxDecoration?)?.color;
      }

      final o = slotText('12:00');
      final oBg = slotBg('12:00');
      final plain = slotText('11:00');
      note(
        '겹침 칸 12:00 — 줄=${o.style?.decoration}, 글자=${o.style?.color}, 바탕=$oBg; '
        '보통 칸 11:00 — 글자=${plain.style?.color}, 바탕=${slotBg('11:00')}',
      );
      await shot('08f-slots-overlap');
      soft(o.style?.decoration == TextDecoration.lineThrough, '겹침 칸에 줄이 없다');
      soft(oBg == AppColors.white, '겹침 칸 바탕이 흰색이 아니다');
      // 경고 줄은 시각을 고른 뒤에 보인다 — 11:00 을 고르고 휴무일로 옮긴다.
      await tap(p('11:00'));
      await tap(p(dayLabel(nextMonday)), after: const Duration(seconds: 1));
      await waitFor(find.text('· ${AppStrings.warningClosedDay}'));
      final f = slotText('15:00');
      final fBg = slotBg('15:00');
      note(
        '휴무일(${dayLabel(nextMonday)}) 칸 15:00 — 줄=${f.style?.decoration}, 글자=${f.style?.color}, 바탕=$fBg',
      );
      await shot('08g-slots-closed-day');
      soft(fBg == AppColors.backgroundTop, '휴무일 칸 바탕이 옅지 않다');
      soft(f.style?.color == AppColors.secondary, '휴무일 칸 글자가 옅지 않다');
      soft(f.style?.decoration != TextDecoration.lineThrough, '휴무일 칸에 줄이 있다');

      // 보호자 탭 "노쇼 횟수 / N회"
      await goHome();
      final detail = await api.get('$s/customers/$kimId');
      final count = detail['no_show_count'] as int;
      router.push('/pets/$kongId');
      await waitFor(find.byKey(ScreenKeys.petDetail));
      await tap(p(AppStrings.petTabOwner), after: const Duration(seconds: 1));
      await reveal(find.text(AppStrings.noShowCountLabel));
      final value = find
          .text(AppStrings.timesCount(count))
          .evaluate()
          .isNotEmpty;
      final old = find
          .text(AppStrings.noShowCount(count))
          .evaluate()
          .isNotEmpty;
      note(
        '보호자 탭 — "노쇼 횟수" 라벨, 값 "${AppStrings.timesCount(count)}" 보임=$value, 옛 값 "${AppStrings.noShowCount(count)}" 보임=$old',
      );
      await shot('08h-owner-tab-noshow');
      soft(value, '보호자 탭에 "${AppStrings.timesCount(count)}"가 없다');
      soft(!old, '보호자 탭에 옛 "노쇼 N회"가 남았다');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint('RESULT $r');
    }
    // takeScreenshot 이 reportData['screenshots'] 에 모아 두므로 덮어쓰지 않는다.
    (binding.reportData ??= <String, dynamic>{})['results'] = results;
  });
}

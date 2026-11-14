// ⑨-1b 완료 기준 — 실제 백엔드(와 임베딩 프로세스)에 붙은 앱을 시뮬레이터에서 조작해, 기록 피드의 돋보기로 검색 화면을
// 열고, 적어 둔 말로 찾아 방문 상세로 가고, 말을 바꿔도 찾아지고, 보호자 메모에서 [보호자] 탭으로 가고, 반려동물 상세의
// [기록] 탭에서 그 아이로 좁혀 찾는지 확인한다. 도구는 `flow_kit.dart`.
//
// 준비(infra/ 에서): bash ../app/tool/prepare_search_flow.sh → 마지막 줄의 --dart-define 들(실행마다 새로).
//   에뮬레이터는 `adb reverse tcp:8080 tcp:8080`.
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/search_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>
//
// 검색어와 걸린 문장은 준비 스크립트가 넣은 지어낸 글이다 — 단계 이름과 실패 문구에는 적지 않는다.

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/design/widgets/app_segment.dart';
import 'package:chagocnote/features/customer/screens/pet_detail_screen.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const petId = int.fromEnvironment('PET');
const otherPetId = int.fromEnvironment('PET2');
const visitId = int.fromEnvironment('VISIT');
const ownerName = String.fromEnvironment('OWNER');

final screen = find.byKey(ScreenKeys.search);
Finder row(int index) => find.byKey(ValueKey('search-item-$index'));
Finder inRow(Finder r, String text) => find.descendant(of: r, matching: find.text(text));

/// 그 제목과 종류 줄을 가진 결과 줄.
Finder rowOf(String title, String meta) => find.byElementPredicate((element) {
  final key = element.widget.key;
  if (key is! ValueKey<String> || !key.value.startsWith('search-item-')) return false;
  var hasTitle = false;
  var hasMeta = false;
  void visit(Element child) {
    final widget = child.widget;
    if (widget is Text) {
      if (widget.data == title) hasTitle = true;
      if (widget.data == meta) hasMeta = true;
    }
    child.visitChildren(visit);
  }

  element.visitChildren(visit);
  return hasTitle && hasMeta;
});

/// 입력 칸에 글을 넣는다. 화면을 연 뒤 처음은 키보드 입력으로(`enter`), 같은 칸에 다시 넣을 때는 칸의 컨트롤러로 넣는다 —
/// 기기에서는 포커스를 내린 칸에 `enterText`를 다시 하면 글이 들어가지 않는다. 어느 쪽이든 화면의 같은 듣는 쪽이 받는다.
Future<void> type(String text, {bool first = false}) async {
  if (first) {
    await enter('search-field', text);
  } else {
    _field().controller!.text = text;
  }
  await pumpFor(const Duration(milliseconds: 900));
}

/// 검색어를 적고 결과가 그려질 때까지 기다린다(0.5초 쉰 뒤 묻는다).
Future<void> ask(String text, {bool first = false}) async {
  await type(text, first: first);
  await waitFor(row(0));
}

Future<void> backToSearch() async {
  router.pop();
  await waitFor(screen);
  await pumpFor(const Duration(milliseconds: 400));
}

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('⑨-1b 완료 기준', timeout: const Timeout(Duration(minutes: 10)), (tester) async {
    t = tester;
    await initializeGlass();
    await t.pumpWidget(buildRoot());
    final end = DateTime.now().add(const Duration(seconds: 40));
    while (DateTime.now().isBefore(end)) {
      await t.pump(const Duration(milliseconds: 100));
      drain();
      if (find.byKey(ScreenKeys.login).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.home).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.shopSelect).evaluate().isNotEmpty) {
        break;
      }
    }
    if (find.byKey(ScreenKeys.login).evaluate().isEmpty) await logout();
    await login(ownerName);

    await step('S1', '기록 피드 머리의 돋보기 → 기록 찾기 화면(처음에는 안내와 예시)', () async {
      router.go('/home');
      await waitFor(find.byKey(ScreenKeys.home));
      await tap(find.bySemanticsLabel(AppStrings.viewAsFeed));
      await waitFor(find.bySemanticsLabel(AppStrings.searchOpen));
      await shot('S1-feed');
      await tap(find.bySemanticsLabel(AppStrings.searchOpen));
      await waitFor(screen);
      soft(find.text(AppStrings.searchIntro).evaluate().isNotEmpty, '처음 안내가 없다');
      soft(find.text(AppStrings.searchExampleA).evaluate().isNotEmpty, '예시가 없다');
      await shot('S1-search');
    });

    await step('S2', '적어 둔 말로 찾는다 — 맨 위 줄에 아이 이름, 케어 노트와 방문 날', () async {
      await ask('귀 청소할 때', first: true);
      soft(inRow(row(0), '콩이').evaluate().isNotEmpty, '맨 위 줄이 그 아이가 아니다');
      soft(
        find.descendant(of: row(0), matching: find.textContaining('${AppStrings.searchKindCareNote} · ')).evaluate().isNotEmpty,
        '맨 위 줄이 날짜가 붙은 케어 노트가 아니다',
      );
      soft(find.text(AppStrings.searchNearest).evaluate().isNotEmpty, '"가까운 기록부터" 줄이 없다');
      soft(find.textContaining('AI').evaluate().isEmpty, '화면에 AI 라는 말이 있다');
      await shot('S2-results');
    });

    await step('S3', '방문 줄 → 방문 상세 → 돌아오면 검색어와 결과가 그대로', () async {
      await tap(row(0));
      await waitFor(find.byKey(ScreenKeys.visitDetail));
      soft(router.state.uri.path == '/visits/$visitId', '다른 방문으로 갔다');
      await shot('S3-visit');
      await backToSearch();
      soft(fieldTextOf() == '귀 청소할 때', '검색어가 남아 있지 않다');
      soft(inRow(row(0), '콩이').evaluate().isNotEmpty, '결과가 남아 있지 않다');
    });

    await step('S4', '말을 바꿔 찾는다(글자가 겹치지 않는다) — 그 아이의 특이사항 줄', () async {
      await ask('드라이어 바람에 겁먹는 강아지');
      final memo = rowOf('콩이', AppStrings.searchKindPetMemo);
      await waitFor(memo);
      await shot('S4-meaning');
      await tap(memo);
      await waitFor(find.byKey(ScreenKeys.petDetail));
      soft(router.state.uri.path == '/pets/$petId', '다른 아이로 갔다');
      await backToSearch();
    });

    await step('S5', '보호자 메모 줄(사진 없이 보호자 이름) → 반려동물 상세의 [보호자] 탭', () async {
      await ask('전화를 달라고');
      final memo = rowOf('김검색', AppStrings.searchKindCustomerMemo);
      await waitFor(memo);
      await shot('S5-owner-memo');
      await tap(memo);
      await waitFor(find.byKey(ScreenKeys.petDetail));
      await pumpFor(const Duration(seconds: 1));
      soft(
        t.widget<AppSegment>(find.byType(AppSegment)).currentIndex == PetDetailScreen.ownerTab,
        '[보호자] 탭이 아니다',
      );
      await shot('S5-owner-tab');
      await backToSearch();
    });

    await step('S6', '반려동물 상세 [기록] 탭 → 그 아이로 좁힌 검색(다른 아이의 글이 없다)', () async {
      router.go('/home');
      await pumpFor(const Duration(milliseconds: 300));
      router.push('/pets/$otherPetId');
      await waitFor(find.byKey(ScreenKeys.petDetail));
      await tap(find.text(AppStrings.petTabRecords));
      await tap(find.text(AppStrings.petRecordsSearch));
      await waitFor(screen);
      soft(find.text(AppStrings.searchInPet('두부')).evaluate().isNotEmpty, '좁힌 아이의 이름 줄이 없다');
      await ask('드라이기 소리', first: true);
      soft(find.text('콩이').evaluate().isEmpty, '다른 아이의 글이 보인다');
      soft(inRow(row(0), '두부').evaluate().isNotEmpty || inRow(row(0), '김검색').evaluate().isNotEmpty, '그 아이나 보호자의 줄이 아니다');
      await shot('S6-narrowed');
    });

    await step('S7', '검색어를 지우면 처음 화면으로 돌아간다', () async {
      await type('');
      await waitFor(find.text(AppStrings.searchIntro));
      soft(row(0).evaluate().isEmpty, '결과가 남아 있다');
      await shot('S7-cleared');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}

/// 입력 칸의 글 — 키가 감싼 위젯에 있어 그 안의 TextField 를 찾는다.
String fieldTextOf() => _field().controller!.text;

TextField _field() => t.widget<TextField>(
  find.descendant(of: find.byKey(const ValueKey('search-field')), matching: find.byType(TextField)),
);

import 'package:chagocnote/design/widgets/app_back_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

/// go_router를 최소 구성으로 띄운다 — `/home`, `/base`(눌러서 쌓는 시작점) 두
/// 경로만 있으면 판별에 충분하다.
GoRouter _router({required String initialLocation}) => GoRouter(
      initialLocation: initialLocation,
      routes: [
        GoRoute(path: '/home', builder: (context, state) => const _Screen('home')),
        GoRoute(path: '/base', builder: (context, state) => const _Screen('base')),
        GoRoute(
          path: '/detail',
          builder: (context, state) => const _Screen('detail'),
        ),
      ],
    );

class _Screen extends StatelessWidget {
  const _Screen(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(children: [Text(label), const AppBackButton()]),
    );
  }
}

Widget _appWith(GoRouter router) => MaterialApp.router(routerConfig: router);

void main() {
  testWidgets('쌓인 경로에서 누르면 이전 화면으로 돌아간다', (tester) async {
    final router = _router(initialLocation: '/base');
    await tester.pumpWidget(_appWith(router));
    await tester.pumpAndSettle();

    router.push('/detail');
    await tester.pumpAndSettle();
    expect(find.text('detail'), findsOneWidget);

    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await tester.pumpAndSettle();

    expect(find.text('base'), findsOneWidget);
  });

  testWidgets('돌아갈 곳이 없으면 /home 으로 간다', (tester) async {
    final router = _router(initialLocation: '/base');
    await tester.pumpWidget(_appWith(router));
    await tester.pumpAndSettle();
    expect(find.text('base'), findsOneWidget);

    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await tester.pumpAndSettle();

    expect(find.text('home'), findsOneWidget);
  });

  testWidgets('onTap 을 주면 그것을 부른다', (tester) async {
    var called = false;
    final router = GoRouter(
      initialLocation: '/base',
      routes: [
        GoRoute(
          path: '/base',
          builder: (context, state) => Scaffold(
            body: AppBackButton(onTap: () => called = true),
          ),
        ),
      ],
    );
    await tester.pumpWidget(_appWith(router));
    await tester.pumpAndSettle();

    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await tester.pumpAndSettle();

    expect(called, isTrue);
  });

  testWidgets('접근성 이름표 "뒤로" 로 찾을 수 있다', (tester) async {
    final router = _router(initialLocation: '/base');
    await tester.pumpWidget(_appWith(router));
    await tester.pumpAndSettle();

    expect(find.bySemanticsLabel(AppStrings.back), findsOneWidget);
  });
}

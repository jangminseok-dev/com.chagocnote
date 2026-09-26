import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/error/error_messages.dart';
import 'package:chagocnote/design/widgets/app_video_player.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/fake_video_playback.dart';

const _url = 'http://media.test/b/original/shops/3/71.mp4?sig=a';

final _poster = MemoryImage(
  // 1×1 회색 PNG.
  Uri.parse(
    'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAACklEQVR4nGNoAAAAggCBd81ytgAAAABJRU5ErkJggg==',
  ).data!.contentAsBytes(),
);

Future<void> _pump(
  WidgetTester tester,
  FakeVideoPlayback playback, {
  Future<String?> Function()? onRetry,
}) => tester.pumpWidget(
  MaterialApp(
    home: Scaffold(
      body: AppVideoPlayer(
        playback: playback,
        url: _url,
        poster: _poster,
        errorMessage: loadMessageFor,
        onRetry: onRetry ?? () async => null,
      ),
    ),
  ),
);

void main() {
  testWidgets('재생 버튼을 누르면 열고 재생한다, 다시 누르면 멈춘다', (tester) async {
    final playback = FakeVideoPlayback();
    await _pump(tester, playback);
    expect(playback.calls, isEmpty, reason: '누르기 전에는 열지 않는다');

    await tester.tap(find.bySemanticsLabel(AppStrings.playVideo));
    await tester.pump();

    expect(playback.calls, ['open $_url', 'play']);
    expect(find.byKey(const Key('video-surface')), findsOneWidget);
    expect(find.text('-0:31'), findsOneWidget);

    await tester.tap(find.bySemanticsLabel(AppStrings.pauseVideo));
    await tester.pump();

    expect(playback.calls.last, 'pause');
    expect(find.bySemanticsLabel(AppStrings.playVideo), findsOneWidget);

    // 끝까지 가면 처음 자리로 돌아가 재생 버튼.
    playback.finish();
    await tester.pump();
    expect(find.text('-0:31'), findsOneWidget);
    expect(find.bySemanticsLabel(AppStrings.playVideo), findsOneWidget);
  });

  testWidgets('실패하면 원인 문구와 [다시 시도] 가 보이고 누르면 onRetry', (tester) async {
    final playback = FakeVideoPlayback(
      failWith: ApiException.network('연결 실패'),
    );
    var retried = 0;
    await _pump(
      tester,
      playback,
      onRetry: () async {
        retried++;
        return 'http://media.test/b/original/shops/3/71.mp4?sig=b';
      },
    );

    await tester.tap(find.bySemanticsLabel(AppStrings.playVideo));
    await tester.pump();

    expect(find.text(offlineLoadMessage), findsOneWidget);
    expect(playback.calls, ['open $_url'], reason: '실패하면 재생하지 않는다');

    playback.failWith = null;
    await tester.tap(find.text(AppStrings.retry));
    await tester.pump();

    expect(retried, 1);
    expect(playback.calls, [
      'open $_url',
      'open http://media.test/b/original/shops/3/71.mp4?sig=b',
      'play',
    ], reason: '받은 새 URL 로 다시 연다');
    expect(find.text(offlineLoadMessage), findsNothing);
  });
}

import 'package:chagocnote/features/visit/api/report_models.dart';
import 'package:chagocnote/features/visit/state/report_rules.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/visit_fixtures.dart';

ReportMedia _media(int id, {bool hidden = false}) =>
    ReportMedia.fromJson(reportMediaJson(mediaId: id, hidden: hidden));

/// 서버의 지금 상태 — 1 보임, 2 뺌, 3 보임.
final _server = [_media(1), _media(2, hidden: true), _media(3)];

void main() {
  group('hiddenIdsOf', () {
    test('누른 것은 서버 상태를 덮고, 누르지 않은 것은 서버의 뺌을 따른다', () {
      expect(hiddenIdsOf(_server, {}), [2]);
      expect(hiddenIdsOf(_server, {3: true}), [2, 3]);
      expect(hiddenIdsOf(_server, {2: false}), isEmpty);
    });

    test('서버에 이제 없는 사진을 눌렀던 것은 버린다', () {
      expect(hiddenIdsOf(_server, {9: true, 1: true}), [1, 2]);
    });

    test('새로 붙은 사진은 보인다', () {
      expect(hiddenIdsOf([..._server, _media(4)], {1: true}), [1, 2]);
    });
  });

  group('hasSomethingToShow', () {
    test('보일 것이 없으면 false — 전부 뺐고 메모도 없다', () {
      const all = {1: true, 3: true};

      expect(hasSomethingToShow(_server, all, null), isFalse);
      // 서버는 빈칸뿐인 메모를 없는 것으로 본다.
      expect(hasSomethingToShow(_server, all, '  \n'), isFalse);
      expect(hasSomethingToShow(const [], const {}, null), isFalse);
    });

    test('메모만 있으면 true', () {
      expect(
        hasSomethingToShow(_server, {1: true, 3: true}, '발바닥 각질'),
        isTrue,
      );
    });

    test('미디어 하나라도 보이면 true — 뺐던 것을 다시 넣어도', () {
      expect(hasSomethingToShow(_server, {1: true}, null), isTrue);
      expect(
        hasSomethingToShow(_server, {1: true, 2: false, 3: true}, null),
        isTrue,
      );
    });
  });
}

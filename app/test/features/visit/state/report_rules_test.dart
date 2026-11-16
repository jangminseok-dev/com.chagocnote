import 'package:chagocnote/features/visit/api/report_models.dart';
import 'package:chagocnote/features/visit/state/report_rules.dart';
import 'package:chagocnote/l10n/app_strings.dart';
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

  // 리뷰 줄(⑫ 설계 3.6) — 서버(`visit/domain/services/report_rules.check_review`)와 같은 규칙이다.
  group('reviewUrlProblem', () {
    test('빈 칸은 문제가 아니다(줄을 지운다)', () {
      expect(reviewUrlProblem(''), isNull);
      expect(reviewUrlProblem('   '), isNull);
    });

    test('https 주소는 통과한다 — 대문자 스킴·앞뒤 공백·질의·숫자 포트·한글 경로', () {
      for (final ok in [
        'https://m.place.naver.com/place/1/review',
        'HTTPS://naver.me/abc',
        '  https://naver.me/abc \n',
        'https://map.kakao.com/?itemId=1#review',
        'https://example.com:8443/review',
        'https://example.com/후기',
      ]) {
        expect(reviewUrlProblem(ok), isNull, reason: ok);
      }
    });

    test('https:// 로 시작하지 않으면 그 까닭을 말한다', () {
      for (final bad in [
        'http://naver.me/abc',
        'naver.me/abc',
        'javascript:alert(1)',
        'https:naver.me',
      ]) {
        expect(reviewUrlProblem(bad), AppStrings.reviewUrlNotHttps, reason: bad);
      }
    });

    test('300자까지 — 301자는 길다', () {
      final base = 'https://example.com/';
      expect(reviewUrlProblem(base + 'a' * (300 - base.length)), isNull);
      expect(
        reviewUrlProblem(base + 'a' * (301 - base.length)),
        AppStrings.reviewUrlTooLong,
      );
    });

    test('호스트 없음·계정 정보·가운데 공백·보이지 않는 문자·숫자가 아닌 포트·짝 없는 대괄호는 주소를 다시 보라고 한다', () {
      for (final bad in [
        'https://',
        'https:///review',
        'https://user@naver.me/abc',
        'https://@naver.me/abc',
        'https://naver.me/a b',
        'https://naver.me/a\u200bb',
        'https://naver.me/a\u202eb',
        'https://naver.me:abc/review',
        'https://naver.me]',
      ]) {
        expect(reviewUrlProblem(bad), AppStrings.reviewUrlInvalid, reason: bad);
      }
    });
  });

  group('reviewTextProblem', () {
    test('빈 칸과 60자까지의 한 줄은 통과한다', () {
      expect(reviewTextProblem(''), isNull);
      expect(reviewTextProblem('가' * 60), isNull);
      expect(reviewTextProblem('🐶' * 60), isNull); // 글자 수는 보이는 글자로 센다
    });

    test('61자는 길다', () {
      expect(reviewTextProblem('가' * 61), AppStrings.reviewTextTooLong);
    });

    test('줄바꿈·탭·보이지 않는 문자는 한 줄로 쓰라고 한다', () {
      for (final bad in ['첫 줄\n둘째 줄', '탭\t글', '너비\u200b없음']) {
        expect(reviewTextProblem(bad), AppStrings.reviewTextOneLine, reason: bad);
      }
    });

    test('주소처럼 보이는 글(http·www.)은 넣지 못한다 — 대소문자 무관', () {
      for (final bad in ['HTTP 로 오세요', '후기는 www.example.com', 'https 말고']) {
        expect(reviewTextProblem(bad), AppStrings.reviewTextNoLink, reason: bad);
      }
    });
  });

  group('cleanReviewUrl · cleanReviewText', () {
    test('주소는 앞뒤 공백을 걷고, 비면 null', () {
      expect(cleanReviewUrl('  https://naver.me/abc\n'), 'https://naver.me/abc');
      expect(cleanReviewUrl('   '), isNull);
    });

    test('주소의 스킴만 소문자로 바꾼다 — 서버(normalized_review_url)와 같다', () {
      expect(cleanReviewUrl('HTTPS://naver.me/ABC'), 'https://naver.me/ABC');
      expect(cleanReviewUrl('HtTpS://Naver.me/a'), 'https://Naver.me/a');
      expect(cleanReviewUrl('naver.me/ABC'), 'naver.me/ABC');
    });

    test('문구는 앞뒤 공백을 걷고, 비거나 기본 문구와 같으면 null(기본 문구가 나간다)', () {
      expect(cleanReviewText(' 후기 부탁드려요 ', defaultText: reviewTextDefault), '후기 부탁드려요');
      expect(cleanReviewText('  ', defaultText: reviewTextDefault), isNull);
      expect(cleanReviewText(reviewTextDefault, defaultText: reviewTextDefault), isNull);
      expect(cleanReviewText(reviewTextDefault, defaultText: null), reviewTextDefault);
    });
  });
}

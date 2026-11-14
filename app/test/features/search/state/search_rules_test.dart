// 검색 화면의 문구와 갈 곳 — 순수 함수.
import 'package:chagocnote/features/search/api/search_models.dart';
import 'package:chagocnote/features/search/state/search_rules.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/search_fixtures.dart';

SearchItem _item(Map<String, dynamic> json) => SearchItem.tryParse(json)!;

void main() {
  group('검색어 다듬기', () {
    test('앞뒤 공백을 떼고 공백류를 빈칸 하나로 줄인다', () {
      expect(cleanSearchText('  귀를\n만지면 \t 싫어해요  '), '귀를 만지면 싫어해요');
    });

    test('두 자 미만이면 묻지 않는다', () {
      expect(cleanSearchText(''), isNull);
      expect(cleanSearchText('   '), isNull);
      expect(cleanSearchText(' 귀 '), isNull);
      expect(cleanSearchText('발톱'), '발톱');
    });

    test('백 자에서 자른다', () {
      expect(cleanSearchText('가' * 100)!.length, 100);
      expect(cleanSearchText('가' * 130)!.length, 100);
    });
  });

  group('줄의 문구', () {
    test('종류의 이름 여섯', () {
      expect(SearchKind.values.map(kindLabel), ['케어 노트', '내부 메모', '예약 메모', '특이사항', '지병', '보호자 메모']);
    });

    test('제목은 아이 이름이고, 아이가 없으면 보호자 이름이다', () {
      expect(titleOf(_item(searchItemJson())), '콩이');
      expect(titleOf(_item(searchOwnerItemJson())), '김민지');
      expect(titleOf(_item(searchItemJson(kind: 'visit_memo', petId: null, pet: null))), '김민지');
    });

    test('둘째 줄은 종류와 날짜다 — 날짜가 없으면 종류만', () {
      expect(metaLine(_item(searchItemJson())), '케어 노트 · 11월 3일');
      expect(metaLine(_item(searchPetItemJson())), '특이사항');
      expect(metaLine(_item(searchPetItemJson(kind: 'condition_note'))), '지병');
      expect(metaLine(_item(searchOwnerItemJson())), '보호자 메모');
    });
  });

  group('누르면 갈 곳', () {
    test('방문이 있으면 방문 상세', () {
      expect(destinationOf(_item(searchItemJson(visitId: 7))), '/visits/7');
    });

    test('방문이 없으면 그 아이의 상세', () {
      expect(destinationOf(_item(searchPetItemJson(petId: 102))), '/pets/102');
    });

    test('보호자 메모는 열 아이의 [보호자] 탭', () {
      expect(destinationOf(_item(searchOwnerItemJson(openPetId: 101))), '/pets/101?tab=owner');
    });

    test('방문도 열 아이도 없으면 갈 곳이 없다', () {
      expect(destinationOf(_item(searchOwnerItemJson(openPetId: null))), isNull);
    });
  });
}

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 반려동물 상세의 [기록] 탭에 들어갈 화면 — 기록 피드는 visit 기능이 그리는데 customer 는 visit 를
/// import 하지 않는다(기능 폴더 규칙). 이 자리를 `app.dart`의 `buildRoot`가 채운다.
typedef PetRecordsBuilder = Widget Function(int petId);

final petRecordsPlugProvider = Provider<PetRecordsBuilder>(
  (ref) => throw UnimplementedError('app.dart 의 buildRoot 가 채운다'),
);

/// [기록] 탭을 다시 읽게 하는 자리 — 반려동물 상세를 당겨서 새로고침할 때 부른다(오류 화면 다듬기 설계
/// 3절). `buildRoot`가 visit 의 피드를 무효화하도록 채운다. 채우지 않으면(테스트) 아무것도 하지 않는다.
typedef PetRecordsRefresher = void Function(int petId);

final petRecordsRefreshPlugProvider = Provider<PetRecordsRefresher>(
  (ref) => (_) {},
);

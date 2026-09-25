import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 반려동물 상세의 [기록] 탭에 들어갈 화면 — 기록 피드는 visit 기능이 그리는데 customer 는 visit 를
/// import 하지 않는다(기능 폴더 규칙). 이 자리를 `app.dart`의 `buildRoot`가 채운다.
typedef PetRecordsBuilder = Widget Function(int petId);

final petRecordsPlugProvider = Provider<PetRecordsBuilder>(
  (ref) => throw UnimplementedError('app.dart 의 buildRoot 가 채운다'),
);
